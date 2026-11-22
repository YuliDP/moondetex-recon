import sqlite3
from pathlib import Path

# =====================================
# MOONDETEX - CLASE 14
# COMPARADOR DE HISTORIAL
# =====================================

CARPETA = Path(__file__).resolve().parent
BASE_DATOS = CARPETA / "moondetex.db"

if not BASE_DATOS.is_file():
    raise SystemExit(
        "No encuentro moondetex.db en esta carpeta."
    )


# OBTENER OBSERVACIONES DE UN ANALISIS
def cargar_observaciones(conexion, analisis_id):

    filas = conexion.execute("""
        SELECT clave, titulo, detalle
        FROM historial_observaciones
        WHERE analisis_id = ?
    """, (analisis_id,)).fetchall()

    return {
        clave: (titulo, detalle)
        for clave, titulo, detalle in filas
    }


# =====================================
# COMPARAR LOS DOS ULTIMOS ANALISIS
# =====================================

with sqlite3.connect(BASE_DATOS) as conexion:

    proyectos = conexion.execute(
        "SELECT id, nombre FROM proyectos ORDER BY id"
    ).fetchall()

    print("\n===== MOONDETEX V0.14 =====")
    print("COMPARADOR DE HISTORIAL")

    if not proyectos:
        print("Todavia no hay proyectos guardados.")

    for proyecto_id, nombre in proyectos:

        print(f"\nProyecto: {nombre} (ID {proyecto_id})")

        analisis = conexion.execute("""
            SELECT id, fecha
            FROM historial_analisis
            WHERE proyecto_id = ?
            ORDER BY id DESC
            LIMIT 2
        """, (proyecto_id,)).fetchall()

        if len(analisis) < 2:
            print(
                "Necesitas al menos 2 analisis "
                "para comparar."
            )
            continue

        # IDENTIFICAR AMBOS ANALISIS
        (id_actual, fecha_actual), (
            id_anterior, fecha_anterior
        ) = analisis

        anterior = cargar_observaciones(
            conexion, id_anterior
        )

        actual = cargar_observaciones(
            conexion, id_actual
        )

        # COMPARAR IDENTIFICADORES
        claves_anteriores = set(anterior)
        claves_actuales = set(actual)

        nuevas = (
            claves_actuales - claves_anteriores
        )

        ausentes = (
            claves_anteriores - claves_actuales
        )

        comunes = (
            claves_actuales & claves_anteriores
        )

        cambiadas = {
            clave
            for clave in comunes
            if anterior[clave] != actual[clave]
        }

        iguales = comunes - cambiadas

        # MOSTRAR RESULTADOS
        print(
            f"Anterior: #{id_anterior} "
            f"({fecha_anterior})"
        )

        print(
            f"Reciente: #{id_actual} "
            f"({fecha_actual})"
        )

        print(
            f"Nuevas observaciones: {len(nuevas)}"
        )

        print(
            f"Persistentes sin cambios: {len(iguales)}"
        )

        print(
            f"Persistentes con cambios: {len(cambiadas)}"
        )

        print(
            f"Ya no observadas: {len(ausentes)}"
        )

        # MOSTRAR DETALLES DE LOS CAMBIOS
        for etiqueta, claves, datos in (
            ("NUEVA", nuevas, actual),
            ("CAMBIO", cambiadas, actual),
            ("YA NO OBSERVADA", ausentes, anterior)
        ):

            for clave in sorted(claves):

                titulo, detalle = datos[clave]

                print(
                    f"  [{etiqueta}] "
                    f"{titulo}: {detalle}"
                )

print(
    "\nNota: que una observacion deje "
    "de aparecer no confirma que "
    "el problema haya sido corregido."
)
