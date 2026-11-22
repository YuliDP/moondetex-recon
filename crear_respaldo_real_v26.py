import sqlite3

from pathlib import Path
from contextlib import closing

from base_datos import DB
from respaldo_sqlite_v26 import crear_respaldo


# =====================================
# MOONDETEX - CLASE 26
# RESPALDO REAL DE LA BASE DE DATOS
# =====================================

CARPETA = Path(__file__).resolve().parent

RESPALDOS = CARPETA / "respaldos"

TABLAS = (
    "proyectos",
    "hallazgos",
    "historial_analisis"
)


def comprobar_base(ruta):

    # Abrir solamente en modo lectura
    with closing(
        sqlite3.connect(
            ruta.as_uri() + "?mode=ro",
            uri=True
        )
    ) as con:

        # Verificar integridad SQLite
        integridad = con.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        # Contar registros importantes
        cantidades = {}

        for tabla in TABLAS:

            cantidad = con.execute(
                f"SELECT COUNT(*) FROM {tabla}"
            ).fetchone()[0]

            cantidades[tabla] = cantidad

    return integridad, cantidades


def ejecutar_respaldo():

    print("\n================================")
    print("MOONDETEX - RESPALDO REAL")
    print("================================\n")

    # Verificar que exista la base original
    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontro moondetex.db"
        )

    # Revisar los datos originales
    integridad_original, datos_originales = (
        comprobar_base(DB)
    )

    if integridad_original != "ok":
        raise RuntimeError(
            "La base original no supero la "
            "verificacion de integridad."
        )

    print("Base original: OK")

    # Crear respaldo permanente
    copia = crear_respaldo(
        DB,
        RESPALDOS
    )

    print("Respaldo creado:", copia.name)

    # Verificar la copia
    integridad_copia, datos_copia = (
        comprobar_base(copia)
    )

    if integridad_copia != "ok":
        raise RuntimeError(
            "El respaldo no supero la "
            "verificacion de integridad."
        )

    if datos_originales != datos_copia:
        raise RuntimeError(
            "Los registros no coinciden. "
            "Revisar el respaldo."
        )

    print("\nREGISTROS VERIFICADOS")
    print("==============================")

    for tabla, cantidad in datos_copia.items():
        print(f"{tabla}: {cantidad}")

    print("\nIntegridad del respaldo: OK")
    print("Comparacion de registros: OK")
    print("Base original: SIN MODIFICACIONES")

    print("\nRESPALDO CREADO CORRECTAMENTE")
    print("Ubicacion:", copia)


if __name__ == "__main__":

    try:
        ejecutar_respaldo()

    except (OSError, sqlite3.Error, RuntimeError) as error:
        print("\nERROR:", error)
        print("No se modifico la base original.")
