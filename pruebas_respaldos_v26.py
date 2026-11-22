import sqlite3
import tempfile
import unittest

from contextlib import closing
from pathlib import Path

from respaldo_sqlite_v26 import crear_respaldo


# =====================================
# MOONDETEX - CLASE 26
# PRUEBAS AUTOMATICAS DE RESPALDOS
# =====================================

class PruebasRespaldos(unittest.TestCase):

    def setUp(self):

        # Crear un laboratorio temporal
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.carpeta = Path(self.temporal.name)

        self.original = self.carpeta / "original.db"
        self.respaldos = self.carpeta / "respaldos"

        # Crear una base con datos ficticios
        with closing(sqlite3.connect(self.original)) as con:

            con.execute("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL
                )
            """)

            con.execute(
                "INSERT INTO proyectos (nombre) VALUES (?)",
                ("Laboratorio MOONDETEX",)
            )

            con.commit()


    # =====================================
    # PRUEBA 1: RESPALDO CON DATOS
    # =====================================

    def test_respaldo_con_datos(self):

        copia = crear_respaldo(
            self.original,
            self.respaldos
        )

        self.assertTrue(copia.is_file())

        with closing(sqlite3.connect(copia)) as con:

            nombre = con.execute(
                "SELECT nombre FROM proyectos"
            ).fetchone()[0]

            integridad = con.execute(
                "PRAGMA quick_check"
            ).fetchone()[0]

        self.assertEqual(
            nombre,
            "Laboratorio MOONDETEX"
        )

        self.assertEqual(integridad, "ok")

        # Comprobar que la base original conserva sus datos
        with closing(sqlite3.connect(self.original)) as con:

            cantidad = con.execute(
                "SELECT COUNT(*) FROM proyectos"
            ).fetchone()[0]

        self.assertEqual(cantidad, 1)


    # =====================================
    # PRUEBA 2: BASE INEXISTENTE
    # =====================================

    def test_base_inexistente(self):

        inexistente = self.carpeta / "no_existe.db"

        with self.assertRaises(FileNotFoundError):

            crear_respaldo(
                inexistente,
                self.respaldos
            )

        self.assertFalse(inexistente.exists())


    # =====================================
    # PRUEBA 3: NO SOBRESCRIBIR COPIAS
    # =====================================

    def test_conservar_respaldos(self):

        primera = crear_respaldo(
            self.original,
            self.respaldos
        )

        # Agregar otro registro a la base de laboratorio
        with closing(sqlite3.connect(self.original)) as con:

            con.execute(
                "INSERT INTO proyectos (nombre) VALUES (?)",
                ("Segundo proyecto",)
            )

            con.commit()

        segunda = crear_respaldo(
            self.original,
            self.respaldos
        )

        # Las copias deben tener nombres diferentes
        self.assertNotEqual(primera, segunda)

        self.assertTrue(primera.is_file())
        self.assertTrue(segunda.is_file())

        # La primera copia debe conservar sus datos
        with closing(sqlite3.connect(primera)) as con:

            cantidad_primera = con.execute(
                "SELECT COUNT(*) FROM proyectos"
            ).fetchone()[0]

        # La segunda copia contiene el nuevo proyecto
        with closing(sqlite3.connect(segunda)) as con:

            cantidad_segunda = con.execute(
                "SELECT COUNT(*) FROM proyectos"
            ).fetchone()[0]

        self.assertEqual(cantidad_primera, 1)
        self.assertEqual(cantidad_segunda, 2)


# =====================================
# EJECUTAR LAS PRUEBAS
# =====================================

if __name__ == "__main__":

    unittest.main(verbosity=2)
