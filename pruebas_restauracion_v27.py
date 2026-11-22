import io
import sqlite3
import tempfile
import unittest

from pathlib import Path
from contextlib import closing, redirect_stdout
from unittest.mock import patch

import simular_restauracion_v27 as simulador


# =====================================
# MOONDETEX - CLASE 27
# PRUEBAS DE RESTAURACION
# =====================================

class PruebasRestauracion(unittest.TestCase):

    def setUp(self):

        # Crear una carpeta temporal
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.carpeta = Path(self.temporal.name)
        self.respaldos = self.carpeta / "respaldos"
        self.respaldos.mkdir()

        # Redirigir las pruebas al laboratorio
        parche = patch.object(
            simulador,
            "RESPALDOS",
            self.respaldos
        )

        parche.start()
        self.addCleanup(parche.stop)


    def crear_base_prueba(self, relacion_correcta=True):

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
                    proyecto_id INTEGER,
                    FOREIGN KEY(proyecto_id)
                        REFERENCES proyectos(id)
                );

                CREATE TABLE historial_analisis (
                    id INTEGER PRIMARY KEY
                );

                INSERT INTO proyectos
                VALUES (1, 'Laboratorio');

                INSERT INTO historial_analisis
                VALUES (1);
            """)

            if relacion_correcta:
                proyecto_id = 1
            else:
                proyecto_id = 999

            con.execute(
                "INSERT INTO hallazgos "
                "(id, proyecto_id) VALUES (?, ?)",
                (1, proyecto_id)
            )

            con.commit()

        return archivo


    # PRUEBA 1: RESTAURACION CORRECTA

    def test_restauracion_correcta(self):

        archivo = self.crear_base_prueba()

        hash_antes = simulador.calcular_hash(archivo)

        salida = io.StringIO()

        with redirect_stdout(salida):
            simulador.simular_restauracion()

        texto = salida.getvalue()

        self.assertIn("SIMULACION APROBADA", texto)

        hash_despues = simulador.calcular_hash(archivo)

        self.assertEqual(hash_antes, hash_despues)


    # PRUEBA 2: NO EXISTEN RESPALDOS

    def test_sin_respaldos(self):

        with redirect_stdout(io.StringIO()):

            with self.assertRaises(FileNotFoundError):
                simulador.simular_restauracion()


    # PRUEBA 3: RELACION INCORRECTA

    def test_relacion_incorrecta(self):

        self.crear_base_prueba(
            relacion_correcta=False
        )

        with redirect_stdout(io.StringIO()):

            with self.assertRaises(RuntimeError):
                simulador.simular_restauracion()


    # PRUEBA 4: ARCHIVO DANADO

    def test_archivo_danado(self):

        archivo = (
            self.respaldos
            / "respaldo_20261025_120000_danado.db"
        )

        archivo.write_bytes(
            b"Archivo ficticio no valido"
        )

        with redirect_stdout(io.StringIO()):

            with self.assertRaises(sqlite3.DatabaseError):
                simulador.simular_restauracion()


if __name__ == "__main__":
    unittest.main(verbosity=2)
