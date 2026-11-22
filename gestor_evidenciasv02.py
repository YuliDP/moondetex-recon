import hashlib
import sqlite3
from pathlib import Path

# MOONDETEX V0.16
# GESTOR AUTOMATICO DE EVIDENCIAS

CARPETA = Path(__file__).resolve().parent
BD = CARPETA / "moondetex.db"


def registrar_evidencia(proyecto_id, contenido):

    if not contenido.strip():
        raise ValueError(
            "La evidencia HTTP está vacía."
        )

    # Calcular huella digital
    huella = hashlib.sha256(
        contenido.encode("utf-8")
    ).hexdigest()

    with sqlite3.connect(BD) as con:

        con.execute("PRAGMA foreign_keys = ON")

        # Vincular evidencias con análisis
        con.execute("""
            CREATE TABLE IF NOT EXISTS historial_evidencias (
                analisis_id INTEGER PRIMARY KEY,
                evidencia_id INTEGER NOT NULL,
                FOREIGN KEY (analisis_id)
                    REFERENCES historial_analisis(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (evidencia_id)
                    REFERENCES evidencias_http(id)
                    ON DELETE CASCADE
            )
        """)

        # Guardar evitando copias idénticas
        con.execute("""
            INSERT OR IGNORE INTO evidencias_http
            (proyecto_id, contenido, huella_sha256)
            VALUES (?, ?, ?)
        """, (proyecto_id, contenido, huella))

        evidencia = con.execute("""
            SELECT id FROM evidencias_http
            WHERE proyecto_id = ?
              AND huella_sha256 = ?
        """, (proyecto_id, huella)).fetchone()

        evidencia_id = evidencia[0]

        # Buscar el análisis recién guardado
        analisis = con.execute("""
            SELECT id FROM historial_analisis
            WHERE proyecto_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (proyecto_id,)).fetchone()

        if analisis is None:
            raise ValueError(
                "No se encontró un análisis "
                "para este proyecto."
            )

        analisis_id = analisis[0]

        # Vincular la evidencia al análisis
        con.execute("""
            INSERT INTO historial_evidencias
            (analisis_id, evidencia_id)
            VALUES (?, ?)
            ON CONFLICT(analisis_id)
            DO UPDATE SET
                evidencia_id = excluded.evidencia_id
        """, (analisis_id, evidencia_id))

    return analisis_id, evidencia_id
