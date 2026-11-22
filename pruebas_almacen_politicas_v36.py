"""Pruebas independientes: solo SQLite en memoria o en carpeta temporal."""

import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from almacen_politicas_v36 import (
    actualizar_politica_proyecto,
    consultar_politica_proyecto,
    guardar_politica_proyecto,
)
from guardado_seguro_politicas_v35 import validar_politica
from verificar_politica_guardada_v35 import verificar_objetivo_guardado


def preparar_laboratorio(conexion):
    # El esquema se crea exclusivamente en las conexiones de estas pruebas.
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.executescript("""
        CREATE TABLE proyectos (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL
        );
        CREATE TABLE politicas_proyecto (
            proyecto_id INTEGER PRIMARY KEY,
            dominios TEXT NOT NULL,
            puertos TEXT NOT NULL,
            protocolos TEXT NOT NULL,
            FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
                ON DELETE RESTRICT
        );
        CREATE TABLE eventos (detalle TEXT NOT NULL);
    """)
    conexion.executemany(
        "INSERT INTO proyectos (id, nombre) VALUES (?, ?)",
        [(1, "Web ficticia"), (2, "API ficticia")],
    )
    conexion.commit()


class PruebasAlmacenPoliticas(unittest.TestCase):
    def setUp(self):
        self.conexion = sqlite3.connect(":memory:")
        self.addCleanup(self.conexion.close)
        preparar_laboratorio(self.conexion)
        self.web = {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"https"},
        }
        self.api = {
            "dominios": {"example.net"},
            "puertos": {8443},
            "protocolos": {"https"},
        }

    def leer(self, proyecto_id=1):
        return consultar_politica_proyecto(self.conexion, proyecto_id)

    def fila_cruda(self):
        return self.conexion.execute(
            "SELECT * FROM politicas_proyecto WHERE proyecto_id = 1"
        ).fetchone()

    def test_guardar_y_consultar(self):
        self.assertTrue(guardar_politica_proyecto(self.conexion, 1, self.web))
        self.assertEqual(self.leer(), self.web)
        self.assertFalse(self.conexion.in_transaction)

    def test_actualizar(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        self.assertTrue(actualizar_politica_proyecto(self.conexion, 1, self.api))
        self.assertEqual(self.leer(), self.api)

    def test_duplicado_no_reemplaza(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        with self.assertRaises(sqlite3.IntegrityError):
            guardar_politica_proyecto(self.conexion, 1, self.api)
        self.assertEqual(self.leer(), self.web)

    def test_proyecto_sin_politica(self):
        self.assertIsNone(self.leer())

    def test_actualizar_sin_politica(self):
        with self.assertRaisesRegex(ValueError, "no tiene una politica"):
            actualizar_politica_proyecto(self.conexion, 1, self.web)
        self.assertIsNone(self.leer())

    def test_ids_invalidos(self):
        for identificador in (True, False, 0, -1, "1", 1.0, None):
            for operacion in (guardar_politica_proyecto, actualizar_politica_proyecto):
                with self.subTest(id=identificador, operacion=operacion.__name__):
                    with self.assertRaises(ValueError):
                        operacion(self.conexion, identificador, self.web)
            with self.subTest(id=identificador, operacion="consultar"):
                with self.assertRaises(ValueError):
                    self.leer(identificador)

    def test_proyecto_inexistente_con_y_sin_claves_foraneas(self):
        for activadas in (False, True):
            self.conexion.execute(
                "PRAGMA foreign_keys = " + ("ON" if activadas else "OFF")
            )
            self.assertEqual(
                self.conexion.execute("PRAGMA foreign_keys").fetchone()[0],
                int(activadas),
            )
            for operacion in (guardar_politica_proyecto, actualizar_politica_proyecto):
                with self.subTest(fk=activadas, operacion=operacion.__name__):
                    with self.assertRaisesRegex(ValueError, "El proyecto no existe"):
                        operacion(self.conexion, 99, self.web)
            with self.assertRaisesRegex(ValueError, "El proyecto no existe"):
                self.leer(99)
        self.assertEqual(
            self.conexion.execute("SELECT COUNT(*) FROM politicas_proyecto").fetchone()[0],
            0,
        )

    def test_actualizaciones_invalidas_conservan_fila_original(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        original = self.fila_cruda()
        invalidas = [
            None,
            {},
            {"dominios": {"example.org"}, "puertos": {443}},
            {**self.web, "extra": True},
            {**self.web, "dominios": {"dominio..org"}},
            {**self.web, "dominios": {"Example.org"}},
            {**self.web, "dominios": set()},
            {**self.web, "dominios": "example.org"},
            {**self.web, "puertos": {0}},
            {**self.web, "puertos": {65536}},
            {**self.web, "puertos": {True}},
            {**self.web, "puertos": {"443"}},
            {**self.web, "protocolos": {"ftp"}},
            {**self.web, "protocolos": []},
        ]
        for politica in invalidas:
            with self.subTest(politica=politica):
                with self.assertRaises(ValueError):
                    actualizar_politica_proyecto(self.conexion, 1, politica)
                self.assertEqual(self.fila_cruda(), original)

    def test_guardado_invalido_no_crea_fila(self):
        with self.assertRaises(ValueError):
            guardar_politica_proyecto(self.conexion, 1, {**self.web, "puertos": {70000}})
        self.assertIsNone(self.leer())

    def test_politicas_independientes(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        guardar_politica_proyecto(self.conexion, 2, self.api)
        nueva = {**self.web, "puertos": {443, 8443}}
        actualizar_politica_proyecto(self.conexion, 1, nueva)
        self.assertEqual(self.leer(1), nueva)
        self.assertEqual(self.leer(2), self.api)

    def test_validar_no_ejecuta_sql(self):
        with self.assertRaisesRegex(ValueError, "Puerto invalido"):
            validar_politica(1, {**self.web, "puertos": {70000}})
        validar_politica(1, self.web)
        self.assertIsNone(self.leer())

    def test_guardar_no_confirma_transaccion_externa(self):
        self.conexion.execute("BEGIN")
        self.conexion.execute("INSERT INTO eventos VALUES ('pendiente')")
        guardar_politica_proyecto(self.conexion, 1, self.web)
        self.assertTrue(self.conexion.in_transaction)
        self.assertEqual(self.leer(), self.web)
        self.conexion.rollback()
        self.assertIsNone(self.leer())
        self.assertEqual(self.conexion.execute("SELECT * FROM eventos").fetchall(), [])

    def test_actualizar_no_confirma_transaccion_externa(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        self.conexion.execute("BEGIN")
        self.conexion.execute("INSERT INTO eventos VALUES ('pendiente')")
        actualizar_politica_proyecto(self.conexion, 1, self.api)
        self.assertTrue(self.conexion.in_transaction)
        self.assertEqual(self.leer(), self.api)
        self.conexion.rollback()
        self.assertEqual(self.leer(), self.web)
        self.assertEqual(self.conexion.execute("SELECT * FROM eventos").fetchall(), [])

    def test_fallo_sql_revierte_solo_la_operacion(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        # RAISE(FAIL) conserva efectos previos del trigger sin el SAVEPOINT.
        self.conexion.executescript("""
            CREATE TRIGGER fallo_insertar BEFORE INSERT ON politicas_proyecto
            BEGIN
                INSERT INTO eventos VALUES ('efecto del trigger');
                SELECT RAISE(FAIL, 'fallo simulado');
            END;
            CREATE TRIGGER fallo_actualizar BEFORE UPDATE ON politicas_proyecto
            BEGIN
                INSERT INTO eventos VALUES ('efecto del trigger');
                SELECT RAISE(FAIL, 'fallo simulado');
            END;
        """)
        self.conexion.execute("BEGIN")
        self.conexion.execute("INSERT INTO eventos VALUES ('anterior')")
        for operacion, proyecto_id in (
            (guardar_politica_proyecto, 2),
            (actualizar_politica_proyecto, 1),
        ):
            with self.subTest(operacion=operacion.__name__):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "fallo simulado"):
                    operacion(self.conexion, proyecto_id, self.api)
                self.assertTrue(self.conexion.in_transaction)
                self.assertEqual(self.leer(1), self.web)
                self.assertIsNone(self.leer(2))
                self.assertEqual(
                    self.conexion.execute("SELECT * FROM eventos").fetchall(),
                    [("anterior",)],
                )
        self.conexion.execute("INSERT INTO eventos VALUES ('posterior')")
        self.conexion.commit()
        self.assertEqual(
            self.conexion.execute("SELECT * FROM eventos").fetchall(),
            [("anterior",), ("posterior",)],
        )

    def test_fallo_validacion_conserva_transaccion_externa(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        self.conexion.execute("BEGIN")
        self.conexion.execute("INSERT INTO eventos VALUES ('anterior')")
        with self.assertRaises(ValueError):
            actualizar_politica_proyecto(self.conexion, 1, {**self.web, "puertos": {0}})
        self.assertTrue(self.conexion.in_transaction)
        self.assertEqual(self.leer(), self.web)
        self.assertEqual(
            self.conexion.execute("SELECT * FROM eventos").fetchall(), [("anterior",)]
        )
        self.conexion.rollback()

    def test_json_danado_se_rechaza(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        self.conexion.execute(
            "UPDATE politicas_proyecto SET dominios = ? WHERE proyecto_id = 1",
            ("JSON_INVALIDO",),
        )
        with self.assertRaises(ValueError):
            self.leer()

    def test_sin_politica_bloquea_antes_del_dns(self):
        resolver = Mock(side_effect=AssertionError("No consultar DNS"))
        with self.assertRaisesRegex(ValueError, "no tiene una politica"):
            verificar_objetivo_guardado(
                self.conexion, 1, "https://example.org", resolver
            )
        resolver.assert_not_called()

    def test_politica_guardada_con_dns_simulado(self):
        guardar_politica_proyecto(self.conexion, 1, self.web)
        resolver = Mock(return_value=["8.8.8.8"])
        resultado = verificar_objetivo_guardado(
            self.conexion, 1, "https://example.org", resolver
        )
        self.assertEqual(resultado["puerto"], 443)
        self.assertEqual(resultado["ips"], ["8.8.8.8"])
        resolver.assert_called_once_with("example.org")

    def test_sin_tabla_no_la_crea(self):
        with closing(sqlite3.connect(":memory:")) as conexion:
            conexion.execute("CREATE TABLE proyectos (id INTEGER PRIMARY KEY)")
            conexion.execute("INSERT INTO proyectos VALUES (1)")
            conexion.commit()
            for operacion in (guardar_politica_proyecto, actualizar_politica_proyecto):
                with self.assertRaises(sqlite3.OperationalError):
                    operacion(conexion, 1, self.web)
            with self.assertRaises(sqlite3.OperationalError):
                consultar_politica_proyecto(conexion, 1)
            self.assertIsNone(conexion.execute(
                "SELECT name FROM sqlite_master WHERE name = 'politicas_proyecto'"
            ).fetchone())

    def test_persistencia_y_lectura_sin_escritura(self):
        with TemporaryDirectory(prefix="moondetex_v36_") as temporal:
            archivo = Path(temporal) / "politicas_prueba.db"
            with closing(sqlite3.connect(archivo)) as conexion:
                preparar_laboratorio(conexion)
                guardar_politica_proyecto(conexion, 1, self.web)
                actualizar_politica_proyecto(conexion, 1, self.api)
            with closing(sqlite3.connect(archivo.as_uri() + "?mode=ro", uri=True)) as conexion:
                self.assertEqual(consultar_politica_proyecto(conexion, 1), self.api)
                with self.assertRaises(sqlite3.OperationalError):
                    actualizar_politica_proyecto(conexion, 1, self.web)
                self.assertEqual(consultar_politica_proyecto(conexion, 1), self.api)


if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=True)
