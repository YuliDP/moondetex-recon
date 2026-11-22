
import unittest
import sqlite3
import json

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from verificar_politica_guardada_v35 import (
    verificar_objetivo_guardado
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE POLITICAS GUARDADAS
# =====================================

class PruebasPoliticaGuardada(unittest.TestCase):

    def setUp(self):

        # Crear base de datos temporal
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.db = Path(
            self.temporal.name
        ) / "pruebas.db"

        self.conexion = sqlite3.connect(self.db)
        self.addCleanup(self.conexion.close)

        self.conexion.execute(
            "PRAGMA foreign_keys = ON"
        )

        # Crear las tablas
        self.conexion.execute("""
            CREATE TABLE proyectos (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL
            )
        """)

        self.conexion.execute("""
            CREATE TABLE politicas_proyecto (
                proyecto_id INTEGER PRIMARY KEY,
                dominios TEXT NOT NULL,
                puertos TEXT NOT NULL,
                protocolos TEXT NOT NULL,
                FOREIGN KEY (proyecto_id)
                    REFERENCES proyectos(id)
            )
        """)

        # Proyecto 1 sin politica
        # Proyecto 2 con politica
        self.conexion.executemany(
            "INSERT INTO proyectos VALUES (?, ?)",
            [
                (1, "Laboratorio Web"),
                (2, "Laboratorio API")
            ]
        )

        self.conexion.execute(
            """
            INSERT INTO politicas_proyecto
            VALUES (?, ?, ?, ?)
            """,
            (
                2,
                json.dumps(["example.net"]),
                json.dumps([8443]),
                json.dumps(["https"])
            )
        )

        self.conexion.commit()

        # Simular el DNS
        self.resolver = Mock(
            return_value=["1.1.1.1"]
        )

    # PRUEBA 1: API AUTORIZADA

    def test_api_autorizada(self):

        resultado = verificar_objetivo_guardado(
            self.conexion,
            2,
            "https://example.net:8443/docs",
            self.resolver
        )

        self.assertEqual(resultado["puerto"], 8443)
        self.assertEqual(resultado["ips"], ["1.1.1.1"])

        self.resolver.assert_called_once_with(
            "example.net"
        )

    # PRUEBA 2: PUERTO NO AUTORIZADO

    def test_puerto_no_autorizado(self):

        with self.assertRaisesRegex(
            ValueError,
            "Puerto no autorizado"
        ):
            verificar_objetivo_guardado(
                self.conexion,
                2,
                "https://example.net",
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 3: PROYECTO SIN POLITICA

    def test_proyecto_sin_politica(self):

        with self.assertRaisesRegex(
            ValueError,
            "no tiene una politica"
        ):
            verificar_objetivo_guardado(
                self.conexion,
                1,
                "https://example.org",
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 4: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaisesRegex(
            ValueError,
            "El proyecto no existe"
        ):
            verificar_objetivo_guardado(
                self.conexion,
                99,
                "https://example.net:8443",
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 5: DOMINIO NO AUTORIZADO

    def test_dominio_no_autorizado(self):

        with self.assertRaises(ValueError):
            verificar_objetivo_guardado(
                self.conexion,
                2,
                "https://example.org:8443",
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 6: PROTOCOLO NO AUTORIZADO

    def test_protocolo_no_autorizado(self):

        with self.assertRaisesRegex(
            ValueError,
            "Protocolo no autorizado"
        ):
            verificar_objetivo_guardado(
                self.conexion,
                2,
                "http://example.net:8443",
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 7: DIRECCION IP PRIVADA

    def test_ip_privada(self):

        self.resolver.return_value = [
            "192.168.1.10"
        ]

        with self.assertRaises(ValueError):
            verificar_objetivo_guardado(
                self.conexion,
                2,
                "https://example.net:8443",
                self.resolver
            )

    # PRUEBA 8: POLITICA ALMACENADA INVALIDA

    def test_politica_invalida(self):

        # Modificar solo la base temporal
        self.conexion.execute(
            """
            UPDATE politicas_proyecto
            SET puertos = ?
            WHERE proyecto_id = ?
            """,
            (json.dumps([70000]), 2)
        )

        self.conexion.commit()

        with self.assertRaisesRegex(
            ValueError,
            "puerto invalido"
        ):
            verificar_objetivo_guardado(
                self.conexion,
                2,
                "https://example.net:8443",
                self.resolver
            )

        self.resolver.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
