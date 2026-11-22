import sqlite3
import json

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing


# =====================================
# MOONDETEX - CLASE 35
# POLITICAS EN SQLITE TEMPORAL
# =====================================

CARPETA = Path(__file__).resolve().parent


def crear_tablas(conexion):

    conexion.execute("""
        CREATE TABLE proyectos (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL
        )
    """)

    conexion.execute("""
        CREATE TABLE politicas (
            proyecto_id INTEGER PRIMARY KEY,
            dominios TEXT NOT NULL,
            puertos TEXT NOT NULL,
            protocolos TEXT NOT NULL,
            FOREIGN KEY (proyecto_id)
                REFERENCES proyectos(id)
        )
    """)

    conexion.commit()


def guardar_politica(conexion, proyecto_id, politica):

    conexion.execute(
        """
        INSERT INTO politicas
        (proyecto_id, dominios, puertos, protocolos)
        VALUES (?, ?, ?, ?)
        """,
        (
            proyecto_id,
            json.dumps(sorted(politica["dominios"])),
            json.dumps(sorted(politica["puertos"])),
            json.dumps(sorted(politica["protocolos"]))
        )
    )

    conexion.commit()


def consultar_politica(conexion, proyecto_id):

    fila = conexion.execute(
        """
        SELECT dominios, puertos, protocolos
        FROM politicas
        WHERE proyecto_id = ?
        """,
        (proyecto_id,)
    ).fetchone()

    if fila is None:
        return None

    return {
        "dominios": set(json.loads(fila[0])),
        "puertos": set(json.loads(fila[1])),
        "protocolos": set(json.loads(fila[2]))
    }


# =====================================
# LABORATORIO LOCAL
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("ALMACENAMIENTO DE POLITICAS")
    print("BASE DE DATOS TEMPORAL")
    print("==============================")

    with TemporaryDirectory(
        prefix="moondetex_politicas_",
        dir=CARPETA
    ) as carpeta_temporal:

        db = Path(carpeta_temporal) / "laboratorio.db"

        with closing(sqlite3.connect(db)) as conexion:

            conexion.execute("PRAGMA foreign_keys = ON")

            crear_tablas(conexion)

            conexion.executemany(
                "INSERT INTO proyectos (id, nombre) VALUES (?, ?)",
                [
                    (1, "Laboratorio Web"),
                    (2, "Laboratorio API")
                ]
            )

            conexion.commit()

            # Solo el proyecto 2 recibe una
            # politica de ejemplo
            guardar_politica(
                conexion,
                2,
                {
                    "dominios": {"example.net"},
                    "puertos": {8443},
                    "protocolos": {"https"}
                }
            )

        # Reabrir la base temporal en solo lectura
        with closing(
            sqlite3.connect(
                db.as_uri() + "?mode=ro",
                uri=True
            )
        ) as conexion:

            for proyecto_id in (1, 2):

                politica = consultar_politica(
                    conexion,
                    proyecto_id
                )

                print(f"\nPROYECTO ID: {proyecto_id}")

                if politica is None:
                    print("POLITICA: PENDIENTE")
                    print("ANALISIS: BLOQUEADO")

                else:
                    print("POLITICA: GUARDADA")
                    print("Dominios:", politica["dominios"])
                    print("Puertos:", politica["puertos"])
                    print("Protocolos:", politica["protocolos"])

    print("\nLABORATORIO FINALIZADO")
    print("Base de datos temporal eliminada.")
