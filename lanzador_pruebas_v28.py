import subprocess
import sys

from pathlib import Path


# =====================================
# MOONDETEX - CLASE 28
# LANZADOR DE PRUEBAS AUTOMATICAS
# =====================================

CARPETA = Path(__file__).resolve().parent

PROGRAMA = CARPETA / "registrar_pruebas_v21.py"


def ejecutar_y_registrar_pruebas():

    # Comprobar que existe el programa
    if not PROGRAMA.is_file():

        return (
            False,
            "No se encontro registrar_pruebas_v21.py"
        )

    try:

        # Ejecutar las pruebas en otro proceso
        resultado = subprocess.run(
            [sys.executable, str(PROGRAMA)],
            cwd=CARPETA,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120
        )

        mensaje = resultado.stdout.strip()

        if resultado.stderr:
            mensaje += "\n" + resultado.stderr.strip()

        if resultado.returncode == 0:

            return True, mensaje

        return False, mensaje or "Las pruebas fallaron."

    except subprocess.TimeoutExpired:

        return (
            False,
            "Se supero el tiempo maximo de ejecucion."
        )

    except OSError as error:

        return (
            False,
            f"No se pudieron ejecutar las pruebas: {error}"
        )


# =====================================
# COMPROBACION DEL LANZADOR
# =====================================

if __name__ == "__main__":

    correcto, mensaje = ejecutar_y_registrar_pruebas()

    print("\nMOONDETEX - CLASE 28")
    print("==============================")

    print(mensaje)

    if correcto:
        print("\nEJECUCION COMPLETADA")
    else:
        print("\nREVISAR EJECUCION")

    sys.exit(0 if correcto else 1)
