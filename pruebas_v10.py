import unittest
from motor_http import revisar_csp


class PruebasMoonDetexV10(unittest.TestCase):

    # PRUEBA 1
    def test_default_src_comodin(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "Content-Security-Policy: default-src *\n"
        )

        avisos = revisar_csp(respuesta)

        self.assertEqual(len(avisos), 1)


    # PRUEBA 2
    def test_script_src_comodin(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "Content-Security-Policy: "
            "default-src 'self'; script-src *\n"
        )

        avisos = revisar_csp(respuesta)

        self.assertEqual(len(avisos), 1)


    # PRUEBA 3
    def test_sin_comodin(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
            "Content-Security-Policy: "
            "default-src 'self'\n"
        )

        avisos = revisar_csp(respuesta)

        self.assertEqual(len(avisos), 0)


    # PRUEBA 4
    def test_csp_ausente(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/html\n"
        )

        avisos = revisar_csp(respuesta)

        self.assertEqual(len(avisos), 1)


    # PRUEBA 5
    def test_respuesta_json(self):

        respuesta = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: application/json\n"
        )

        avisos = revisar_csp(respuesta)

        self.assertEqual(len(avisos), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
