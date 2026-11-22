import unittest
import sqlite3
import json

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from laboratorio_politicas_sqlite_v35 import (
    crear_tablas,
    guardar_politica,
    consultar_politica
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE POLITICAS EN SQLITE
# =====================================

class PruebasPoliticasSQLite(unittest.TestCase):

    def setUp(self):

        # Crear una base temporal independiente
        self.temporal = TemporaryDirectory(
            prefix="pruebas_politicas_"
        )

        self.addCleanup(self.temporal.cleanup)

        self.db = Path(
            self.temporal.name
        ) / "pruebas.db"

        self.conexion = sqlite3.connect(self.db)
        self.addCleanup(self.conexion.close)

        self.conexion.execute(
            "PRAGMA foreign_keys = ON"
        )

        crear_tablas(self.conexion)

        # Proyectos ficticios
        self.conexion.executemany(
            "INSERT INTO proyectos "
            "(id, nombre) VALUES (?, ?)",
            [
                (1, "Laboratorio Web"),
                (2, "Laboratorio API")
            ]
        )

        self.conexion.commit()

        self.politica_web = {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"https"}
        }

        self.politica_api = {
            "dominios": {"example.net"},
            "puertos": {8443},
            "protocolos": {"https"}
        }

    # PRUEBA 1: PROYECTO SIN POLITICA

    def test_sin_politica(self):

        resultado = consultar_politica(
            self.conexion, 1
        )

        self.assertIsNone(resultado)

    # PRUEBA 2: GUARDAR Y RECUPERAR

    def test_guardar_y_recuperar(self):

        guardar_politica(
            self.conexion, 1, self.politica_web
        )

        resultado = consultar_politica(
            self.conexion, 1
        )

        self.assertEqual(
            resultado,
            self.politica_web
        )

    # PRUEBA 3: POLITICAS INDEPENDIENTES

    def test_politicas_independientes(self):

        guardar_politica(
            self.conexion, 1, self.politica_web
        )

        guardar_politica(
            self.conexion, 2, self.politica_api
        )

        self.assertEqual(
            consultar_politica(self.conexion, 1),
            self.politica_web
        )

        self.assertEqual(
            consultar_politica(self.conexion, 2),
            self.politica_api
        )

    # PRUEBA 4: PERSISTENCIA TRAS REABRIR

    def test_persistencia(self):

        guardar_politica(
            self.conexion, 2, self.politica_api
        )

        # Reabrir el archivo en modo lectura
        with closing(
            sqlite3.connect(
                self.db.as_uri() + "?mode=ro",
                uri=True
            )
        ) as lectura:

            resultado = consultar_politica(
                lectura, 2
            )

        self.assertEqual(
            resultado,
            self.politica_api
        )

    # PRUEBA 5: IMPEDIR POLITICA DUPLICADA

    def test_politica_duplicada(self):

        guardar_politica(
            self.conexion, 1, self.politica_web
        )

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            guardar_politica(
                self.conexion, 1, self.politica_api
            )

    # PRUEBA 6: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            guardar_politica(
                self.conexion, 99, self.politica_web
            )

    # PRUEBA 7: CONSULTAR ID DESCONOCIDO

    def test_consulta_desconocida(self):

        resultado = consultar_politica(
            self.conexion, 99
        )

        self.assertIsNone(resultado)

    # PRUEBA 8: DETECTAR JSON INCORRECTO

    def test_json_incorrecto(self):

        self.conexion.execute(
            """
            INSERT INTO politicas
            (proyecto_id, dominios, puertos, protocolos)
            VALUES (?, ?, ?, ?)
            """,
            (1, "JSON_INVALIDO", "[443]", '["https"]')
        )

        self.conexion.commit()

        with self.assertRaises(
            json.JSONDecodeError
        ):
            consultar_politica(
                self.conexion, 1
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
