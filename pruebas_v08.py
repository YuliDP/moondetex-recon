import unittest

from motor_http import evaluar


# MOONDETEX V0.8
# PRUEBAS DE POLITICAS CSP


class PruebasCSP(unittest.TestCase):

    # PRUEBA 1: CSP sin directivas
    def test_csp_sin_directivas(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "Content-Security-Policy: ;;;\n"
        )

        resultado = evaluar(respuesta)

        self.assertFalse(resultado["csp"])


    # PRUEBA 2: CSP con una directiva valida
    def test_csp_con_directiva(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "Content-Security-Policy: "
            "default-src 'self'\n"
        )

        resultado = evaluar(respuesta)

        self.assertTrue(resultado["csp"])


    # PRUEBA 3: CSP ausente
    def test_csp_ausente(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
        )

        resultado = evaluar(respuesta)

        self.assertFalse(resultado["csp"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
