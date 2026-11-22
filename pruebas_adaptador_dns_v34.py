import unittest
import socket

from adaptador_dns_v34 import extraer_ips_dns


# =====================================
# MOONDETEX - CLASE 34
# PRUEBAS DEL ADAPTADOR DNS
# =====================================

class PruebasAdaptadorDNS(unittest.TestCase):

    def registro_ipv4(self, direccion):
        return (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            (direccion, 443)
        )

    def registro_ipv6(self, direccion):
        return (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            (direccion, 443, 0, 0)
        )

    # PRUEBA 1: IPv4 GLOBAL

    def test_ipv4_global(self):

        registros = [
            self.registro_ipv4("8.8.8.8")
        ]

        resultado = extraer_ips_dns(registros)

        self.assertEqual(resultado, ["8.8.8.8"])

    # PRUEBA 2: IPv6 GLOBAL

    def test_ipv6_global(self):

        registros = [
            self.registro_ipv6("2001:4860:4860::8888")
        ]

        resultado = extraer_ips_dns(registros)

        self.assertEqual(
            resultado,
            ["2001:4860:4860::8888"]
        )

    # PRUEBA 3: ELIMINAR DUPLICADOS

    def test_ips_duplicadas(self):

        registros = [
            self.registro_ipv4("8.8.8.8"),
            self.registro_ipv4("8.8.8.8")
        ]

        resultado = extraer_ips_dns(registros)

        self.assertEqual(resultado, ["8.8.8.8"])

    # PRUEBA 4: IPv4 PRIVADA

    def test_ipv4_privada(self):

        registros = [
            self.registro_ipv4("192.168.1.10")
        ]

        with self.assertRaises(ValueError):
            extraer_ips_dns(registros)

    # PRUEBA 5: IPv6 LOCAL

    def test_ipv6_local(self):

        registros = [
            self.registro_ipv6("::1")
        ]

        with self.assertRaises(ValueError):
            extraer_ips_dns(registros)

    # PRUEBA 6: FAMILIA INCORRECTA

    def test_familia_incorrecta(self):

        registros = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2001:4860:4860::8888", 443)
            )
        ]

        with self.assertRaises(ValueError):
            extraer_ips_dns(registros)

    # PRUEBA 7: REGISTRO INCOMPLETO

    def test_registro_incompleto(self):

        registros = [
            (socket.AF_INET, socket.SOCK_STREAM)
        ]

        with self.assertRaises(ValueError):
            extraer_ips_dns(registros)

    # PRUEBA 8: LISTA VACIA

    def test_lista_vacia(self):

        with self.assertRaises(ValueError):
            extraer_ips_dns([])

    # PRUEBA 9: RESPUESTA MIXTA

    def test_respuesta_mixta(self):

        registros = [
            self.registro_ipv4("8.8.8.8"),
            self.registro_ipv4("10.0.0.5")
        ]

        with self.assertRaises(ValueError):
            extraer_ips_dns(registros)


    # PRUEBA 10: IPv4 CON ESTRUCTURA INCORRECTA

    def test_formato_ipv4_incorrecto(self):

        registros = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("8.8.8.8", 443, 0, 0)
            )
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Formato IPv4 incorrecto"
        ):
            extraer_ips_dns(registros)


    # PRUEBA 11: IPv6 CON ESTRUCTURA INCORRECTA

    def test_formato_ipv6_incorrecto(self):

        registros = [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2001:4860:4860::8888", 443)
            )
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Formato IPv6 incorrecto"
        ):
            extraer_ips_dns(registros)


    # PRUEBA 12: TIPO DE CONEXION INCORRECTO

    def test_tipo_conexion_incorrecto(self):

        registro = (
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 443)
        )

        with self.assertRaisesRegex(
            ValueError,
            "Tipo de conexion no permitido"
        ):
            extraer_ips_dns([registro])


    # PRUEBA 13: PROTOCOLO INCORRECTO

    def test_protocolo_incorrecto(self):

        registro = (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_UDP,
            "",
            ("8.8.8.8", 443)
        )

        with self.assertRaisesRegex(
            ValueError,
            "Protocolo de conexion no permitido"
        ):
            extraer_ips_dns([registro])


    # PRUEBA 14: PUERTO COMO TEXTO

    def test_puerto_texto(self):

        registro = (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", "443")
        )

        with self.assertRaisesRegex(
            ValueError,
            "El puerto debe ser un numero entero"
        ):
            extraer_ips_dns([registro])


    # PRUEBA 15: PUERTO CERO

    def test_puerto_cero(self):

        registro = (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 0)
        )

        with self.assertRaisesRegex(
            ValueError,
            "Puerto fuera del rango permitido"
        ):
            extraer_ips_dns([registro])


    # PRUEBA 16: PUERTO MAYOR AL MAXIMO

    def test_puerto_fuera_rango(self):

        registro = (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 65536)
        )

        with self.assertRaisesRegex(
            ValueError,
            "Puerto fuera del rango permitido"
        ):
            extraer_ips_dns([registro])


if __name__ == "__main__":
    unittest.main(verbosity=2)
