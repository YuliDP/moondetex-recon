import unittest

from motor_http import evaluar, comparar

# MOONDETEX - PRUEBAS V0.7

# Ejemplo de configuracion sin controles
ANTES = (
    "HTTP/1.1 200 OK\n"
    "Content-Type: text/html\n"
)

# Ejemplo con controles de seguridad
DESPUES = (
    "HTTP/1.1 200 OK\n"
    "Content-Type: text/html\n"
    "Content-Security-Policy: "
    "default-src 'self'; frame-ancestors 'none'\n"
    "X-Content-Type-Options: nosniff\n"
)


class PruebasMoonDetex(unittest.TestCase):

    # PRUEBA 1
    def test_sin_controles(self):
        resultado = evaluar(ANTES)

        self.assertEqual(resultado, {
            "csp": False,
            "marcos": False,
            "nosniff": False
        })

    # PRUEBA 2
    def test_con_controles(self):
        resultado = evaluar(DESPUES)

        self.assertEqual(resultado, {
            "csp": True,
            "marcos": True,
            "nosniff": True
        })

    # PRUEBA 3
    def test_comparacion(self):
        resultado = comparar(ANTES, DESPUES)

        estados = [
            item["estado"]
            for item in resultado
        ]

        self.assertEqual(
            estados,
            ["Mejora observada"] * 3
        )

    # PRUEBA 4
    def test_texto_incorrecto(self):
        with self.assertRaises(ValueError):
            evaluar("Esto no es HTTP")


# EJECUTAR LAS PRUEBAS
if __name__ == "__main__":
    unittest.main(verbosity=2)
