# =====================================
# MOONDETEX - CLASE 33
# VERIFICACION AUTOMATICA DE INFORMES
# =====================================

from contador_pruebas_v33 import contar_pruebas
from verificar_centro_v29 import MINIMO_PRUEBAS

from lector_reportes_v22 import (
    obtener_reportes,
    resumir_reporte
)


def verificar_ultimo_informe():

    # Contar las pruebas registradas
    esperadas = contar_pruebas()

    if esperadas < MINIMO_PRUEBAS:
        raise ValueError(
            "La cantidad de pruebas es inferior al minimo."
        )

    # Buscar el informe mas reciente
    informes = obtener_reportes()

    if not informes:
        raise FileNotFoundError(
            "No existen informes guardados."
        )

    nombre = informes[0]
    datos = resumir_reporte(nombre)

    # Convertir los datos a numeros
    try:
        ejecutadas = int(datos["ejecutadas"])
        aprobadas = int(datos["aprobadas"])
        fallos = int(datos["fallos"])
        errores = int(datos["errores"])

    except (ValueError, TypeError):
        raise ValueError(
            "El informe contiene cantidades invalidas."
        ) from None

    # Verificar los resultados
    if (
        ejecutadas != esperadas
        or aprobadas != esperadas
        or fallos != 0
        or errores != 0
        or datos["estado"] != "APROBADO"
    ):
        raise ValueError(
            "El informe no coincide con las pruebas actuales."
        )

    return nombre, esperadas


# =====================================
# EJECUTAR VERIFICACION
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 33")
    print("VERIFICACION DE INFORMES")
    print("==============================")

    try:
        archivo, cantidad = verificar_ultimo_informe()

    except (ValueError, OSError) as error:
        print("VERIFICACION RECHAZADA")
        print("Motivo:", error)
        raise SystemExit(1)

    print("==============================")
    print("INFORME:", archivo)
    print("PRUEBAS VERIFICADAS:", cantidad)
    print("RESULTADO: INFORME VALIDADO")
