import unittest

from comparador_dns_v35 import comparar_respuestas_dns


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DEL COMPARADOR DNS
# =====================================

class PruebasComparadorDNS(unittest.TestCase):

    # PRUEBA 1: DNS ESTABLE

    def test_dns_estable(self):

        resultado = comparar_respuestas_dns(
            ["8.8.8.8"],
            ["8.8.8.8"]
        )

        self.assertTrue(resultado)


    # PRUEBA 2: CAMBIO DE IP PUBLICA

    def test_cambio_ip_publica(self):

        with self.assertRaisesRegex(
            ValueError,
            "Las respuestas DNS cambiaron"
        ):
            comparar_respuestas_dns(
                ["8.8.8.8"],
                ["1.1.1.1"]
            )


    # PRUEBA 3: CAMBIO A IP PRIVADA

    def test_cambio_ip_privada(self):

        with self.assertRaises(ValueError):
            comparar_respuestas_dns(
                ["8.8.8.8"],
                ["192.168.1.10"]
            )


    # PRUEBA 4: CAMBIO DE ORDEN

    def test_cambio_orden(self):

        resultado = comparar_respuestas_dns(
            ["8.8.8.8", "1.1.1.1"],
            ["1.1.1.1", "8.8.8.8"]
        )

        self.assertTrue(resultado)


    # PRUEBA 5: DIRECCIONES DUPLICADAS

    def test_ips_duplicadas(self):

        resultado = comparar_respuestas_dns(
            ["8.8.8.8", "8.8.8.8"],
            ["8.8.8.8"]
        )

        self.assertTrue(resultado)


    # PRUEBA 6: IPv6 ESTABLE

    def test_ipv6_estable(self):

        resultado = comparar_respuestas_dns(
            ["2001:4860:4860::8888"],
            ["2001:4860:4860::8888"]
        )

        self.assertTrue(resultado)


    # PRUEBA 7: NUEVA IP AGREGADA

    def test_nueva_ip_agregada(self):

        with self.assertRaises(ValueError):
            comparar_respuestas_dns(
                ["8.8.8.8"],
                ["8.8.8.8", "1.1.1.1"]
            )


    # PRUEBA 8: RESPUESTA DNS VACIA

    def test_respuesta_vacia(self):

        with self.assertRaises(ValueError):
            comparar_respuestas_dns(
                ["8.8.8.8"],
                []
            )


# =====================================
# EJECUTAR PRUEBAS
# =====================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
