import unittest
from unittest.mock import Mock

from politicas_proyectos_v35 import verificar_objetivo_proyecto


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE POLITICAS POR PROYECTO
# =====================================

class PruebasPoliticasProyectos(unittest.TestCase):

    def setUp(self):

        self.politicas = {
            "web_demo": {
                "dominios": {"example.org"},
                "puertos": {443},
                "protocolos": {"https"}
            },
            "api_demo": {
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

    def test_web_permitido(self):

        resultado = verificar_objetivo_proyecto(
            "web_demo",
            "https://example.org/inicio",
            self.politicas,
            self.resolver
        )

        self.assertEqual(resultado["puerto"], 443)
        self.resolver.assert_called_once_with(
            "example.org"
        )

    # PRUEBA 2: PROYECTO API PERMITIDO

    def test_api_permitida(self):

        resultado = verificar_objetivo_proyecto(
            "api_demo",
            "https://example.net:8443/docs",
            self.politicas,
            self.resolver
        )

        self.assertEqual(resultado["puerto"], 8443)
        self.resolver.assert_called_once_with(
            "example.net"
        )

    # PRUEBA 3: WEB NO PUEDE USAR DOMINIO API

    def test_web_no_puede_usar_api(self):

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "web_demo",
                "https://example.net",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 4: API NO PUEDE USAR DOMINIO WEB

    def test_api_no_puede_usar_web(self):

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "api_demo",
                "https://example.org",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 5: PUERTO API INCORRECTO

    def test_puerto_api_incorrecto(self):

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "api_demo",
                "https://example.net",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 6: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "desconocido",
                "https://example.org",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 7: REGISTRO DE POLITICAS INVALIDO

    def test_registro_invalido(self):

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "web_demo",
                "https://example.org",
                None,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 8: POLITICA INCOMPLETA

    def test_politica_incompleta(self):

        politicas = {
            "web_demo": {
                "dominios": {"example.org"},
                "puertos": {443}
            }
        }

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "web_demo",
                "https://example.org",
                politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 9: HTTP NO AUTORIZADO

    def test_http_no_autorizado(self):

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "web_demo",
                "http://example.org:443",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 10: RESPUESTA DNS PRIVADA

    def test_dns_privado(self):

        resolver = Mock(
            return_value=["192.168.1.10"]
        )

        with self.assertRaises(ValueError):
            verificar_objetivo_proyecto(
                "web_demo",
                "https://example.org",
                self.politicas,
                resolver
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
