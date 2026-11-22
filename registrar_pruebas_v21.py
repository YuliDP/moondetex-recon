import subprocess
import sys

from datetime import datetime
from pathlib import Path
from verificar_centro_v29 import validar_resultado

# =====================================
# MOONDETEX V0.21
# REGISTRO AUTOMATICO DE PRUEBAS
# =====================================

CARPETA = Path(__file__).resolve().parent

PROGRAMA = CARPETA / "ejecutar_pruebas_v21.py"

REPORTES = CARPETA / "reportes_pruebas"


def registrar_pruebas():

    if not PROGRAMA.is_file():
        print("ERROR: No se encontro el centro de pruebas.")
        return False

    # Ejecutar el centro de pruebas
    resultado = subprocess.run(
        [sys.executable, str(PROGRAMA)],
        cwd=CARPETA,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    # Obtener fecha y hora
    ahora = datetime.now().astimezone()

    fecha = ahora.strftime("%Y-%m-%d %H:%M:%S")

    nombre = ahora.strftime(
        "pruebas_%Y%m%d_%H%M%S_%f.txt"
    )

    # Crear carpeta de reportes
    REPORTES.mkdir(exist_ok=True)

    archivo = REPORTES / nombre

   
    # Comprobar que se ejecutaron todas
    # las pruebas requeridas
    correcto, detalle = validar_resultado(
        resultado.stdout,
        resultado.returncode
    )

    if correcto:
        estado = "APROBADO"
    else:
        estado = "REVISAR ERRORES"


    # Preparar informe
    informe = (
        "================================\n"
        "MOONDETEX - INFORME DE PRUEBAS\n"
        "================================\n\n"
        f"Fecha: {fecha}\n"
        f"Estado: {estado}\n"
        f"Codigo de salida: {resultado.returncode}\n"
        f"Validacion: {detalle}\n\n"

        "RESULTADOS GENERALES\n"
        "================================\n"
        f"{resultado.stdout}\n\n"
        "DETALLE DE PRUEBAS Y ERRORES\n"
        "================================\n"
        f"{resultado.stderr}\n"
    )

    # Guardar el informe
    archivo.write_text(
        informe,
        encoding="utf-8"
    )

    # Mostrar resumen en terminal
    print("\n================================")
    print("MOONDETEX - REGISTRO DE PRUEBAS")
    print("================================")

    print("Fecha:", fecha)
    print("Resultado:", estado)
    print("Informe guardado en:")
    print(archivo)

    return correcto


if __name__ == "__main__":

    correcto = registrar_pruebas()

    if correcto:
        sys.exit(0)
    else:
        sys.exit(1)
