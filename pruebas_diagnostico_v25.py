import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

import verificador_sintaxis_v24


# =====================================
# MOONDETEX - CLASE 25
# PRUEBAS DEL DIAGNOSTICO
# =====================================

class PruebasDiagnostico(unittest.TestCase):

    def setUp(self):

        # Crear carpeta temporal
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.carpeta = Path(self.temporal.name)
        self.archivo = self.carpeta / "prueba.py"

        # Usar archivos temporales
        parche_carpeta = patch.object(
            verificador_sintaxis_v24,
            "CARPETA",
            self.carpeta
        )

        parche_archivos = patch.object(
            verificador_sintaxis_v24,
            "ARCHIVOS",
            ["prueba.py"]
        )

        parche_carpeta.start()
        self.addCleanup(parche_carpeta.stop)

        parche_archivos.start()
        self.addCleanup(parche_archivos.stop)


    # PRUEBA 1: CODIGO CORRECTO

    def test_codigo_correcto(self):

        self.archivo.write_text(
            "resultado = 10 + 5\n",
            encoding="utf-8"
        )

        resultados = (
            verificador_sintaxis_v24.revisar_sintaxis()
        )

        valido, mensaje = resultados["prueba.py"]

        self.assertTrue(valido)


    # PRUEBA 2: ERROR DE SINTAXIS

    def test_error_sintaxis(self):

        self.archivo.write_text(
            "def funcion(:\n    pass\n",
            encoding="utf-8"
        )

        resultados = (
            verificador_sintaxis_v24.revisar_sintaxis()
        )

        valido, mensaje = resultados["prueba.py"]

        self.assertFalse(valido)
        self.assertTrue(mensaje)


    # PRUEBA 3: ARCHIVO INEXISTENTE

    def test_archivo_inexistente(self):

        resultados = (
            verificador_sintaxis_v24.revisar_sintaxis()
        )

        valido, mensaje = resultados["prueba.py"]

        self.assertFalse(valido)
        self.assertTrue(mensaje)


if __name__ == "__main__":
    unittest.main(verbosity=2)
