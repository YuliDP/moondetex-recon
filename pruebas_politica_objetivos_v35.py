import unittest
from unittest.mock import Mock

from politica_objetivos_v35 import aplicar_politica_local


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE POLITICAS DE OBJETIVOS
# =====================================

class PruebasPoliticaObjetivos(unittest.TestCase):

    def setUp(self):

        self.politica = {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"https"}
        }

        self.resolver = Mock(
            return_value=["8.8.8.8"]
        )

    # PRUEBA 1: OBJETIVO PERMITIDO

    def test_objetivo_permitido(self):

        resultado = aplicar_politica_local(
            "https://example.org/inicio",
            self.politica,
            self.resolver
        )

        self.assertEqual(resultado["puerto"], 443)
        self.assertEqual(resultado["ips"], ["8.8.8.8"])

    # PRUEBA 2: HTTP EN PUERTO 443

    def test_http_puerto_443(self):

        with self.assertRaisesRegex(
            ValueError,
            "Protocolo no autorizado"
        ):
            aplicar_politica_local(
                "http://example.org:443",
                self.politica,
                self.resolver
            )

    # PRUEBA 3: HTTP PREDETERMINADO

    def test_http_no_autorizado(self):

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "http://example.org",
                self.politica,
                self.resolver
            )

    # PRUEBA 4: PUERTO NO AUTORIZADO

    def test_puerto_no_autorizado(self):

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "https://example.org:8080",
                self.politica,
                self.resolver
            )

    # PRUEBA 5: DOMINIO EXTERNO

    def test_dominio_externo(self):

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "https://otro-dominio.org",
                self.politica,
                self.resolver
            )

    # PRUEBA 6: POLITICA SIN PROTOCOLOS

    def test_sin_protocolos(self):

        politica = {
            "dominios": {"example.org"},
            "puertos": {443}
        }

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "https://example.org",
                politica,
                self.resolver
            )

    # PRUEBA 7: PROTOCOLO INVALIDO EN POLITICA

    def test_protocolo_invalido(self):

        politica = {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"ftp"}
        }

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "https://example.org",
                politica,
                self.resolver
            )

    # PRUEBA 8: LISTA DE PUERTOS VACIA

    def test_puertos_vacios(self):

        politica = {
            "dominios": {"example.org"},
            "puertos": set(),
            "protocolos": {"https"}
        }

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "https://example.org",
                politica,
                self.resolver
            )

    # PRUEBA 9: DIRECCION IP PRIVADA

    def test_ip_privada(self):

        self.resolver.return_value = [
            "192.168.1.10"
        ]

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "https://example.org",
                self.politica,
                self.resolver
            )

    # PRUEBA 10: BLOQUEAR ANTES DE CONSULTAR DNS

    def test_no_consultar_dns_si_http(self):

        with self.assertRaises(ValueError):
            aplicar_politica_local(
                "http://example.org:443",
                self.politica,
                self.resolver
            )

        self.resolver.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
