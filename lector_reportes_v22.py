from pathlib import Path

# =====================================
# MOONDETEX V0.22
# LECTOR DE REPORTES
# =====================================

CARPETA = Path(__file__).resolve().parent

REPORTES = CARPETA / "reportes_pruebas"


def obtener_reportes():

    if not REPORTES.is_dir():
        return []

    archivos = REPORTES.glob("pruebas_*.txt")

    nombres = [
        archivo.name
        for archivo in archivos
        if archivo.is_file()
    ]

    return sorted(nombres, reverse=True)


def leer_reporte(nombre):

    # Validar que sea un informe de MOONDETEX
    if (
        nombre != Path(nombre).name
        or not nombre.startswith("pruebas_")
        or not nombre.endswith(".txt")
    ):
        raise ValueError("Nombre de informe no valido")

    archivo = REPORTES / nombre

    return archivo.read_text(encoding="utf-8")


def resumir_reporte(nombre):

    contenido = leer_reporte(nombre)

    datos = {
        "archivo": nombre,
        "fecha": "No disponible",
        "estado": "SIN IDENTIFICAR",
        "ejecutadas": "0",
        "aprobadas": "0",
        "fallos": "0",
        "errores": "0"
    }

    etiquetas = {
        "Fecha": "fecha",
        "Estado": "estado",
        "Ejecutadas": "ejecutadas",
        "Aprobadas": "aprobadas",
        "Fallos": "fallos",
        "Errores": "errores"
    }

    for linea in contenido.splitlines():

        etiqueta, separador, valor = linea.partition(":")

        etiqueta = etiqueta.strip()

        if separador and etiqueta in etiquetas:
            campo = etiquetas[etiqueta]
            datos[campo] = valor.strip()

    return datos


# =====================================
# COMPROBACION DEL MODULO
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX V0.22")
    print("LECTOR DE REPORTES\n")

    informes = obtener_reportes()

    print("Informes encontrados:", len(informes))

    for nombre in informes:

        contenido = leer_reporte(nombre)

        if "Estado: APROBADO" in contenido:
            estado = "APROBADO"

        elif "Estado: REVISAR ERRORES" in contenido:
            estado = "REVISAR ERRORES"

        else:
            estado = "SIN IDENTIFICAR"

        print(f"\nArchivo: {nombre}")
        print(f"Resultado: {estado}")
