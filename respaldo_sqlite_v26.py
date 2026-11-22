import sqlite3
import tempfile

from pathlib import Path
from datetime import datetime
from contextlib import closing
from uuid import uuid4


# =====================================
# MOONDETEX - CLASE 26
# SISTEMA DE RESPALDOS SQLITE
# =====================================


def crear_respaldo(origen, carpeta_respaldos):

    origen = Path(origen).resolve()

    carpeta_respaldos = Path(
        carpeta_respaldos
    ).resolve()

    # Comprobar que la base original existe
    if not origen.is_file():
        raise FileNotFoundError(
            "No se encontro la base de datos original."
        )

    carpeta_respaldos.mkdir(
        parents=True,
        exist_ok=True
    )

    # Crear nombre unico para cada respaldo
    fecha = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    identificador = uuid4().hex[:8]

    nombre = (
        f"respaldo_{fecha}_{identificador}.db"
    )

    destino = carpeta_respaldos / nombre

    try:

        # Abrir la base original en modo lectura
        with closing(
            sqlite3.connect(
                origen.as_uri() + "?mode=ro",
                uri=True
            )
        ) as fuente:

            # Crear una copia con el sistema SQLite
            with closing(
                sqlite3.connect(destino)
            ) as copia:

                fuente.backup(copia)

                # Comprobar la integridad de la copia
                resultado = copia.execute(
                    "PRAGMA quick_check"
                ).fetchone()[0]

                if resultado != "ok":
                    raise sqlite3.DatabaseError(
                        "La copia no supero la verificacion."
                    )

        return destino

    except Exception:

        # Eliminar solamente la copia incompleta
        destino.unlink(missing_ok=True)

        raise


# =====================================
# LABORATORIO CON DATOS TEMPORALES
# =====================================

if __name__ == "__main__":

    with tempfile.TemporaryDirectory() as temporal:

        carpeta = Path(temporal)

        original = carpeta / "laboratorio.db"

        # Crear una base de datos ficticia
        with closing(sqlite3.connect(original)) as con:

            con.execute("""
                CREATE TABLE pruebas (
                    id INTEGER PRIMARY KEY,
                    mensaje TEXT NOT NULL
                )
            """)

            con.execute(
                "INSERT INTO pruebas (mensaje) VALUES (?)",
                ("MOONDETEX protegido",)
            )

            con.commit()

        # Generar el respaldo temporal
        copia = crear_respaldo(
            original,
            carpeta / "respaldos"
        )

        # Leer los datos de la copia
        with closing(sqlite3.connect(copia)) as con:

            mensaje = con.execute(
                "SELECT mensaje FROM pruebas"
            ).fetchone()[0]

        if mensaje != "MOONDETEX protegido":
            raise AssertionError(
                "Los datos del respaldo no coinciden."
            )

        print("\nMOONDETEX - CLASE 26")
        print("==============================")
        print("Base de laboratorio creada: OK")
        print("Copia de seguridad creada: OK")
        print("Integridad SQLite: OK")
        print("Datos recuperados: OK")
        print("\nPRUEBA APROBADA")
        print("Base de datos real: SIN MODIFICACIONES")
