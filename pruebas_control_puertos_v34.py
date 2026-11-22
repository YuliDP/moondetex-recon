import unittest

from control_puertos_v34 import validar_puerto_objetivo


# =====================================
# MOONDETEX - CLASE 34
# PRUEBAS DEL CONTROL DE PUERTOS
# =====================================

class PruebasControlPuertos(unittest.TestCase):

    def setUp(self):
        self.dominios = {"example.org"}
        self.puertos = {443}

    # PRUEBA 1: HTTPS PREDETERMINADO
    def test_https_predeterminado(self):

        resultado = validar_puerto_objetivo(
            "https://example.org",
            self.dominios,
            self.puertos
        )

        self.assertEqual(resultado, 443)

    # PRUEBA 2: PUERTO 443 EXPLICITO
    def test_puerto_443(self):

        resultado = validar_puerto_objetivo(
            "https://example.org:443",
            self.dominios,
            self.puertos
        )

        self.assertEqual(resultado, 443)

    # PRUEBA 3: HTTP NO AUTORIZADO
    def test_http_no_autorizado(self):

        with self.assertRaises(ValueError):
            validar_puerto_objetivo(
                "http://example.org",
                self.dominios,
                self.puertos
            )

    # PRUEBA 4: PUERTO 8080
    def test_puerto_8080(self):

        with self.assertRaises(ValueError):
            validar_puerto_objetivo(
                "https://example.org:8080",
                self.dominios,
                self.puertos
            )

    # PRUEBA 5: DOMINIO EXTERNO
    def test_dominio_externo(self):

        with self.assertRaises(ValueError):
            validar_puerto_objetivo(
                "https://otro-dominio.org",
                self.dominios,
                self.puertos
            )

    # PRUEBA 6: LISTA VACIA
    def test_lista_puertos_vacia(self):

        with self.assertRaises(ValueError):
            validar_puerto_objetivo(
                "https://example.org",
                self.dominios,
                set()
            )

    # PRUEBA 7: PUERTO INCORRECTO EN LISTA
    def test_puerto_invalido_en_lista(self):

        with self.assertRaises(ValueError):
            validar_puerto_objetivo(
                "https://example.org",
                self.dominios,
                {"443"}
            )

    # PRUEBA 8: PUERTO FUERA DE RANGO
    def test_puerto_fuera_rango(self):

        with self.assertRaises(ValueError):
            validar_puerto_objetivo(
                "https://example.org:65536",
                self.dominios,
                self.puertos
            )

    # PRUEBA 9: HTTP AUTORIZADO
    def test_http_autorizado(self):

        resultado = validar_puerto_objetivo(
            "http://example.org",
            self.dominios,
            {80}
        )

        self.assertEqual(resultado, 80)

    # PRUEBA 10: PUERTO PERSONALIZADO
    def test_puerto_personalizado(self):

        resultado = validar_puerto_objetivo(
            "https://example.org:8443",
            self.dominios,
            {8443}
        )

        self.assertEqual(resultado, 8443)


if __name__ == "__main__":
    unittest.main(verbosity=2)
