import io
import sqlite3
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing, redirect_stdout
from unittest.mock import patch

from ensayo_migracion_politicas_v35 import ensayar_migracion


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE MIGRACION SQLITE
# =====================================

class PruebasMigracionPoliticas(unittest.TestCase):

    def setUp(self):

        # Crear una base de datos ficticia
        self.temporal = TemporaryDirectory(
            prefix="moondetex_test_migracion_"
        )

        self.addCleanup(self.temporal.cleanup)

        self.db = (
            Path(self.temporal.name) / "laboratorio.db"
        )

        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL
                )
            """)

            conexion.execute(
                "INSERT INTO proyectos (id, nombre) "
                "VALUES (?, ?)",
                (1, "Laboratorio Web")
            )

            conexion.commit()

    def ejecutar_ensayo(self):

        salida = io.StringIO()

        # Sustituir la ruta original por la base ficticia
        with patch(
            "ensayo_migracion_politicas_v35.DB",
            self.db
        ):
            with redirect_stdout(salida):
                ensayar_migracion()

        return salida.getvalue()

    # PRUEBA 1: CONSERVAR PROYECTO

    def test_conservar_proyecto(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Proyectos conservados: 1",
            salida
        )

    # PRUEBA 2: CONSERVAR VARIOS PROYECTOS

    def test_varios_proyectos(self):

        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute(
                "INSERT INTO proyectos (id, nombre) "
                "VALUES (?, ?)",
                (2, "Laboratorio API")
            )

            conexion.commit()

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Proyectos conservados: 2",
            salida
        )

    # PRUEBA 3: CREAR TABLA EN LA COPIA

    def test_crear_tabla_en_copia(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Tabla de politicas creada: True",
            salida
        )

        # Confirmar que NO exista en la base original
        with closing(sqlite3.connect(self.db)) as conexion:

            tabla = conexion.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' "
                "AND name = 'politicas_proyecto'"
            ).fetchone()

        self.assertIsNone(tabla)

    # PRUEBA 4: NO CREAR POLITICAS AUTOMATICAS

    def test_sin_politicas_automaticas(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Politicas iniciales: 0",
            salida
        )

    # PRUEBA 5: ELIMINAR COPIA TEMPORAL

    def test_eliminar_copia_temporal(self):

        self.ejecutar_ensayo()

        carpetas = list(
            Path(self.temporal.name).glob(
                "ensayo_politicas_*"
            )
        )

        self.assertEqual(carpetas, [])

    # PRUEBA 6: CONSERVAR BASE ORIGINAL

    def test_base_original_intacta(self):

        contenido_antes = self.db.read_bytes()

        self.ejecutar_ensayo()

        contenido_despues = self.db.read_bytes()

        self.assertEqual(
            contenido_antes,
            contenido_despues
        )

    # PRUEBA 7: BASE INEXISTENTE

    def test_base_inexistente(self):

        self.db.unlink()

        with self.assertRaises(FileNotFoundError):
            self.ejecutar_ensayo()


if __name__ == "__main__":
    unittest.main(verbosity=2)
