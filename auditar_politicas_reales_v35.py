import sqlite3
from contextlib import closing

from base_datos import DB
from lector_politicas_v35 import cargar_politica


# =====================================
# MOONDETEX - CLASE 35
# AUDITORIA DE POLITICAS REALES
# MODO: SOLO LECTURA
# =====================================

def auditar_politicas_reales():

    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontro la base de datos."
        )

    with closing(
        sqlite3.connect(
            DB.as_uri() + "?mode=ro",
            uri=True
        )
    ) as conexion:

        conexion.execute("PRAGMA query_only = ON")

        # Comprobar si existe la tabla de politicas
        tabla = conexion.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'politicas_proyecto'
            """
        ).fetchone()

        # Leer los proyectos existentes
        proyectos = conexion.execute(
            "SELECT id, nombre FROM proyectos ORDER BY id"
        ).fetchall()

        resultados = []

        for proyecto_id, nombre in proyectos:

            if tabla is None:
                estado = "PENDIENTE (sin tabla de politicas)"

            else:
                try:
                    politica = cargar_politica(
                        conexion, proyecto_id
                    )

                    if politica is None:
                        estado = "PENDIENTE"
                    else:
                        estado = "CONFIGURADA"

                except (ValueError, sqlite3.DatabaseError):
                    estado = "INVALIDA"

            resultados.append({
                "id": proyecto_id,
                "nombre": nombre,
                "estado": estado,
                "analisis_red": "BLOQUEADO"
            })

    return resultados


# =====================================
# LABORATORIO DE SOLO LECTURA
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("AUDITORIA DE POLITICAS REALES")
    print("MODO: SOLO LECTURA")
    print("==============================")

    proyectos = auditar_politicas_reales()

    if not proyectos:
        print("No hay proyectos registrados.")

    for proyecto in proyectos:

        print("\nPROYECTO ID:", proyecto["id"])
        print("NOMBRE:", proyecto["nombre"])
        print("POLITICA:", proyecto["estado"])
        print(
            "ANALISIS DE RED:",
            proyecto["analisis_red"]
        )

    print("\nAUDITORIA FINALIZADA")
    print("BASE ORIGINAL: SIN MODIFICACIONES")
