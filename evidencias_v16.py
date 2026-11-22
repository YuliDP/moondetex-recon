import hashlib
import sqlite3
from pathlib import Path

# =====================================
# MOONDETEX V0.16
# EVIDENCIAS HTTP DE LABORATORIO
# =====================================

CARPETA = Path(__file__).resolve().parent
BD = CARPETA / "moondetex.db"

# Respuesta HTTP de ejemplo
EJEMPLO_HTTP = (
    "HTTP/1.1 200 OK\n"
    "Content-Type: text/html\n"
    "Content-Security-Policy: default-src *\n"
    "X-Content-Type-Options: nosniff\n"
    "X-Frame-Options: DENY\n"
)


def guardar_evidencia():

    if not BD.is_file():
        print("ERROR: No se encontró moondetex.db.")
        return

    conexion = sqlite3.connect(BD)

    try:
        conexion.execute("PRAGMA foreign_keys = ON")

        # Crear tabla sin modificar las anteriores
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS evidencias_http (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER NOT NULL,
                contenido TEXT NOT NULL,
                huella_sha256 TEXT NOT NULL,
                fecha TEXT NOT NULL DEFAULT
                    (datetime('now', 'localtime')),

                FOREIGN KEY (proyecto_id)
                    REFERENCES proyectos(id)
                    ON DELETE CASCADE,

                UNIQUE (proyecto_id, huella_sha256)
            )
        """)

        # Obtener el primer proyecto
        proyecto = conexion.execute(
            "SELECT id, nombre FROM proyectos "
            "ORDER BY id LIMIT 1"
        ).fetchone()

        if proyecto is None:
            print("Primero crea un proyecto en MOONDETEX.")
            return

        proyecto_id, nombre = proyecto

        # Crear huella digital de la evidencia
        huella = hashlib.sha256(
            EJEMPLO_HTTP.encode("utf-8")
        ).hexdigest()

        # Guardar solo si no existe una copia igual
        cursor = conexion.execute(
            "INSERT OR IGNORE INTO evidencias_http "
            "(proyecto_id, contenido, huella_sha256) "
            "VALUES (?, ?, ?)",
            (proyecto_id, EJEMPLO_HTTP, huella)
        )

        conexion.commit()

        print("\n=== MOONDETEX | EVIDENCIAS V0.16 ===")
        print("Proyecto:", nombre)

        if cursor.rowcount:
            print("Resultado: Evidencia guardada")
        else:
            print(
                "Resultado: Evidencia duplicada; "
                "no se creó otra copia"
            )

        print("Huella SHA-256:", huella)

        cantidad = conexion.execute(
            "SELECT COUNT(*) FROM evidencias_http "
            "WHERE proyecto_id = ?",
            (proyecto_id,)
        ).fetchone()[0]

        print(
            "Evidencias distintas del proyecto:",
            cantidad
        )

    finally:
        conexion.close()


# =====================================
# EJECUTAR
# =====================================

if __name__ == "__main__":
    guardar_evidencia()
