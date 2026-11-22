import unittest

from control_redirecciones_v32 import validar_redireccion


# =====================================
# MOONDETEX - CLASE 32
# PRUEBAS AUTOMATICAS DE REDIRECCIONES
# =====================================

class PruebasRedirecciones(unittest.TestCase):

    def setUp(self):

        self.origen = "https://example.org/inicio"
        self.permitidos = {"example.org"}

    # PRUEBA 1: RUTA RELATIVA PERMITIDA

    def test_ruta_relativa(self):

        resultado = validar_redireccion(
            self.origen,
            "/documentacion",
            self.permitidos
        )

        self.assertEqual(
            resultado,
            "https://example.org/documentacion"
        )

    # PRUEBA 2: URL ABSOLUTA PERMITIDA

    def test_url_absoluta(self):

        resultado = validar_redireccion(
            self.origen,
            "https://example.org/ayuda",
            self.permitidos
        )

        self.assertEqual(
            resultado,
            "https://example.org/ayuda"
        )

    # PRUEBA 3: DOMINIO EXTERNO

    def test_dominio_externo(self):

        with self.assertRaises(ValueError):

            validar_redireccion(
                self.origen,
                "https://otro-dominio.org",
                self.permitidos
            )

    # PRUEBA 4: SUBDOMINIO NO AUTORIZADO

    def test_subdominio_no_autorizado(self):

        with self.assertRaises(ValueError):

            validar_redireccion(
                self.origen,
                "//admin.example.org/panel",
                self.permitidos
            )

    # PRUEBA 5: DESTINO VACIO

    def test_destino_vacio(self):

        with self.assertRaises(ValueError):

            validar_redireccion(
                self.origen,
                "",
                self.permitidos
            )

    # PRUEBA 6: CARACTERES OCULTOS

    def test_caracteres_ocultos(self):

        with self.assertRaises(ValueError):

            validar_redireccion(
                self.origen,
                "/pagina\noculta",
                self.permitidos
            )

    # PRUEBA 7: CREDENCIALES EN URL

    def test_credenciales(self):

        with self.assertRaises(ValueError):

            validar_redireccion(
                self.origen,
                "https://usuario:clave@example.org",
                self.permitidos
            )

    # PRUEBA 8: PUERTO INVALIDO

    def test_puerto_invalido(self):

        with self.assertRaises(ValueError):

            validar_redireccion(
                self.origen,
                "https://example.org:99999",
                self.permitidos
            )

    # PRUEBA 9: PROTOCOLO NO PERMITIDO

    def test_protocolo_invalido(self):

        with self.assertRaises(ValueError):

            validar_redireccion(
                self.origen,
                "ftp://example.org/archivo",
                self.permitidos
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
