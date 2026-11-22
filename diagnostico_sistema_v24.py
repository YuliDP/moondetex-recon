from pathlib import Path
import sys

# =====================================
# MOONDETEX - CLASE 24
# DIAGNOSTICO DEL SISTEMA
# =====================================

CARPETA = Path(__file__).resolve().parent

ARCHIVOS = {
    "Aplicacion principal": "main.py",
    "Motor HTTP": "motor_http.py",
    "Base de datos": "moondetex.db",
    "Gestor de proyectos": "gestor_proyectos.py",
    "Gestor de hallazgos": "gestor_hallazgos.py",
    "Lector de reportes": "lector_reportes_v22.py",
    "Centro de pruebas": "ejecutar_pruebas_v21.py"
}


def revisar_sistema():

    resultados = {}

    for descripcion, nombre in ARCHIVOS.items():

        ruta = CARPETA / nombre

        resultados[descripcion] = ruta.is_file()

    return resultados


def contar_reportes():

    carpeta = CARPETA / "reportes_pruebas"

    if not carpeta.is_dir():
        return 0

    informes = carpeta.glob("pruebas_*.txt")

    return sum(
        1 for archivo in informes
        if archivo.is_file()
    )


# =====================================
# MOSTRAR DIAGNOSTICO
# =====================================

if __name__ == "__main__":

    print("\n================================")
    print("MOONDETEX - DIAGNOSTICO")
    print("================================\n")

    print("Python:", sys.version.split()[0])
    print()

    resultados = revisar_sistema()

    for descripcion, encontrado in resultados.items():

        if encontrado:
            estado = "OK"
        else:
            estado = "NO ENCONTRADO"

        print(f"{descripcion}: {estado}")

    print()
    print("Informes guardados:", contar_reportes())

    if all(resultados.values()):
        print("\nArchivos principales encontrados.")
    else:
        print("\nHay archivos que debemos revisar.")
