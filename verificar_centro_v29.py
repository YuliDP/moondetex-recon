import re
import subprocess
import sys

from pathlib import Path


# =====================================
# MOONDETEX - CLASE 29
# VALIDACION DEL CENTRO DE PRUEBAS
# =====================================

CARPETA = Path(__file__).resolve().parent

CENTRO = CARPETA / "ejecutar_pruebas_v21.py"

MINIMO_PRUEBAS = 264



def obtener_numero(texto, etiqueta):

    patron = (
        rf"^{re.escape(etiqueta)}:"
        rf"[ \t]*(\d+)[ \t]*$"
    )

    resultado = re.search(
        patron,
        texto,
        re.MULTILINE
    )

    if resultado is None:
        raise ValueError(
            f"No se encontro el dato: {etiqueta}"
        )

    return int(resultado.group(1))


def validar_resultado(texto, codigo_salida):

    try:
        encontradas = obtener_numero(
            texto, "Pruebas encontradas"
        )

        ejecutadas = obtener_numero(
            texto, "Ejecutadas"
        )

        aprobadas = obtener_numero(
            texto, "Aprobadas"
        )

        fallos = obtener_numero(
            texto, "Fallos"
        )

        errores = obtener_numero(
            texto, "Errores"
        )

        omitidas = obtener_numero(
            texto, "Omitidas"
        )

    except ValueError as error:
        return False, str(error)

    if codigo_salida != 0:
        return False, "El centro de pruebas reporto un error."

    if encontradas < MINIMO_PRUEBAS:
        return (
            False,
            f"Pruebas insuficientes: "
            f"{encontradas} de al menos {MINIMO_PRUEBAS}"
        )

    if ejecutadas != encontradas:
        return False, "No se ejecutaron todas las pruebas."

    if aprobadas != ejecutadas:
        return False, "No todas las pruebas fueron aprobadas."

    if fallos != 0 or errores != 0:
        return False, "Se detectaron fallos o errores."

    if omitidas != 0:
        return False, "Hay pruebas omitidas."

    if "RESULTADO: PRUEBAS APROBADAS" not in texto:
        return False, "Falta la confirmacion final."

    return (
        True,
        f"VALIDACION APROBADA: "
        f"{aprobadas} pruebas correctas."
    )


def comprobar_centro():

    if not CENTRO.is_file():
        return False, "No se encontro el centro de pruebas."

    try:
        resultado = subprocess.run(
            [sys.executable, str(CENTRO)],
            cwd=CARPETA,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120
        )

    except subprocess.TimeoutExpired:
        return False, "Se supero el tiempo permitido."

    except OSError as error:
        return False, f"Error al ejecutar: {error}"

    return validar_resultado(
        resultado.stdout,
        resultado.returncode
    )


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 29")
    print("==============================")

    correcto, mensaje = comprobar_centro()

    print(mensaje)

    if correcto:
        sys.exit(0)
    else:
        sys.exit(1)
