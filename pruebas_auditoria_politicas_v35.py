import unittest
import sqlite3
import json

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from unittest.mock import patch

from auditar_politicas_reales_v35 import (
    auditar_politicas_reales
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE AUDITORIA DE POLITICAS
# =====================================

class PruebasAuditoriaPoliticas(unittest.TestCase):

    def setUp(self):

        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.db = (
            Path(self.temporal.name) / "pruebas.db"
        )

        # Crear proyecto ficticio
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

        # Reemplazar solo durante estas pruebas
        parche = patch(
            "auditar_politicas_reales_v35.DB",
            self.db
        )

        parche.start()
        self.addCleanup(parche.stop)

    def crear_tabla_politicas(self):

        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute("""
                CREATE TABLE politicas_proyecto (
                    proyecto_id INTEGER PRIMARY KEY,
                    dominios TEXT NOT NULL,
                    puertos TEXT NOT NULL,
                    protocolos TEXT NOT NULL,
                    FOREIGN KEY (proyecto_id)
                        REFERENCES proyectos(id)
                )
            """)

            conexion.commit()

    def guardar_politica(
        self, proyecto_id=1,
        dominios=None, puertos=None, protocolos=None
    ):

        if dominios is None:
            dominios = ["example.org"]

        if puertos is None:
            puertos = [443]

        if protocolos is None:
            protocolos = ["https"]

        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute(
                """
                INSERT INTO politicas_proyecto
                VALUES (?, ?, ?, ?)
                """,
                (
                    proyecto_id,
                    json.dumps(dominios),
                    json.dumps(puertos),
                    json.dumps(protocolos)
                )
            )

            conexion.commit()

    # PRUEBA 1: NO EXISTE TABLA DE POLITICAS

    def test_sin_tabla_politicas(self):

        resultado = auditar_politicas_reales()

        self.assertIn(
            "PENDIENTE",
            resultado[0]["estado"]
        )

        self.assertEqual(
            resultado[0]["analisis_red"],
            "BLOQUEADO"
        )

    # PRUEBA 2: TABLA EXISTE, SIN POLITICA

    def test_politica_pendiente(self):

        self.crear_tabla_politicas()

        resultado = auditar_politicas_reales()

        self.assertEqual(
            resultado[0]["estado"],
            "PENDIENTE"
        )

    # PRUEBA 3: POLITICA VALIDA

    def test_politica_valida(self):

        self.crear_tabla_politicas()
        self.guardar_politica()

        resultado = auditar_politicas_reales()

        self.assertEqual(
            resultado[0]["estado"],
            "CONFIGURADA"
        )

        self.assertEqual(
            resultado[0]["analisis_red"],
            "BLOQUEADO"
        )

    # PRUEBA 4: JSON INCORRECTO

    def test_json_incorrecto(self):

        self.crear_tabla_politicas()
        self.guardar_politica()

        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute(
                "UPDATE politicas_proyecto "
                "SET dominios = ? WHERE proyecto_id = 1",
                ("JSON_INVALIDO",)
            )

            conexion.commit()

        resultado = auditar_politicas_reales()

        self.assertEqual(
            resultado[0]["estado"],
            "INVALIDA"
        )

    # PRUEBA 5: PUERTO FUERA DE RANGO

    def test_puerto_invalido(self):

        self.crear_tabla_politicas()
        self.guardar_politica(puertos=[70000])

        resultado = auditar_politicas_reales()

        self.assertEqual(
            resultado[0]["estado"],
            "INVALIDA"
        )

    # PRUEBA 6: PROYECTOS INDEPENDIENTES

    def test_proyectos_independientes(self):

        self.crear_tabla_politicas()

        with closing(sqlite3.connect(self.db)) as conexion:

            conexion.execute(
                "INSERT INTO proyectos (id, nombre) "
                "VALUES (?, ?)",
                (2, "Laboratorio API")
            )

            conexion.commit()

        # Solamente el proyecto 2 tiene politica
        self.guardar_politica(
            proyecto_id=2,
            dominios=["example.net"],
            puertos=[8443]
        )

        resultado = auditar_politicas_reales()

        self.assertEqual(
            resultado[0]["estado"],
            "PENDIENTE"
        )

        self.assertEqual(
            resultado[1]["estado"],
            "CONFIGURADA"
        )

    # PRUEBA 7: BASE DE DATOS INEXISTENTE

    def test_base_inexistente(self):

        self.db.unlink()

        with self.assertRaises(FileNotFoundError):
            auditar_politicas_reales()

    # PRUEBA 8: NO MODIFICAR LA BASE

    def test_base_sin_modificaciones(self):

        self.crear_tabla_politicas()

        contenido_antes = self.db.read_bytes()

        auditar_politicas_reales()

        contenido_despues = self.db.read_bytes()

        self.assertEqual(
            contenido_antes,
            contenido_despues
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
