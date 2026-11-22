import sqlite3
import tempfile
import unittest

from pathlib import Path
from contextlib import closing
from unittest.mock import patch

import gestor_proyectos


# =====================================
# MOONDETEX V0.20
# PRUEBAS SEGURAS DE PROYECTOS
# =====================================

class PruebasProyectos(unittest.TestCase):

    def setUp(self):

        # Crear una carpeta temporal
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.bd_prueba = (
            Path(self.temporal.name)
            / "proyectos_prueba.db"
        )

        # Crear base de datos de laboratorio
        with closing(sqlite3.connect(self.bd_prueba)) as con:

            con.execute("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    alcance TEXT NOT NULL,
                    notas TEXT NOT NULL DEFAULT '',
                    fecha TEXT NOT NULL DEFAULT
                        (datetime('now','localtime'))
                )
            """)

            con.commit()

        # Redirigir el gestor a la base temporal
        parche = patch.object(
            gestor_proyectos,
            "conectar",
            self.conectar_prueba
        )

        parche.start()
        self.addCleanup(parche.stop)

    def conectar_prueba(self):

        conexion = sqlite3.connect(self.bd_prueba)
        conexion.execute("PRAGMA foreign_keys = ON")

        return conexion

    # =====================================
    # PRUEBA 1: GUARDAR Y CONSULTAR
    # =====================================

    def test_guardar_y_consultar(self):

        identificador = gestor_proyectos.guardar_proyecto(
            "Proyecto de prueba",
            "Laboratorio local",
            "Prueba automatica"
        )

        proyectos = gestor_proyectos.obtener_proyectos()

        self.assertEqual(len(proyectos), 1)

        self.assertEqual(
            proyectos[0][0],
            identificador
        )

        self.assertEqual(
            proyectos[0][1],
            "Proyecto de prueba"
        )

    # =====================================
    # PRUEBA 2: RECHAZAR DATOS VACIOS
    # =====================================

    def test_datos_obligatorios(self):

        with self.assertRaises(ValueError):
            gestor_proyectos.guardar_proyecto(
                "",
                "Laboratorio",
                ""
            )

        with self.assertRaises(ValueError):
            gestor_proyectos.guardar_proyecto(
                "Proyecto",
                "",
                ""
            )

        self.assertEqual(
            len(gestor_proyectos.obtener_proyectos()),
            0
        )

    # =====================================
    # PRUEBA 3: ELIMINAR CORRECTAMENTE
    # =====================================

    def test_eliminar_proyecto(self):

        primero = gestor_proyectos.guardar_proyecto(
            "Proyecto A",
            "Laboratorio A",
            ""
        )

        segundo = gestor_proyectos.guardar_proyecto(
            "Proyecto B",
            "Laboratorio B",
            ""
        )

        eliminado = gestor_proyectos.eliminar_proyecto_bd(
            primero
        )

        self.assertTrue(eliminado)

        proyectos = gestor_proyectos.obtener_proyectos()

        self.assertEqual(len(proyectos), 1)

        self.assertEqual(
            proyectos[0][0],
            segundo
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
