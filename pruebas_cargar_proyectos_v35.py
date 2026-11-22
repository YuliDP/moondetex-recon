import unittest
import sqlite3

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from unittest.mock import patch

from cargar_proyectos_reales_v35 import cargar_proyectos_reales


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE CARGA DE PROYECTOS
# =====================================

class PruebasCargarProyectos(unittest.TestCase):

    def setUp(self):

        # Crear una carpeta temporal dentro de MoonDetex
        carpeta = Path(__file__).resolve().parent

        self.temporal = TemporaryDirectory(
            prefix="prueba_proyectos_",
            dir=carpeta
        )

        self.addCleanup(self.temporal.cleanup)

        self.db_prueba = (
            Path(self.temporal.name) / "prueba.db"
        )

        # Crear una base de datos de prueba
        with closing(
            sqlite3.connect(self.db_prueba)
        ) as conexion:

            conexion.execute("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT,
                    alcance TEXT
                )
            """)

            conexion.commit()

        # Sustituir temporalmente la ruta de la BD
        parche = patch(
            "cargar_proyectos_reales_v35.DB",
            self.db_prueba
        )

        parche.start()
        self.addCleanup(parche.stop)

    def agregar_proyecto(self, id, nombre, alcance):

        with closing(
            sqlite3.connect(self.db_prueba)
        ) as conexion:

            conexion.execute(
                "INSERT INTO proyectos "
                "(id, nombre, alcance) VALUES (?, ?, ?)",
                (id, nombre, alcance)
            )

            conexion.commit()

    # PRUEBA 1: SIN PROYECTOS

    def test_sin_proyectos(self):

        resultado = cargar_proyectos_reales()

        self.assertEqual(resultado, [])

    # PRUEBA 2: CARGAR UN PROYECTO

    def test_cargar_proyecto(self):

        self.agregar_proyecto(
            1, "Laboratorio Web", "Pruebas locales"
        )

        resultado = cargar_proyectos_reales()

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["id"], 1)
        self.assertEqual(
            resultado[0]["nombre"],
            "Laboratorio Web"
        )

    # PRUEBA 3: POLITICA PENDIENTE

    def test_politica_pendiente(self):

        self.agregar_proyecto(
            1, "Laboratorio Web", "Pruebas locales"
        )

        resultado = cargar_proyectos_reales()

        self.assertFalse(
            resultado[0]["politica_configurada"]
        )

    # PRUEBA 4: CONSERVAR EL ALCANCE

    def test_conservar_alcance(self):

        self.agregar_proyecto(
            1, "Laboratorio", "Entorno local"
        )

        resultado = cargar_proyectos_reales()

        self.assertEqual(
            resultado[0]["alcance"],
            "Entorno local"
        )

    # PRUEBA 5: VARIOS PROYECTOS ORDENADOS

    def test_varios_proyectos(self):

        self.agregar_proyecto(
            2, "Proyecto API", "API local"
        )

        self.agregar_proyecto(
            1, "Proyecto Web", "Web local"
        )

        resultado = cargar_proyectos_reales()

        self.assertEqual(
            [proyecto["id"] for proyecto in resultado],
            [1, 2]
        )

    # PRUEBA 6: BASE DE DATOS INEXISTENTE

    def test_base_inexistente(self):

        self.db_prueba.unlink()

        with self.assertRaises(FileNotFoundError):
            cargar_proyectos_reales()


if __name__ == "__main__":
    unittest.main(verbosity=2)
