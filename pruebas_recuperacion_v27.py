import io
import sqlite3
import tempfile
import unittest

from pathlib import Path
from contextlib import closing, redirect_stdout
from unittest.mock import patch

import probar_recuperacion_v27 as recuperacion


# =====================================
# MOONDETEX - CLASE 27
# PRUEBAS AUTOMATICAS DE RECUPERACION
# =====================================

class PruebasRecuperacion(unittest.TestCase):

    def setUp(self):

        # Crear carpeta temporal
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.carpeta = Path(self.temporal.name)
        self.respaldos = self.carpeta / "respaldos"
        self.respaldos.mkdir()

        # Usar solo la carpeta temporal
        parche = patch.object(
            recuperacion,
            "RESPALDOS",
            self.respaldos
        )

        parche.start()
        self.addCleanup(parche.stop)


    def crear_base_prueba(self):

        archivo = (
            self.respaldos
            / "respaldo_20261025_120000_prueba.db"
        )

        with closing(sqlite3.connect(archivo)) as con:

            con.executescript("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT
                );

                CREATE TABLE hallazgos (
                    id INTEGER PRIMARY KEY,
                    titulo TEXT
                );

                CREATE TABLE historial_analisis (
                    id INTEGER PRIMARY KEY
                );

                INSERT INTO proyectos
                VALUES (1, 'Laboratorio');

                INSERT INTO hallazgos
                VALUES (1, 'Observacion de prueba');

                INSERT INTO historial_analisis
                VALUES (1);
            """)

            con.commit()

        return archivo


    # PRUEBA 1: RECUPERACION CORRECTA

    def test_recuperacion_correcta(self):

        archivo = self.crear_base_prueba()

        hash_antes = recuperacion.calcular_hash(
            archivo
        )

        salida = io.StringIO()

        with redirect_stdout(salida):
            recuperacion.probar_recuperacion()

        texto = salida.getvalue()

        self.assertIn(
            "RECUPERACION DE PRUEBA: APROBADA",
            texto
        )

        self.assertIn(
            "Integridad SQLite: OK",
            texto
        )

        hash_despues = recuperacion.calcular_hash(
            archivo
        )

        self.assertEqual(hash_antes, hash_despues)


    # PRUEBA 2: RESPALDO INEXISTENTE

    def test_sin_respaldos(self):

        with redirect_stdout(io.StringIO()):

            with self.assertRaises(FileNotFoundError):
                recuperacion.probar_recuperacion()


    # PRUEBA 3: RESPALDO DANADO

    def test_respaldo_danado(self):

        archivo = (
            self.respaldos
            / "respaldo_20261025_120000_danado.db"
        )

        # Crear datos ficticios invalidos
        archivo.write_bytes(
            b"Este archivo no es una base SQLite"
        )

        with redirect_stdout(io.StringIO()):

            with self.assertRaises(sqlite3.DatabaseError):
                recuperacion.probar_recuperacion()


if __name__ == "__main__":
    unittest.main(verbosity=2)
