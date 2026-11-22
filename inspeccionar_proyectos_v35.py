import sqlite3
from contextlib import closing

from base_datos import DB


# =====================================
# MOONDETEX - CLASE 35
# INSPECCION DE PROYECTOS
# SOLO LECTURA
# =====================================

def inspeccionar_proyectos():

    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontro la base de datos."
        )

    # Abrir SQLite exclusivamente en modo lectura
    with closing(
        sqlite3.connect(
            DB.as_uri() + "?mode=ro",
            uri=True
        )
    ) as conexion:

        conexion.execute("PRAGMA query_only = ON")

        # Identificar las tablas existentes
        filas = conexion.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()

        tablas = [fila[0] for fila in filas]

        print("\nTABLAS ENCONTRADAS:")
        for tabla in tablas:
            print("-", tabla)

        if "proyectos" not in tablas:
            print("\nNo se encontro la tabla 'proyectos'.")
            return

        # Revisar la estructura de proyectos
        columnas = [
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(proyectos)"
            ).fetchall()
        ]

        print("\nCOLUMNAS DE PROYECTOS:")
        for columna in columnas:
            print("-", columna)

        # Mostrar proyectos si existen estas columnas
        if {"id", "nombre"}.issubset(columnas):

            proyectos = conexion.execute(
                "SELECT id, nombre FROM proyectos "
                "ORDER BY id LIMIT 10"
            ).fetchall()

            print("\nPROYECTOS REGISTRADOS:")

            if not proyectos:
                print("No hay proyectos registrados.")

            for identificador, nombre in proyectos:
                print(
                    f"ID: {identificador} | "
                    f"Nombre: {nombre}"
                )

        else:
            print(
                "\nRevisaremos los nombres reales "
                "de las columnas antes de continuar."
            )


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("INSPECCION DE PROYECTOS")
    print("MODO: SOLO LECTURA")
    print("==============================")

    inspeccionar_proyectos()
