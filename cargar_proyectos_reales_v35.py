import sqlite3
from contextlib import closing

from base_datos import DB


# =====================================
# MOONDETEX - CLASE 35
# CARGAR PROYECTOS REALES
# MODO SOLO LECTURA
# =====================================

def cargar_proyectos_reales():

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

        filas = conexion.execute(
            "SELECT id, nombre, alcance "
            "FROM proyectos ORDER BY id"
        ).fetchall()

    proyectos = []

    for identificador, nombre, alcance in filas:

        proyectos.append({
            "id": identificador,
            "nombre": nombre,
            "alcance": alcance,
            "politica_configurada": False
        })

    return proyectos


# =====================================
# LABORATORIO LOCAL
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("PROYECTOS REALES")
    print("MODO: SOLO LECTURA")
    print("==============================")

    proyectos = cargar_proyectos_reales()

    for proyecto in proyectos:

        print("\nID:", proyecto["id"])
        print("Nombre:", proyecto["nombre"])
        print("Alcance:", proyecto["alcance"])

        if not proyecto["politica_configurada"]:
            print("Politica: PENDIENTE")
            print("Analisis de red: NO AUTORIZADO")
