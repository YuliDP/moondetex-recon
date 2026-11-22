import io
import sqlite3
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing, redirect_stdout
from unittest.mock import patch

from comparar_datos_migracion_v35 import (
    obtener_huellas,
    comparar_migracion
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE COMPARACION SHA-256
# =====================================

class PruebasComparacionMigracion(unittest.TestCase):

    def setUp(self):

        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.db = Path(self.temporal.name) / "pruebas.db"

        self.conexion = sqlite3.connect(self.db)
        self.addCleanup(self.conexion.close)

        self.conexion.execute("""
            CREATE TABLE proyectos (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL
            )
        """)

        self.conexion.executemany(
            "INSERT INTO proyectos VALUES (?, ?)",
            [
                (1, "Laboratorio Web"),
                (2, "Laboratorio API")
            ]
        )

        self.conexion.commit()

    # PRUEBA 1: DATOS SIN CAMBIOS

    def test_datos_sin_cambios(self):

        antes = obtener_huellas(self.conexion)
        despues = obtener_huellas(self.conexion)

        self.assertEqual(antes, despues)

    # PRUEBA 2: DETECTAR MODIFICACION

    def test_registro_modificado(self):

        antes = obtener_huellas(self.conexion)

        self.conexion.execute(
            "UPDATE proyectos SET nombre = ? WHERE id = 1",
            ("Laboratorio Modificado",)
        )

        self.conexion.commit()

        despues = obtener_huellas(self.conexion)

        self.assertNotEqual(antes, despues)

        # La cantidad no cambio
        self.assertEqual(
            antes["proyectos"]["cantidad"],
            despues["proyectos"]["cantidad"]
        )

    # PRUEBA 3: DETECTAR REGISTRO AGREGADO

    def test_registro_agregado(self):

        antes = obtener_huellas(self.conexion)

        self.conexion.execute(
            "INSERT INTO proyectos VALUES (?, ?)",
            (3, "Laboratorio Nuevo")
        )

        self.conexion.commit()

        despues = obtener_huellas(self.conexion)

        self.assertNotEqual(antes, despues)

    # PRUEBA 4: DETECTAR REGISTRO ELIMINADO

    def test_registro_eliminado(self):

        antes = obtener_huellas(self.conexion)

        self.conexion.execute(
            "DELETE FROM proyectos WHERE id = 2"
        )

        self.conexion.commit()

        despues = obtener_huellas(self.conexion)

        self.assertNotEqual(antes, despues)

    # PRUEBA 5: DETECTAR TABLA AGREGADA

    def test_tabla_agregada(self):

        antes = obtener_huellas(self.conexion)

        self.conexion.execute("""
            CREATE TABLE nueva_tabla (
                id INTEGER PRIMARY KEY
            )
        """)

        self.conexion.commit()

        despues = obtener_huellas(self.conexion)

        self.assertNotEqual(antes, despues)
        self.assertIn("nueva_tabla", despues)

    # PRUEBA 6: MIGRACION SEGURA

    def test_migracion_segura(self):

        contenido_antes = self.db.read_bytes()
        salida = io.StringIO()

        with patch(
            "comparar_datos_migracion_v35.DB",
            self.db
        ):
            with redirect_stdout(salida):
                comparar_migracion()

        contenido_despues = self.db.read_bytes()

        self.assertEqual(
            contenido_antes,
            contenido_despues
        )

        self.assertIn(
            "RESULTADO: COMPARACION APROBADA",
            salida.getvalue()
        )

    # PRUEBA 7: BASE INEXISTENTE

    def test_base_inexistente(self):

        ruta_inexistente = (
            Path(self.temporal.name) / "inexistente.db"
        )

        with patch(
            "comparar_datos_migracion_v35.DB",
            ruta_inexistente
        ):
            with self.assertRaises(FileNotFoundError):
                comparar_migracion()


if __name__ == "__main__":
    unittest.main(verbosity=2)
