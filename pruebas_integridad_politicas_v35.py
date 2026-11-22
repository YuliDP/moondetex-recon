import unittest
import sqlite3

from pathlib import Path
from tempfile import TemporaryDirectory

from laboratorio_politicas_sqlite_v35 import (
    crear_tablas,
    consultar_politica
)

from guardado_seguro_politicas_v35 import (
    guardar_politica_validada
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE INTEGRIDAD REFERENCIAL
# =====================================

class PruebasIntegridadPoliticas(unittest.TestCase):

    def setUp(self):

        # Crear una base de datos temporal
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.db = (
            Path(self.temporal.name) / "pruebas.db"
        )

        self.conexion = sqlite3.connect(self.db)
        self.addCleanup(self.conexion.close)

        # Activar las claves foraneas
        self.conexion.execute(
            "PRAGMA foreign_keys = ON"
        )

        crear_tablas(self.conexion)

        # Crear proyectos ficticios
        self.conexion.executemany(
            "INSERT INTO proyectos (id, nombre) "
            "VALUES (?, ?)",
            [
                (1, "Laboratorio Web"),
                (2, "Laboratorio API")
            ]
        )

        self.conexion.commit()

        self.politica = {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"https"}
        }

    # PRUEBA 1: PROYECTO EXISTENTE

    def test_proyecto_existente(self):

        guardar_politica_validada(
            self.conexion, 1, self.politica
        )

        resultado = consultar_politica(
            self.conexion, 1
        )

        self.assertEqual(resultado, self.politica)

    # PRUEBA 2: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaises(sqlite3.IntegrityError):
            guardar_politica_validada(
                self.conexion, 99, self.politica
            )

        self.conexion.rollback()

        self.assertIsNone(
            consultar_politica(self.conexion, 99)
        )

    # PRUEBA 3: POLITICA DUPLICADA

    def test_politica_duplicada(self):

        guardar_politica_validada(
            self.conexion, 1, self.politica
        )

        with self.assertRaises(sqlite3.IntegrityError):
            guardar_politica_validada(
                self.conexion, 1, self.politica
            )

        self.conexion.rollback()

    # PRUEBA 4: PROYECTO SIN POLITICA

    def test_proyecto_sin_politica(self):

        resultado = consultar_politica(
            self.conexion, 2
        )

        self.assertIsNone(resultado)

    # PRUEBA 5: PROTEGER LA ELIMINACION

    def test_eliminacion_protegida(self):

        guardar_politica_validada(
            self.conexion, 1, self.politica
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.conexion.execute(
                "DELETE FROM proyectos WHERE id = ?",
                (1,)
            )

        self.conexion.rollback()

    # PRUEBA 6: CONSERVAR LOS DATOS

    def test_datos_conservados(self):

        guardar_politica_validada(
            self.conexion, 1, self.politica
        )

        try:
            self.conexion.execute(
                "DELETE FROM proyectos WHERE id = ?",
                (1,)
            )

        except sqlite3.IntegrityError:
            self.conexion.rollback()

        proyecto = self.conexion.execute(
            "SELECT id FROM proyectos WHERE id = 1"
        ).fetchone()

        politica = consultar_politica(
            self.conexion, 1
        )

        self.assertEqual(proyecto, (1,))
        self.assertEqual(politica, self.politica)

    # PRUEBA 7: INTEGRIDAD SIN VIOLACIONES

    def test_integridad_correcta(self):

        guardar_politica_validada(
            self.conexion, 1, self.politica
        )

        errores = self.conexion.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        self.assertEqual(errores, [])


# =====================================
# EJECUTAR PRUEBAS
# =====================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
