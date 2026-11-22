import unittest
from unittest.mock import Mock, patch

from puente_politicas_v35 import verificar_proyecto_real


# =====================================
# MOONDETEX - CLASE 35
# PRUEBAS DEL PUENTE DE POLITICAS
# =====================================

class PruebasPuentePoliticas(unittest.TestCase):

    def setUp(self):

        self.proyectos = [
            {"id": 1, "nombre": "Laboratorio Web"},
            {"id": 2, "nombre": "Laboratorio API"}
        ]

        self.politicas = {
            1: {
                "dominios": {"example.org"},
                "puertos": {443},
                "protocolos": {"https"}
            },
            2: {
                "dominios": {"example.net"},
                "puertos": {8443},
                "protocolos": {"https"}
            }
        }

        self.resolver = Mock(
            return_value=["8.8.8.8"]
        )

        # Simular la lectura de proyectos de SQLite
        parche = patch(
            "puente_politicas_v35.cargar_proyectos_reales",
            return_value=self.proyectos
        )

        self.cargar = parche.start()
        self.addCleanup(parche.stop)

    # PRUEBA 1: PROYECTO SIN POLITICA

    def test_proyecto_sin_politica(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_real(
                1,
                "https://example.org",
                {},
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 2: PROYECTO INEXISTENTE

    def test_proyecto_inexistente(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_real(
                99,
                "https://example.org",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 3: PROYECTO AUTORIZADO

    def test_proyecto_autorizado(self):

        resultado = verificar_proyecto_real(
            1,
            "https://example.org",
            self.politicas,
            self.resolver
        )

        self.assertEqual(resultado["puerto"], 443)
        self.assertEqual(resultado["ips"], ["8.8.8.8"])

        self.resolver.assert_called_once_with(
            "example.org"
        )

    # PRUEBA 4: DOMINIO DE OTRO PROYECTO

    def test_dominio_otro_proyecto(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_real(
                1,
                "https://example.net:8443",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 5: PROTOCOLO NO AUTORIZADO

    def test_protocolo_no_autorizado(self):

        with self.assertRaises(ValueError):
            verificar_proyecto_real(
                1,
                "http://example.org:443",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 6: IP PRIVADA

    def test_ip_privada(self):

        self.resolver.return_value = [
            "192.168.1.10"
        ]

        with self.assertRaises(ValueError):
            verificar_proyecto_real(
                1,
                "https://example.org",
                self.politicas,
                self.resolver
            )

    # PRUEBA 7: IDENTIFICADORES DUPLICADOS

    def test_ids_duplicados(self):

        self.cargar.return_value = [
            {"id": 1, "nombre": "Web"},
            {"id": 1, "nombre": "Duplicado"}
        ]

        with self.assertRaises(ValueError):
            verificar_proyecto_real(
                1,
                "https://example.org",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()

    # PRUEBA 8: ERROR AL CARGAR PROYECTOS

    def test_error_carga_proyectos(self):

        self.cargar.side_effect = OSError(
            "Error de lectura"
        )

        with self.assertRaises(OSError):
            verificar_proyecto_real(
                1,
                "https://example.org",
                self.politicas,
                self.resolver
            )

        self.resolver.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
