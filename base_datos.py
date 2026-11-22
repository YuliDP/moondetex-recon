import sqlite3
from pathlib import Path

# =====================================
# MOONDETEX V0.20
# CONEXION A LA BASE DE DATOS
# =====================================

CARPETA = Path(__file__).resolve().parent

DB = CARPETA / "moondetex.db"


def conectar():

    # Comprobar que la base de datos existe
    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontró moondetex.db"
        )

    # Abrir conexion SQLite
    conexion = sqlite3.connect(DB)

    # Activar relaciones entre tablas
    conexion.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conexion
