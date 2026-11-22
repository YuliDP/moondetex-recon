import hashlib
import sqlite3
from pathlib import Path

# =====================================
# MOONDETEX V0.17
# VINCULACION EXACTA DE EVIDENCIAS
# =====================================

CARPETA = Path(__file__).resolve().parent
BD = CARPETA / "moondetex.db"


def registrar_evidencia(proyecto_id, contenido, analisis_id):

    if not contenido.strip():
        raise ValueError(
            "La evidencia HTTP esta vacia."
        )

    # Generar huella SHA-256
    huella = hashlib.sha256(
        contenido.encode("utf-8")
    ).hexdigest()

    with sqlite3.connect(BD) as con:

        con.execute("PRAGMA foreign_keys = ON")

        # Comprobar que el analisis pertenece
        # al proyecto seleccionado
        analisis = con.execute("""
            SELECT id
            FROM historial_analisis
            WHERE id = ? AND proyecto_id = ?
        """, (analisis_id, proyecto_id)).fetchone()

        if analisis is None:
            raise ValueError(
                "El analisis no pertenece al proyecto."
            )

        # Tabla para guardar evidencias
        con.execute("""
            CREATE TABLE IF NOT EXISTS evidencias_http (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER NOT NULL,
                contenido TEXT NOT NULL,
                huella_sha256 TEXT NOT NULL,
                fecha TEXT NOT NULL DEFAULT
                    (datetime('now', 'localtime')),
                FOREIGN KEY(proyecto_id)
                    REFERENCES proyectos(id)
                    ON DELETE CASCADE,
                UNIQUE(proyecto_id, huella_sha256)
            )
        """)

        # Tabla de vinculaciones
        con.execute("""
            CREATE TABLE IF NOT EXISTS historial_evidencias (
                analisis_id INTEGER PRIMARY KEY,
                evidencia_id INTEGER NOT NULL,
                FOREIGN KEY(analisis_id)
                    REFERENCES historial_analisis(id)
                    ON DELETE CASCADE,
                FOREIGN KEY(evidencia_id)
                    REFERENCES evidencias_http(id)
                    ON DELETE CASCADE
            )
        """)

        # Guardar evidencia sin duplicados
        con.execute("""
            INSERT OR IGNORE INTO evidencias_http
            (proyecto_id, contenido, huella_sha256)
            VALUES (?, ?, ?)
        """, (proyecto_id, contenido, huella))

        evidencia = con.execute("""
            SELECT id
            FROM evidencias_http
            WHERE proyecto_id = ?
              AND huella_sha256 = ?
        """, (proyecto_id, huella)).fetchone()

        evidencia_id = evidencia[0]

        # Vincular al ID exacto del analisis
        con.execute("""
            INSERT INTO historial_evidencias
            (analisis_id, evidencia_id)
            VALUES (?, ?)
            ON CONFLICT(analisis_id)
            DO UPDATE SET
                evidencia_id = excluded.evidencia_id
        """, (analisis_id, evidencia_id))

    return analisis_id, evidencia_id
