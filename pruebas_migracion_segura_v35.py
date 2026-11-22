import io
import sqlite3
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing, redirect_stdout
from unittest.mock import patch

from verificar_migracion_segura_v35 import (
    verificar_migracion_segura
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE MIGRACION SEGURA
# =====================================

class PruebasMigracionSegura(unittest.TestCase):

    def setUp(self):

        self.temporal = TemporaryDirectory(
            prefix="moondetex_migracion_"
        )
        self.addCleanup(self.temporal.cleanup)

        self.carpeta = Path(self.temporal.name)
        self.db = self.carpeta / "pruebas.db"

        # Crear datos ficticios
        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute("PRAGMA foreign_keys = ON")

            conexion.execute("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL
                )
            """)

            conexion.execute("""
                CREATE TABLE hallazgos (
                    id INTEGER PRIMARY KEY,
                    proyecto_id INTEGER NOT NULL,
                    detalle TEXT NOT NULL,
                    FOREIGN KEY (proyecto_id)
                        REFERENCES proyectos(id)
                )
            """)

            conexion.execute(
                "INSERT INTO proyectos VALUES (?, ?)",
                (1, "Laboratorio de prueba")
            )

            conexion.execute(
                "INSERT INTO hallazgos VALUES (?, ?, ?)",
                (1, 1, "Hallazgo simulado")
            )

            conexion.commit()

    def ejecutar_ensayo(self):

        salida = io.StringIO()

        with patch(
            "verificar_migracion_segura_v35.DB",
            self.db
        ):
            with redirect_stdout(salida):
                verificar_migracion_segura()

        return salida.getvalue()

    # PRUEBA 1: CONSERVAR REGISTROS

    def test_registros_conservados(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Registros conservados: True",
            salida
        )

    # PRUEBA 2: TABLA NUEVA VACIA

    def test_politicas_iniciales(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Politicas nuevas: 0",
            salida
        )

    # PRUEBA 3: INTEGRIDAD SQLITE

    def test_integridad_sqlite(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Integridad SQLite: ok",
            salida
        )

    # PRUEBA 4: CLAVES FORANEAS

    def test_claves_foraneas(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "Errores de claves foraneas: 0",
            salida
        )

    # PRUEBA 5: RESULTADO APROBADO

    def test_ensayo_aprobado(self):

        salida = self.ejecutar_ensayo()

        self.assertIn(
            "RESULTADO: ENSAYO APROBADO",
            salida
        )

    # PRUEBA 6: BASE ORIGINAL INTACTA

    def test_original_intacta(self):

        antes = self.db.read_bytes()

        self.ejecutar_ensayo()

        despues = self.db.read_bytes()

        self.assertEqual(antes, despues)

        with closing(
            sqlite3.connect(
                self.db.as_uri() + "?mode=ro",
                uri=True
            )
        ) as conexion:

            tabla = conexion.execute(
                "SELECT name FROM sqlite_master "
                "WHERE name = 'politicas_proyecto'"
            ).fetchone()

        self.assertIsNone(tabla)

    # PRUEBA 7: ELIMINAR COPIA TEMPORAL

    def test_eliminar_copia(self):

        self.ejecutar_ensayo()

        carpetas = list(
            self.carpeta.glob("ensayo_seguro_*")
        )

        self.assertEqual(carpetas, [])

    # PRUEBA 8: BASE INEXISTENTE

    def test_base_inexistente(self):

        self.db.unlink()

        with self.assertRaises(FileNotFoundError):
            self.ejecutar_ensayo()

    # PRUEBA 9: TABLA YA EXISTENTE

    def test_tabla_existente(self):

        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute("""
                CREATE TABLE politicas_proyecto (
                    proyecto_id INTEGER PRIMARY KEY
                )
            """)

            conexion.commit()

        with self.assertRaisesRegex(
            ValueError,
            "La tabla de politicas ya existe"
        ):
            self.ejecutar_ensayo()


# =====================================
# EJECUTAR PRUEBAS
# =====================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
