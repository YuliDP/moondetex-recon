import unittest
from unittest.mock import Mock

from resolver_dns_v34 import comprobar_resolucion


# =====================================
# MOONDETEX - CLASE 34
# PRUEBAS DEL RESOLUTOR DNS
# =====================================

class PruebasResolverDNS(unittest.TestCase):

    def setUp(self):
        self.permitidos = {"example.org"}
        self.url = "https://example.org/inicio"

    # PRUEBA 1: IPv4 GLOBAL

    def test_ipv4_global(self):

        resolver = Mock(return_value=["8.8.8.8"])

        resultado = comprobar_resolucion(
            self.url,
            self.permitidos,
            resolver
        )

        self.assertEqual(resultado, ["8.8.8.8"])
        resolver.assert_called_once_with("example.org")

    # PRUEBA 2: IPv6 GLOBAL

    def test_ipv6_global(self):

        resolver = Mock(
            return_value=["2001:4860:4860::8888"]
        )

        resultado = comprobar_resolucion(
            self.url,
            self.permitidos,
            resolver
        )

        self.assertEqual(
            resultado,
            ["2001:4860:4860::8888"]
        )

    # PRUEBA 3: IP PRIVADA

    def test_ip_privada(self):

        resolver = Mock(
            return_value=["192.168.1.10"]
        )

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

    # PRUEBA 4: DNS MIXTO

    def test_dns_mixto(self):

        resolver = Mock(
            return_value=["8.8.8.8", "10.0.0.5"]
        )

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

    # PRUEBA 5: SIN RESPUESTAS DNS

    def test_sin_respuestas(self):

        resolver = Mock(return_value=[])

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

    # PRUEBA 6: DOMINIO NO AUTORIZADO

    def test_dominio_no_autorizado(self):

        resolver = Mock(return_value=["8.8.8.8"])

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                "https://otro-dominio.org",
                self.permitidos,
                resolver
            )

        resolver.assert_not_called()

    # PRUEBA 7: PROTOCOLO INVALIDO

    def test_protocolo_invalido(self):

        resolver = Mock(return_value=["8.8.8.8"])

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                "ftp://example.org",
                self.permitidos,
                resolver
            )

        resolver.assert_not_called()

    # PRUEBA 8: RESPUESTA DNS INVALIDA

    def test_respuesta_invalida(self):

        resolver = Mock(
            return_value=["999.999.999.999"]
        )

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

  
    # PRUEBA 9: ERROR DE RESOLUCION DNS

    def test_error_resolucion_dns(self):

        resolver = Mock(
            side_effect=OSError(
                "Servicio DNS no disponible"
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "No se pudo resolver el dominio"
        ):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

        resolver.assert_called_once_with(
            "example.org"
        )

  
    # PRUEBA 10: RESPUESTA DNS NULA

    def test_respuesta_dns_nula(self):

        resolver = Mock(return_value=None)

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

    # PRUEBA 11: RESPUESTA EN TEXTO

    def test_respuesta_dns_texto(self):

        resolver = Mock(return_value="8.8.8.8")

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

    # PRUEBA 12: LISTA CON DATO INCORRECTO

    def test_lista_con_dato_incorrecto(self):

        resolver = Mock(
            return_value=["8.8.8.8", None]
        )

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

    # PRUEBA 13: IPv6 DE ENLACE LOCAL

    def test_ipv6_enlace_local(self):

        resolver = Mock(
            return_value=["fe80::1"]
        )

        with self.assertRaises(ValueError):
            comprobar_resolucion(
                self.url,
                self.permitidos,
                resolver
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)
