import hashlib
import sqlite3
from pathlib import Path

# MOONDETEX V0.18
# GUARDADO ATOMICO DE ANALISIS Y EVIDENCIAS

DB = Path(__file__).resolve().parent / "moondetex.db"


def guardar_analisis_completo(proyecto_id, filas, contenido):

    if not contenido.strip():
        raise ValueError("La respuesta HTTP está vacía.")

    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontró moondetex.db."
        )

    huella = hashlib.sha256(
        contenido.encode("utf-8")
    ).hexdigest()

    con = sqlite3.connect(DB)

    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("BEGIN IMMEDIATE")

        # Recuperar estados anteriores
        anterior = con.execute(
            "SELECT clave, detalle, estado FROM hallazgos "
            "WHERE proyecto_id = ?",
            (proyecto_id,)
        ).fetchall()

        estados = {
            (clave, detalle): estado
            for clave, detalle, estado in anterior
        }

        # Crear registro historico
        cursor = con.execute(
            "INSERT INTO historial_analisis "
            "(proyecto_id, total_observaciones) "
            "VALUES (?, ?)",
            (proyecto_id, len(filas))
        )

        analisis_id = cursor.lastrowid

        registros = [
            (
                clave,
                titulo,
                detalle,
                estados.get((clave, detalle), "Pendiente")
            )
            for clave, titulo, detalle in filas
        ]

        # Guardar observaciones historicas
        con.executemany(
            "INSERT INTO historial_observaciones "
            "(analisis_id, clave, titulo, detalle, estado) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (analisis_id, *r)
                for r in registros
            ]
        )

        # Actualizar hallazgos actuales
        con.execute(
            "DELETE FROM hallazgos WHERE proyecto_id = ?",
            (proyecto_id,)
        )

        con.executemany(
            "INSERT INTO hallazgos "
            "(proyecto_id, clave, titulo, detalle, estado) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (proyecto_id, *r)
                for r in registros
            ]
        )

        # Guardar evidencia sin duplicarla
        con.execute(
            "INSERT OR IGNORE INTO evidencias_http "
            "(proyecto_id, contenido, huella_sha256) "
            "VALUES (?, ?, ?)",
            (proyecto_id, contenido, huella)
        )

        evidencia = con.execute(
            "SELECT id FROM evidencias_http "
            "WHERE proyecto_id = ? AND huella_sha256 = ?",
            (proyecto_id, huella)
        ).fetchone()

        if evidencia is None:
            raise RuntimeError(
                "No se pudo encontrar la evidencia guardada."
            )

        # Vincular al identificador exacto
        con.execute(
            "INSERT INTO historial_evidencias "
            "(analisis_id, evidencia_id) VALUES (?, ?)",
            (analisis_id, evidencia[0])
        )

        # Confirmar todo junto
        con.commit()

        return analisis_id

    except Exception:
        # Si algo falla, cancelar toda la operacion
        con.rollback()
        raise

    finally:
        con.close()
