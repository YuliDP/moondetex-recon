import sqlite3
import tempfile
import shutil
import hashlib

from pathlib import Path
from contextlib import closing


# =====================================
# MOONDETEX - CLASE 27
# PRUEBA SEGURA DE RECUPERACION
# =====================================

CARPETA = Path(__file__).resolve().parent
RESPALDOS = CARPETA / "respaldos"


def calcular_hash(ruta):

    with open(ruta, "rb") as archivo:
        return hashlib.file_digest(
            archivo, "sha256"
        ).hexdigest()


def probar_recuperacion():

    archivos = sorted(
        RESPALDOS.glob("respaldo_*.db")
    )

    if not archivos:
        raise FileNotFoundError(
            "No hay respaldos disponibles."
        )

    # Seleccionar el respaldo mas reciente
    respaldo = archivos[-1]

    print("\nMOONDETEX - CLASE 27")
    print("==============================")
    print("Respaldo:", respaldo.name)

    # Crear una carpeta temporal de laboratorio
    with tempfile.TemporaryDirectory() as temporal:

        recuperada = (
            Path(temporal) / "recuperacion_prueba.db"
        )

        # Copiar el respaldo, sin tocar el original
        shutil.copy2(respaldo, recuperada)

        # Comprobar que la copia sea identica
        if calcular_hash(respaldo) != calcular_hash(recuperada):
            raise RuntimeError(
                "La copia recuperada no coincide."
            )

        print("Copia recuperada: OK")
        print("Comparacion SHA-256: OK")

        # Abrir la copia temporal en modo lectura
        with closing(
            sqlite3.connect(
                recuperada.as_uri() + "?mode=ro",
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

            print("Integridad SQLite: OK")

            print("\nDATOS RECUPERADOS")
            print("==============================")

            for tabla in (
                "proyectos",
                "hallazgos",
                "historial_analisis"
            ):

                cantidad = con.execute(
                    f"SELECT COUNT(*) FROM {tabla}"
                ).fetchone()[0]

                print(f"{tabla}: {cantidad}")

        print("\nRECUPERACION DE PRUEBA: APROBADA")
        print("Base original: SIN MODIFICACIONES")


if __name__ == "__main__":

    try:
        probar_recuperacion()

    except (OSError, sqlite3.Error, RuntimeError) as error:
        print("\nERROR:", error)
