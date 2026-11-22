import unittest
import sqlite3

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from guardado_seguro_politicas_v35 import (
    guardar_politica_validada
)

from laboratorio_politicas_sqlite_v35 import (
    crear_tablas,
    consultar_politica
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE GUARDADO SEGURO
# =====================================

class PruebasGuardadoSeguro(unittest.TestCase):

    def setUp(self):

        carpeta = Path(__file__).resolve().parent

        self.temporal = TemporaryDirectory(
            prefix="pruebas_guardado_",
            dir=carpeta
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

        crear_tablas(self.conexion)

        self.conexion.execute(
            "INSERT INTO proyectos (id, nombre) "
            "VALUES (?, ?)",
            (1, "Laboratorio")
        )

        self.conexion.commit()

        self.politica = {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"https"}
        }

    # PRUEBA 1: POLITICA CORRECTA

    def test_politica_correcta(self):

        resultado = guardar_politica_validada(
            self.conexion, 1, self.politica
        )

        self.assertTrue(resultado)

        recuperada = consultar_politica(
            self.conexion, 1
        )

        self.assertEqual(
            recuperada,
            self.politica
        )

    # PRUEBA 2: PUERTO FUERA DE RANGO

    def test_puerto_invalido(self):

        politica = {
            **self.politica,
            "puertos": {70000}
        }

        with self.assertRaises(ValueError):
            guardar_politica_validada(
                self.conexion, 1, politica
            )

        self.assertIsNone(
            consultar_politica(self.conexion, 1)
        )

    # PRUEBA 3: DOMINIO INCORRECTO

    def test_dominio_invalido(self):

        politica = {
            **self.politica,
            "dominios": {"dominio..org"}
        }

        with self.assertRaises(ValueError):
            guardar_politica_validada(
                self.conexion, 1, politica
            )

        self.assertIsNone(
            consultar_politica(self.conexion, 1)
        )

    # PRUEBA 4: PROTOCOLO NO PERMITIDO

    def test_protocolo_invalido(self):

        politica = {
            **self.politica,
            "protocolos": {"ftp"}
        }

        with self.assertRaises(ValueError):
            guardar_politica_validada(
                self.conexion, 1, politica
            )

        self.assertIsNone(
            consultar_politica(self.conexion, 1)
        )

    # PRUEBA 5: POLITICA INCOMPLETA

    def test_politica_incompleta(self):

        politica = {
            "dominios": {"example.org"},
            "puertos": {443}
        }

        with self.assertRaises(ValueError):
            guardar_politica_validada(
                self.conexion, 1, politica
            )

    # PRUEBA 6: ID INVALIDO

    def test_id_invalido(self):

        with self.assertRaises(ValueError):
            guardar_politica_validada(
                self.conexion, "1", self.politica
            )

    # PRUEBA 7: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            guardar_politica_validada(
                self.conexion, 99, self.politica
            )

    # PRUEBA 8: CONSERVAR POLITICA ORIGINAL

    def test_conservar_politica(self):

        guardar_politica_validada(
            self.conexion, 1, self.politica
        )

        incorrecta = {
            **self.politica,
            "puertos": {70000}
        }

        with self.assertRaises(ValueError):
            guardar_politica_validada(
                self.conexion, 1, incorrecta
            )

        recuperada = consultar_politica(
            self.conexion, 1
        )

        self.assertEqual(
            recuperada,
            self.politica
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
