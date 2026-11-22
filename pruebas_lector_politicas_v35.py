import unittest
import sqlite3
import json

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from lector_politicas_v35 import cargar_politica


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DEL LECTOR DE POLITICAS
# =====================================

class PruebasLectorPoliticas(unittest.TestCase):

    def setUp(self):

        # Crear base de datos temporal
        self.temporal = TemporaryDirectory(
            prefix="pruebas_lector_"
        )

        self.addCleanup(self.temporal.cleanup)

        self.db = (
            Path(self.temporal.name) / "pruebas.db"
        )

        self.conexion = sqlite3.connect(self.db)
        self.addCleanup(self.conexion.close)

        self.conexion.execute(
            "PRAGMA foreign_keys = ON"
        )

        # Crear tablas de laboratorio
        self.conexion.execute("""
            CREATE TABLE proyectos (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL
            )
        """)

        self.conexion.execute("""
            CREATE TABLE politicas_proyecto (
                proyecto_id INTEGER PRIMARY KEY,
                dominios TEXT NOT NULL,
                puertos TEXT NOT NULL,
                protocolos TEXT NOT NULL,
                FOREIGN KEY (proyecto_id)
                    REFERENCES proyectos(id)
            )
        """)

        # Crear proyectos ficticios
        self.conexion.executemany(
            "INSERT INTO proyectos VALUES (?, ?)",
            [
                (1, "Laboratorio Web"),
                (2, "Laboratorio API")
            ]
        )

        # Solo el proyecto 2 tiene politica
        self.conexion.execute(
            """
            INSERT INTO politicas_proyecto
            VALUES (?, ?, ?, ?)
            """,
            (
                2,
                json.dumps(["example.net"]),
                json.dumps([8443]),
                json.dumps(["https"])
            )
        )

        self.conexion.commit()

    # PRUEBA 1: PROYECTO CON POLITICA

    def test_politica_existente(self):

        resultado = cargar_politica(
            self.conexion, 2
        )

        self.assertEqual(
            resultado["dominios"],
            {"example.net"}
        )

        self.assertEqual(
            resultado["puertos"],
            {8443}
        )

        self.assertEqual(
            resultado["protocolos"],
            {"https"}
        )

    # PRUEBA 2: PROYECTO SIN POLITICA

    def test_politica_pendiente(self):

        resultado = cargar_politica(
            self.conexion, 1
        )

        self.assertIsNone(resultado)

    # PRUEBA 3: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaisesRegex(
            ValueError,
            "El proyecto no existe"
        ):
            cargar_politica(
                self.conexion, 99
            )

    # PRUEBA 4: ID COMO TEXTO

    def test_id_texto(self):

        with self.assertRaises(ValueError):
            cargar_politica(
                self.conexion, "2"
            )

    # PRUEBA 5: ID CERO

    def test_id_cero(self):

        with self.assertRaises(ValueError):
            cargar_politica(
                self.conexion, 0
            )

    # PRUEBA 6: JSON INCORRECTO

    def test_json_incorrecto(self):

        self.conexion.execute(
            """
            UPDATE politicas_proyecto
            SET dominios = ?
            WHERE proyecto_id = ?
            """,
            ("JSON_INVALIDO", 2)
        )

        self.conexion.commit()

        with self.assertRaises(ValueError):
            cargar_politica(
                self.conexion, 2
            )

    # PRUEBA 7: PUERTOS CON TIPO INCORRECTO

    def test_puertos_invalidos(self):

        self.conexion.execute(
            """
            UPDATE politicas_proyecto
            SET puertos = ?
            WHERE proyecto_id = ?
            """,
            (json.dumps(["8443"]), 2)
        )

        self.conexion.commit()

        with self.assertRaises(ValueError):
            cargar_politica(
                self.conexion, 2
            )

    # PRUEBA 8: LECTURA SIN PERMISOS DE ESCRITURA

    def test_solo_lectura(self):

        with closing(
            sqlite3.connect(
                self.db.as_uri() + "?mode=ro",
                uri=True
            )
        ) as lectura:

            resultado = cargar_politica(
                lectura, 2
            )

        self.assertEqual(
            resultado["puertos"],
            {8443}
        )


    # PRUEBA 9: PUERTO FUERA DE RANGO

    def test_puerto_fuera_de_rango(self):

        self.conexion.execute(
            """
            UPDATE politicas_proyecto
            SET puertos = ?
            WHERE proyecto_id = ?
            """,
            (json.dumps([70000]), 2)
        )

        self.conexion.commit()

        with self.assertRaisesRegex(
            ValueError,
            "puerto invalido"
        ):
            cargar_politica(self.conexion, 2)


    # PRUEBA 10: PROTOCOLO NO PERMITIDO

    def test_protocolo_no_permitido(self):

        self.conexion.execute(
            """
            UPDATE politicas_proyecto
            SET protocolos = ?
            WHERE proyecto_id = ?
            """,
            (json.dumps(["ftp"]), 2)
        )

        self.conexion.commit()

        with self.assertRaisesRegex(
            ValueError,
            "protocolo invalido"
        ):
            cargar_politica(self.conexion, 2)


    # PRUEBA 11: DOMINIO MAL FORMADO

    def test_dominio_mal_formado(self):

        self.conexion.execute(
            """
            UPDATE politicas_proyecto
            SET dominios = ?
            WHERE proyecto_id = ?
            """,
            (json.dumps(["dominio..org"]), 2)
        )

        self.conexion.commit()

        with self.assertRaisesRegex(
            ValueError,
            "dominio invalido"
        ):
            cargar_politica(self.conexion, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
