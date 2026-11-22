import unittest
from unittest.mock import Mock

from verificador_preconexion_v35 import (
    verificar_cadena_local
)


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DEL VERIFICADOR PRECONEXION
# =====================================

class PruebasPreconexion(unittest.TestCase):

    def setUp(self):

        self.url = "https://example.org/inicio"
        self.dominios = {"example.org"}
        self.puertos = {443}

        self.resolver = Mock(
            return_value=["8.8.8.8"]
        )

    # PRUEBA 1: OBJETIVO AUTORIZADO

    def test_objetivo_permitido(self):

        resultado = verificar_cadena_local(
            self.url,
            self.dominios,
            self.puertos,
            self.resolver
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["puerto"], 443)
        self.assertEqual(resultado[0]["ips"], ["8.8.8.8"])

    # PRUEBA 2: REDIRECCION PERMITIDA

    def test_redireccion_permitida(self):

        resultado = verificar_cadena_local(
            self.url,
            self.dominios,
            self.puertos,
            self.resolver,
            "/ayuda"
        )

        self.assertEqual(len(resultado), 2)

        self.assertEqual(
            resultado[1]["url"],
            "https://example.org/ayuda"
        )

    # PRUEBA 3: REDIRECCION EXTERNA

    def test_redireccion_externa(self):

        with self.assertRaises(ValueError):

            verificar_cadena_local(
                self.url,
                self.dominios,
                self.puertos,
                self.resolver,
                "https://otro-dominio.org"
            )

        self.resolver.assert_called_once_with(
            "example.org"
        )

    # PRUEBA 4: PUERTO NO AUTORIZADO

    def test_puerto_no_autorizado(self):

        with self.assertRaises(ValueError):

            verificar_cadena_local(
                self.url,
                self.dominios,
                self.puertos,
                self.resolver,
                "https://example.org:8080"
            )

    # PRUEBA 5: DOMINIO INICIAL EXTERNO

    def test_dominio_inicial_externo(self):

        with self.assertRaises(ValueError):

            verificar_cadena_local(
                "https://otro-dominio.org",
                self.dominios,
                self.puertos,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 6: PUERTO INICIAL NO AUTORIZADO

    def test_puerto_inicial_invalido(self):

        with self.assertRaises(ValueError):

            verificar_cadena_local(
                "https://example.org:8080",
                self.dominios,
                self.puertos,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 7: IP PRIVADA

    def test_ip_privada(self):

        self.resolver.return_value = [
            "192.168.1.10"
        ]

        with self.assertRaises(ValueError):

            verificar_cadena_local(
                self.url,
                self.dominios,
                self.puertos,
                self.resolver
            )

    # PRUEBA 8: DNS MIXTO

    def test_dns_mixto(self):

        self.resolver.return_value = [
            "8.8.8.8",
            "10.0.0.5"
        ]

        with self.assertRaises(ValueError):

            verificar_cadena_local(
                self.url,
                self.dominios,
                self.puertos,
                self.resolver
            )

    # PRUEBA 9: ERROR DNS

    def test_error_dns(self):

        self.resolver.side_effect = OSError(
            "Servicio DNS no disponible"
        )

        with self.assertRaisesRegex(
            ValueError,
            "No se pudo resolver el dominio"
        ):

            verificar_cadena_local(
                self.url,
                self.dominios,
                self.puertos,
                self.resolver
            )

    # PRUEBA 10: REDIRECCION HTTP NO AUTORIZADA

    def test_redireccion_http(self):

        with self.assertRaises(ValueError):

            verificar_cadena_local(
                self.url,
                self.dominios,
                self.puertos,
                self.resolver,
                "http://example.org/ayuda"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
