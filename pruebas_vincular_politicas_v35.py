import unittest
from unittest.mock import Mock

from vincular_politicas_v35 import verificar_proyecto_registrado


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE VINCULACION DE POLITICAS
# =====================================

class PruebasVincularPoliticas(unittest.TestCase):

    def setUp(self):

        self.proyectos = [
            {"id": 1, "nombre": "Laboratorio Web"},
            {"id": 2, "nombre": "Laboratorio API"}
        ]

        self.politicas = {
            1: {
                "dominios": {"example.org"},
                "puertos": {443},
                "protocolos": {"https"}
            },
            2: {
                "dominios": {"example.net"},
                "puertos": {8443},
                "protocolos": {"https"}
            }
        }

        self.resolver = Mock(
            side_effect=lambda dominio: {
                "example.org": ["8.8.8.8"],
                "example.net": ["1.1.1.1"]
            }[dominio]
        )

    # PRUEBA 1: PROYECTO WEB PERMITIDO

    def test_proyecto_web(self):

        resultado = verificar_proyecto_registrado(
            1,
            "https://example.org",
            self.proyectos,
            self.politicas,
            self.resolver
        )

        self.assertEqual(resultado["puerto"], 443)

    # PRUEBA 2: PROYECTO API PERMITIDO

    def test_proyecto_api(self):

        resultado = verificar_proyecto_registrado(
            2,
            "https://example.net:8443",
            self.proyectos,
            self.politicas,
            self.resolver
        )

        self.assertEqual(resultado["puerto"], 8443)

    # PRUEBA 3: WEB NO PUEDE USAR API

    def test_web_no_puede_usar_api(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                1,
                "https://example.net:8443",
                self.proyectos,
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 4: API NO PUEDE USAR WEB

    def test_api_no_puede_usar_web(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                2,
                "https://example.org",
                self.proyectos,
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 5: PUERTO INCORRECTO

    def test_puerto_incorrecto(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                2,
                "https://example.net",
                self.proyectos,
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 6: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                99,
                "https://example.org",
                self.proyectos,
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 7: IDENTIFICADORES DUPLICADOS

    def test_ids_duplicados(self):

        proyectos = [
            {"id": 1, "nombre": "Web"},
            {"id": 1, "nombre": "Otro"}
        ]

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                1,
                "https://example.org",
                proyectos,
                self.politicas,
                self.resolver
            )

    # PRUEBA 8: IDENTIFICADOR INVALIDO

    def test_id_invalido(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                "1",
                "https://example.org",
                self.proyectos,
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 9: PROYECTO SIN POLITICA

    def test_proyecto_sin_politica(self):

        politicas = {
            2: self.politicas[2]
        }

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                1,
                "https://example.org",
                self.proyectos,
                politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 10: DIRECCION IP PRIVADA

    def test_ip_privada(self):

        resolver = Mock(
            return_value=["192.168.1.10"]
        )

        with self.assertRaises(ValueError):
            verificar_proyecto_registrado(
                1,
                "https://example.org",
                self.proyectos,
                self.politicas,
                resolver
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
