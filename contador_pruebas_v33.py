import unittest
import importlib

from ejecutar_pruebas_v21 import MODULOS
from verificar_centro_v29 import MINIMO_PRUEBAS


# =====================================
# MOONDETEX - CLASE 33
# CONTADOR AUTOMATICO DE PRUEBAS
# =====================================

def contar_pruebas():

    cargador = unittest.TestLoader()
    total = 0

    if len(MODULOS) != len(set(MODULOS)):
        raise ValueError(
            "Hay modulos de pruebas duplicados."
        )

    for nombre in MODULOS:

        # Cargar cada modulo registrado
        modulo = importlib.import_module(nombre)

        # Descubrir sus pruebas automaticamente
        conjunto = cargador.loadTestsFromModule(modulo)

        cantidad = conjunto.countTestCases()

        print(f"{nombre}: {cantidad} pruebas")

        total += cantidad

    if cargador.errors:
        raise RuntimeError(
            "Error al descubrir pruebas:\n"
            + "\n".join(cargador.errors)
        )

    return total


# =====================================
# EJECUTAR CONTADOR
# =====================================


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 33")
    print("CONTADOR AUTOMATICO")
    print("==============================")

    total = contar_pruebas()

    # Verificar cantidad minima de pruebas
    if total < MINIMO_PRUEBAS:
        raise RuntimeError(
            f"Pruebas insuficientes: {total} "
            f"de al menos {MINIMO_PRUEBAS}"
        )

    print("==============================")
    print(f"TOTAL DE PRUEBAS: {total}")

    print(
        f"CONTROL DE CANTIDAD: OK "
        f"(minimo {MINIMO_PRUEBAS})"
    )
