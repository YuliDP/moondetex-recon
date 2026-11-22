import sqlite3
from pathlib import Path

# Base de datos de MOONDETEX
carpeta = Path(__file__).resolve().parent
ruta = carpeta / "moondetex.db"

if not ruta.exists():
    raise SystemExit("No se encontro moondetex.db")

with sqlite3.connect(ruta) as conexion:

    columnas = conexion.execute(
        "PRAGMA table_info(hallazgos)"
    ).fetchall()

    nombres = [columna[1] for columna in columnas]

    if not nombres:
        raise SystemExit(
            "No existe la tabla hallazgos."
        )

    if "estado" not in nombres:

        conexion.execute("""
            ALTER TABLE hallazgos
            ADD COLUMN estado TEXT NOT NULL
            DEFAULT 'Pendiente'
        """)

        print("Estado agregado correctamente.")

    else:
        print("El campo estado ya existe.")

    total = conexion.execute(
        "SELECT COUNT(*) FROM hallazgos"
    ).fetchone()[0]

    print(f"Hallazgos conservados: {total}")
    print("Base de datos actualizada.")
