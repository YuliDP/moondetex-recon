import sqlite3
from contextlib import closing

from base_datos import DB


# MOONDETEX - CLASE 35
# CONSULTAR ALCANCE - SOLO LECTURA

def consultar_alcance():

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

        proyectos = conexion.execute(
            "SELECT id, nombre, alcance "
            "FROM proyectos ORDER BY id"
        ).fetchall()

        for identificador, nombre, alcance in proyectos:

            print("\nID:", identificador)
            print("Proyecto:", nombre)
            print("Alcance guardado:", repr(alcance))


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("CONSULTA DE ALCANCE")
    print("MODO: SOLO LECTURA")
    print("==============================")

    consultar_alcance()
