import unittest
from unittest.mock import patch

from verificar_informes_v33 import verificar_ultimo_informe
from verificar_centro_v29 import MINIMO_PRUEBAS


# =====================================
# MOONDETEX - CLASE 33
# PRUEBAS DEL VERIFICADOR DE INFORMES
# =====================================

class PruebasVerificarInformes(unittest.TestCase):

    def setUp(self):

        self.datos = {
            "estado": "APROBADO",
            "ejecutadas": str(MINIMO_PRUEBAS),
            "aprobadas": str(MINIMO_PRUEBAS),
            "fallos": "0",
            "errores": "0"
        }

    def ejecutar_simulado(self, informes=None, cantidad=None):

        if informes is None:
            informes = ["pruebas_simuladas.txt"]

        if cantidad is None:
            cantidad = MINIMO_PRUEBAS

        with (
            patch(
                "verificar_informes_v33.contar_pruebas",
                return_value=cantidad
            ),
            patch(
                "verificar_informes_v33.obtener_reportes",
                return_value=informes
            ),
            patch(
                "verificar_informes_v33.resumir_reporte",
                return_value=self.datos
            )
        ):
            return verificar_ultimo_informe()

    # PRUEBA 1: INFORME CORRECTO

    def test_informe_correcto(self):

        nombre, cantidad = self.ejecutar_simulado()

        self.assertEqual(
            nombre, "pruebas_simuladas.txt"
        )

        self.assertEqual(cantidad, MINIMO_PRUEBAS)

    # PRUEBA 2: INFORME DESACTUALIZADO

    def test_informe_desactualizado(self):

        self.datos["ejecutadas"] = str(
            MINIMO_PRUEBAS - 1
        )

        with self.assertRaises(ValueError):
            self.ejecutar_simulado()

    # PRUEBA 3: INFORME CON FALLOS

    def test_informe_con_fallos(self):

        self.datos["fallos"] = "1"

        with self.assertRaises(ValueError):
            self.ejecutar_simulado()

    # PRUEBA 4: SIN INFORMES

    def test_sin_informes(self):

        with patch(
            "verificar_informes_v33.obtener_reportes",
            return_value=[]
        ):
            with patch(
                "verificar_informes_v33.contar_pruebas",
                return_value=MINIMO_PRUEBAS
            ):
                with self.assertRaises(FileNotFoundError):
                    verificar_ultimo_informe()

    # PRUEBA 5: CANTIDAD INSUFICIENTE

    def test_cantidad_insuficiente(self):

        with self.assertRaises(ValueError):
            self.ejecutar_simulado(
                cantidad=MINIMO_PRUEBAS - 1
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
