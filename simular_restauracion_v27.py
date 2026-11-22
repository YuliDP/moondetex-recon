import sqlite3
import tempfile
import shutil
import hashlib

from pathlib import Path
from contextlib import closing


# =====================================
# MOONDETEX - CLASE 27
# SIMULACION DE RESTAURACION SQLITE
# =====================================

CARPETA = Path(__file__).resolve().parent
RESPALDOS = CARPETA / "respaldos"


def calcular_hash(ruta):

    with open(ruta, "rb") as archivo:
        return hashlib.file_digest(
            archivo, "sha256"
        ).hexdigest()


def revisar_base(ruta):

    # Abrir la base sin permitir modificaciones
    with closing(
        sqlite3.connect(
            ruta.resolve().as_uri() + "?mode=ro",
            uri=True
        )
    ) as con:

        integridad = con.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integridad != "ok":
            raise RuntimeError(
                "Error de integridad SQLite."
            )

        # Revisar relaciones entre tablas
        errores_fk = con.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if errores_fk:
            raise RuntimeError(
                f"Relaciones inconsistentes: {len(errores_fk)}"
            )

        # Obtener todas las tablas del usuario
        filas = con.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        tablas = [fila[0] for fila in filas]

        obligatorias = {
            "proyectos",
            "hallazgos",
            "historial_analisis"
        }

        if not obligatorias.issubset(tablas):
            raise RuntimeError(
                "Faltan tablas principales."
            )

        cantidades = {}

        for tabla in tablas:

            nombre_seguro = tabla.replace('"', '""')

            cantidad = con.execute(
                f'SELECT COUNT(*) FROM "{nombre_seguro}"'
            ).fetchone()[0]

            cantidades[tabla] = cantidad

        return cantidades


def simular_restauracion():

    archivos = sorted(
        RESPALDOS.glob("respaldo_*.db")
    )

    if not archivos:
        raise FileNotFoundError(
            "No se encontraron respaldos."
        )

    respaldo = archivos[-1]

    print("\nMOONDETEX - RESTAURACION")
    print("==============================")
    print("Respaldo seleccionado:", respaldo.name)

    # Utilizar una carpeta temporal
    with tempfile.TemporaryDirectory() as temporal:

        restaurada = (
            Path(temporal) / "moondetex_restaurada.db"
        )

        # Copiar el respaldo al laboratorio
        shutil.copy2(respaldo, restaurada)

        if calcular_hash(respaldo) != calcular_hash(restaurada):
            raise RuntimeError(
                "La copia no coincide con el respaldo."
            )

        datos_originales = revisar_base(respaldo)
        datos_restaurados = revisar_base(restaurada)

        if datos_originales != datos_restaurados:
            raise RuntimeError(
                "Las cantidades de registros no coinciden."
            )

        print("\nTABLAS RECUPERADAS")
        print("==============================")

        for tabla, cantidad in datos_restaurados.items():
            print(f"{tabla}: {cantidad}")

        print("\nIntegridad SQLite: OK")
        print("Relaciones verificadas: OK")
        print("Comparacion SHA-256: OK")
        print("Comparacion de registros: OK")

        print("\nSIMULACION APROBADA")
        print("Base real: SIN MODIFICACIONES")


if __name__ == "__main__":

    try:
        simular_restauracion()

    except (OSError, sqlite3.Error, RuntimeError) as error:
        print("\nERROR:", error)
