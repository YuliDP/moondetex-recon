import ast
from pathlib import Path

# =====================================
# MOONDETEX - CLASE 24
# VERIFICADOR DE SINTAXIS
# =====================================

CARPETA = Path(__file__).resolve().parent

ARCHIVOS = [
    "main.py",
    "motor_http.py",
    "base_datos.py",
    "gestor_proyectos.py",
    "gestor_hallazgos.py",
    "lector_reportes_v22.py",
    "ejecutar_pruebas_v21.py",
    "diagnostico_sistema_v24.py"
]


def revisar_sintaxis():

    resultados = {}

    for nombre in ARCHIVOS:

        ruta = CARPETA / nombre

        try:
            codigo = ruta.read_text(
                encoding="utf-8-sig"
            )

            # Analiza el codigo sin ejecutarlo
            ast.parse(codigo, filename=str(ruta))

            resultados[nombre] = (True, "OK")

        except (SyntaxError, OSError, UnicodeError) as error:

            resultados[nombre] = (
                False,
                str(error)
            )

    return resultados


if __name__ == "__main__":

    print("\n================================")
    print("MOONDETEX - VERIFICADOR")
    print("================================\n")

    resultados = revisar_sintaxis()

    correctos = 0

    for nombre, (valido, mensaje) in resultados.items():

        if valido:
            correctos += 1
            print(f"{nombre}: OK")

        else:
            print(f"{nombre}: ERROR")
            print(f"Detalle: {mensaje}")

    print("\n================================")

    print(
        f"Archivos correctos: "
        f"{correctos}/{len(resultados)}"
    )
