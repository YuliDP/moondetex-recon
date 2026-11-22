import unittest
from unittest.mock import Mock

from verificador_dns_estable_v35 import verificar_dns_estable


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DE ESTABILIDAD DNS
# =====================================

class PruebasDNSEstable(unittest.TestCase):

    def setUp(self):

        self.url = "https://example.org/inicio"
        self.dominios = {"example.org"}
        self.puertos = {443}

    def comprobar(self, resolver, url=None):

        return verificar_dns_estable(
            url if url is not None else self.url,
            self.dominios,
            self.puertos,
            resolver
        )

    # PRUEBA 1: DNS ESTABLE

    def test_dns_estable(self):

        resolver = Mock(
            side_effect=[
                ["8.8.8.8"],
                ["8.8.8.8"]
            ]
        )

        resultado = self.comprobar(resolver)

        self.assertEqual(
            resultado["ips"],
            ["8.8.8.8"]
        )

        self.assertEqual(resolver.call_count, 2)

    # PRUEBA 2: CAMBIO DE IP PUBLICA

    def test_cambio_ip_publica(self):

        resolver = Mock(
            side_effect=[
                ["8.8.8.8"],
                ["1.1.1.1"]
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "Las respuestas DNS cambiaron"
        ):
            self.comprobar(resolver)

    # PRUEBA 3: CAMBIO A IP PRIVADA

    def test_cambio_ip_privada(self):

        resolver = Mock(
            side_effect=[
                ["8.8.8.8"],
                ["192.168.1.10"]
            ]
        )

        with self.assertRaises(ValueError):
            self.comprobar(resolver)

    # PRUEBA 4: CAMBIO DE ORDEN

    def test_cambio_de_orden(self):

        resolver = Mock(
            side_effect=[
                ["8.8.8.8", "1.1.1.1"],
                ["1.1.1.1", "8.8.8.8"]
            ]
        )

        resultado = self.comprobar(resolver)

        self.assertEqual(len(resultado["ips"]), 2)

    # PRUEBA 5: IPv6 ESTABLE

    def test_ipv6_estable(self):

        resolver = Mock(
            side_effect=[
                ["2001:4860:4860::8888"],
                ["2001:4860:4860::8888"]
            ]
        )

        resultado = self.comprobar(resolver)

        self.assertEqual(
            resultado["ips"],
            ["2001:4860:4860::8888"]
        )

    # PRUEBA 6: PRIMERA RESPUESTA PRIVADA

    def test_primera_respuesta_privada(self):

        resolver = Mock(
            side_effect=[
                ["10.0.0.5"],
                ["8.8.8.8"]
            ]
        )

        with self.assertRaises(ValueError):
            self.comprobar(resolver)

        self.assertEqual(resolver.call_count, 1)

    # PRUEBA 7: SEGUNDA RESPUESTA VACIA

    def test_segunda_respuesta_vacia(self):

        resolver = Mock(
            side_effect=[
                ["8.8.8.8"],
                []
            ]
        )

        with self.assertRaises(ValueError):
            self.comprobar(resolver)

    # PRUEBA 8: DOMINIO NO AUTORIZADO

    def test_dominio_no_autorizado(self):

        resolver = Mock(
            return_value=["8.8.8.8"]
        )

        with self.assertRaises(ValueError):
            self.comprobar(
                resolver,
                "https://otro-dominio.org"
            )

        resolver.assert_not_called()

    # PRUEBA 9: PUERTO NO AUTORIZADO

    def test_puerto_no_autorizado(self):

        resolver = Mock(
            return_value=["8.8.8.8"]
        )

        with self.assertRaises(ValueError):
            self.comprobar(
                resolver,
                "https://example.org:8080"
            )

        resolver.assert_not_called()

    # PRUEBA 10: ERROR DE RESOLUCION DNS

    def test_error_dns(self):

        resolver = Mock(
            side_effect=OSError(
                "Servicio DNS no disponible"
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "No se pudo resolver el dominio"
        ):
            self.comprobar(resolver)


if __name__ == "__main__":
    unittest.main(verbosity=2)
