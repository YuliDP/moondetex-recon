import unittest

from filtros_hallazgos_v30 import filtrar_hallazgos


# =====================================
# MOONDETEX - CLASE 30
# PRUEBAS AUTOMATICAS DE FILTROS
# =====================================

class PruebasFiltros(unittest.TestCase):

    def setUp(self):

        # Hallazgos ficticios de laboratorio
        self.hallazgos = [
            (1, "Laboratorio", "MIME", "", "2026-10-26", "Pendiente"),
            (2, "Laboratorio", "CSP", "", "2026-10-26", "Revisado"),
            (3, "Laboratorio", "Marcos", "", "2026-10-26", "Pendiente"),
            (4, "Laboratorio", "DNS", "", "2026-10-26", "Descartado")
        ]

    # PRUEBA 1: MOSTRAR TODOS

    def test_mostrar_todos(self):

        resultado = filtrar_hallazgos(
            self.hallazgos, "Todos"
        )

        self.assertEqual(len(resultado), 4)

    # PRUEBA 2: FILTRAR PENDIENTES

    def test_filtrar_pendientes(self):

        resultado = filtrar_hallazgos(
            self.hallazgos, "Pendiente"
        )

        self.assertEqual(len(resultado), 2)

        self.assertTrue(
            all(fila[5] == "Pendiente" for fila in resultado)
        )

    # PRUEBA 3: FILTRAR REVISADOS

    def test_filtrar_revisados(self):

        resultado = filtrar_hallazgos(
            self.hallazgos, "Revisado"
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0][5], "Revisado")

    # PRUEBA 4: FILTRAR DESCARTADOS

    def test_filtrar_descartados(self):

        resultado = filtrar_hallazgos(
            self.hallazgos, "Descartado"
        )

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0][5], "Descartado")

    # PRUEBA 5: RECHAZAR ESTADO INVALIDO

    def test_estado_invalido(self):

        with self.assertRaises(ValueError):

            filtrar_hallazgos(
                self.hallazgos, "Desconocido"
            )

    # PRUEBA 6: NO MODIFICAR HALLAZGOS

    def test_no_modificar_datos(self):

        datos_originales = list(self.hallazgos)

        filtrar_hallazgos(
            self.hallazgos, "Pendiente"
        )

        self.assertEqual(
            self.hallazgos,
            datos_originales
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
