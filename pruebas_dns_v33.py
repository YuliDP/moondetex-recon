import unittest

from validador_dns_v33 import validar_ips_resueltas


# =====================================
# MOONDETEX - CLASE 33
# PRUEBAS AUTOMATICAS DNS
# =====================================

class PruebasDNS(unittest.TestCase):

    # PRUEBA 1: IPv4 PUBLICA

    def test_ipv4_publica(self):

        resultado = validar_ips_resueltas(
            ["8.8.8.8"]
        )

        self.assertTrue(resultado)


    # PRUEBA 2: IPv6 PUBLICA

    def test_ipv6_publica(self):

        resultado = validar_ips_resueltas(
            ["2001:4860:4860::8888"]
        )

        self.assertTrue(resultado)


    # PRUEBA 3: IPv4 PRIVADA

    def test_ipv4_privada(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                ["192.168.1.10"]
            )


    # PRUEBA 4: IPv4 LOCAL

    def test_ipv4_local(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                ["127.0.0.1"]
            )


    # PRUEBA 5: IPv6 LOCAL

    def test_ipv6_local(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                ["::1"]
            )


    # PRUEBA 6: DNS MIXTO

    def test_dns_mixto(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                ["8.8.8.8", "10.0.0.5"]
            )


    # PRUEBA 7: IP RESERVADA

    def test_ip_reservada(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                ["192.0.2.1"]
            )


    # PRUEBA 8: DIRECCION INVALIDA

    def test_ip_invalida(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                ["999.999.999.999"]
            )


    # PRUEBA 9: LISTA VACIA

    def test_lista_vacia(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                []
            )


    # PRUEBA 10: TIPO DE DATO INCORRECTO

    def test_tipo_incorrecto(self):

        with self.assertRaises(ValueError):

            validar_ips_resueltas(
                "8.8.8.8"
            )


# =====================================
# EJECUTAR PRUEBAS
# =====================================

if __name__ == "__main__":

    unittest.main(verbosity=2)
