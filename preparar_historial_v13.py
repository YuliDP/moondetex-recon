import sqlite3
from pathlib import Path

# =====================================
# MOONDETEX - CLASE 13
# PREPARAR HISTORIAL DE ANALISIS
# =====================================

CARPETA = Path(__file__).resolve().parent

BASE_DATOS = CARPETA / "moondetex.db"

# Comprobar que existe la base de datos
if not BASE_DATOS.is_file():
    raise SystemExit(
        "ERROR: No se encontro moondetex.db"
    )

# Abrir base de datos
with sqlite3.connect(BASE_DATOS) as conexion:

    conexion.execute("PRAGMA foreign_keys = ON")

    # Crear tabla de historial
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS historial_analisis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id INTEGER NOT NULL,
            fecha TEXT NOT NULL DEFAULT
                (datetime('now', 'localtime')),
            total_observaciones INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (proyecto_id)
                REFERENCES proyectos(id)
                ON DELETE CASCADE
        )
    """)

    # Crear tabla de observaciones historicas
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS historial_observaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analisis_id INTEGER NOT NULL,
            clave TEXT NOT NULL,
            titulo TEXT NOT NULL,
            detalle TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente',

            FOREIGN KEY (analisis_id)
                REFERENCES historial_analisis(id)
                ON DELETE CASCADE
        )
    """)

    conexion.commit()

    # Comprobar informacion existente
    total_proyectos = conexion.execute(
        "SELECT COUNT(*) FROM proyectos"
    ).fetchone()[0]

    total_hallazgos = conexion.execute(
        "SELECT COUNT(*) FROM hallazgos"
    ).fetchone()[0]

    # Mostrar resultados
    print("================================")
    print("       MOONDETEX V0.13")
    print("================================")

    print("\nHistorial preparado correctamente.")

    print(
        f"Proyectos conservados: {total_proyectos}"
    )

    print(
        f"Hallazgos conservados: {total_hallazgos}"
    )

    print("\nTablas nuevas:")
    print("- historial_analisis")
    print("- historial_observaciones")

    print("\nBase de datos lista para continuar.")
