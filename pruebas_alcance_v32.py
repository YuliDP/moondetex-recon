import unittest

from validador_alcance_v32 import validar_objetivo


# =====================================
# MOONDETEX - CLASE 32
# PRUEBAS AUTOMATICAS DE ALCANCE
# =====================================

class PruebasAlcance(unittest.TestCase):

    def setUp(self):

        # Dominio ficticio permitido
        self.permitidos = {"example.org"}


    # PRUEBA 1: DOMINIO PERMITIDO

    def test_dominio_permitido(self):

        resultado = validar_objetivo(
            "https://example.org/prueba",
            self.permitidos
        )

        self.assertTrue(resultado)


    # PRUEBA 2: DOMINIO PARECIDO

    def test_dominio_parecido(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "https://example.org.falso.net",
                self.permitidos
            )


    # PRUEBA 3: PROTOCOLO NO PERMITIDO

    def test_protocolo_invalido(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "ftp://example.org/archivo",
                self.permitidos
            )


    # PRUEBA 4: OTRO DOMINIO

    def test_dominio_no_autorizado(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "https://otro-dominio.org",
                self.permitidos
            )


    # PRUEBA 5: SUBDOMINIO NO INCLUIDO

    def test_subdominio_no_autorizado(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "https://admin.example.org",
                self.permitidos
            )


    # PRUEBA 6: CREDENCIALES EN LA URL

    def test_credenciales_en_url(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "https://usuario:clave@example.org",
                self.permitidos
            )


    # PRUEBA 7: PUERTO INVALIDO

    def test_puerto_invalido(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "https://example.org:99999",
                self.permitidos
            )


    # PRUEBA 8: URL VACIA

    def test_url_vacia(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "",
                self.permitidos
            )


# =====================================
# EJECUTAR PRUEBAS
# =====================================

    # PRUEBA 9: CARACTERES OCULTOS

    def test_caracteres_de_control(self):

        with self.assertRaises(ValueError):

            validar_objetivo(
                "https://exam\nple.org",
                self.permitidos
            )
      # PRUEBA 10: BLOQUEAR IPv4 DIRECTA
    def test_ipv4_directa(self):

        with self.assertRaises(ValueError):
            validar_objetivo(
                "http://127.0.0.1",
                {"127.0.0.1"}
            )

    # PRUEBA 11: BLOQUEAR IPv6 DIRECTA
    def test_ipv6_directa(self):

        with self.assertRaises(ValueError):
            validar_objetivo(
                "http://[::1]",
                {"::1"}
            )
       

if __name__ == "__main__":

    unittest.main(verbosity=2)
