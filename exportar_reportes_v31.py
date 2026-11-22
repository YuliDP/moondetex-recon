from pathlib import Path
from datetime import datetime
from html import escape
from uuid import uuid4

from lector_reportes_v22 import (
    obtener_reportes,
    leer_reporte,
    resumir_reporte
)


# =====================================
# MOONDETEX - CLASE 31
# EXPORTACION DE INFORMES HTML
# =====================================

CARPETA = Path(__file__).resolve().parent

EXPORTACIONES = CARPETA / "exportaciones"


def exportar_ultimo_reporte():

    informes = obtener_reportes()

    if not informes:
        raise FileNotFoundError(
            "No existen informes para exportar."
        )

    # Seleccionar el informe mas reciente
    nombre = informes[0]

    datos = resumir_reporte(nombre)
    contenido = leer_reporte(nombre)

    # Proteger el contenido al mostrarlo en HTML
    fecha = escape(datos["fecha"])
    estado = escape(datos["estado"])
    ejecutadas = escape(datos["ejecutadas"])
    aprobadas = escape(datos["aprobadas"])
    fallos = escape(datos["fallos"])
    errores = escape(datos["errores"])
    detalle = escape(contenido)

    # Estilos de MOONDETEX
    estilos = """
    <style>
        body {
            background: #12121A;
            color: #F5F2FF;
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
        }

        h1 {
            color: #FF4FA3;
        }

        h2 {
            color: #C9B6FF;
        }

        .tarjeta {
            background: #28263A;
            padding: 22px;
            border-radius: 12px;
            margin-top: 20px;
        }

        .estado {
            color: #4DDBA8;
            font-weight: bold;
        }

        pre {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-family: Consolas, monospace;
            font-size: 13px;
        }
    </style>
    """

    # Construir el documento HTML
    documento = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>MOONDETEX - Informe</title>
        {estilos}
    </head>

    <body>
        <h1>MOONDETEX</h1>
        <h2>Informe de pruebas automaticas</h2>

        <div class="tarjeta">
            <p>Fecha: {fecha}</p>
            <p class="estado">
                Resultado: {estado}
            </p>

            <p>Pruebas ejecutadas: {ejecutadas}</p>
            <p>Pruebas aprobadas: {aprobadas}</p>
            <p>Fallos: {fallos}</p>
            <p>Errores: {errores}</p>
        </div>

        <div class="tarjeta">
            <h2>Detalle de las pruebas</h2>
            <pre>{detalle}</pre>
        </div>
    </body>
    </html>
    """

    # Crear la carpeta de exportaciones
    EXPORTACIONES.mkdir(
        parents=True,
        exist_ok=True
    )

    # Utilizar un nombre unico
    momento = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    identificador = uuid4().hex[:8]

    destino = EXPORTACIONES / (
        f"informe_{momento}_{identificador}.html"
    )

    destino.write_text(
        documento,
        encoding="utf-8"
    )

    return destino


# =====================================
# PRUEBA DEL EXPORTADOR
# =====================================

if __name__ == "__main__":

    archivo = exportar_ultimo_reporte()

    print("\nMOONDETEX - CLASE 31")
    print("==============================")
    print("Informe HTML generado: OK")
    print("Ubicacion:", archivo)
    print("\nEXPORTACION COMPLETADA")
