
import unittest
from motor_http import evaluar


class PruebasMoonDetexV09(unittest.TestCase):

    def test_directiva_desconocida(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "Content-Security-Policy: proteccion-lunar\n"
        )

        resultado = evaluar(respuesta)

        # No hay directivas de proteccion reconocidas
        self.assertFalse(resultado["csp"])


    def test_directiva_reconocida(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "Content-Security-Policy: default-src 'self'\n"
        )

        resultado = evaluar(respuesta)

        self.assertTrue(resultado["csp"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
