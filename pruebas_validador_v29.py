from verificar_centro_v29 import MINIMO_PRUEBAS
import unittest

from verificar_centro_v29 import validar_resultado


# =====================================
# MOONDETEX - CLASE 33
# REPORTE DE PRUEBAS DINAMICO
# =====================================

REPORTE_CORRECTO = f"""
Pruebas encontradas: {MINIMO_PRUEBAS}
Ejecutadas: {MINIMO_PRUEBAS}
Aprobadas: {MINIMO_PRUEBAS}
Fallos: 0
Errores: 0
Omitidas: 0
RESULTADO: PRUEBAS APROBADAS
"""


class PruebasValidador(unittest.TestCase):

    # PRUEBA 1: RESULTADO CORRECTO

    def test_resultado_correcto(self):

        correcto, mensaje = validar_resultado(
            REPORTE_CORRECTO, 0
        )

        self.assertTrue(correcto)


    # PRUEBA 2: FALTAN PRUEBAS

    def test_pruebas_incompletas(self):

        reporte = REPORTE_CORRECTO.replace(
            str(MINIMO_PRUEBAS),
            str(MINIMO_PRUEBAS - 1)
        )

        correcto, mensaje = validar_resultado(
            reporte, 0
        )

        self.assertFalse(correcto)
        self.assertIn("insuficientes", mensaje)

    # PRUEBA 3: HAY ERRORES

    def test_resultado_con_errores(self):

        reporte = REPORTE_CORRECTO.replace(
            "Errores: 0", "Errores: 1"
        )

        correcto, mensaje = validar_resultado(
            reporte, 1
        )

        self.assertFalse(correcto)


    # PRUEBA 4: PRUEBAS OMITIDAS

    def test_pruebas_omitidas(self):

        reporte = REPORTE_CORRECTO.replace(
            "Aprobadas: 75", "Aprobadas: 74"
        ).replace(
            "Omitidas: 0", "Omitidas: 1"
        )

        correcto, mensaje = validar_resultado(
            reporte, 0
        )

        self.assertFalse(correcto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
