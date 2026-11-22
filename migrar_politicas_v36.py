import sqlite3
from contextlib import closing
from datetime import datetime

from base_datos import CARPETA, DB, conectar


# =====================================
# MOONDETEX - CLASE 36
# MIGRACION SEGURA: TABLA DE POLITICAS
# =====================================

def respaldar_base_datos():
    if not DB.is_file():
        raise FileNotFoundError("No se encontro moondetex.db")

    carpeta_respaldos = CARPETA / "respaldos_db"
    carpeta_respaldos.mkdir(exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_respaldo = carpeta_respaldos / f"moondetex_antes_politicas_{marca_tiempo}.db"

    with closing(
        sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)
    ) as origen:
        with closing(sqlite3.connect(ruta_respaldo)) as destino:
            origen.backup(destino)

    return ruta_respaldo


def aplicar_migracion_politicas():
    respaldo = respaldar_base_datos()
    print(f"Respaldo creado en: respaldos_db/{respaldo.name}")

    with closing(conectar()) as conexion:
        # Comprobar que exista la tabla padre 'proyectos'
        tabla_proyectos = conexion.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'proyectos'
            """
        ).fetchone()

        if tabla_proyectos is None:
            raise RuntimeError(
                "No existe la tabla 'proyectos' en moondetex.db."
            )

        # Evitar errores si el script se ejecuta mas de una vez
        tabla_politicas = conexion.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'politicas_proyecto'
            """
        ).fetchone()

        if tabla_politicas is not None:
            print("La tabla 'politicas_proyecto' ya existia. Sin cambios.")
            return

        conexion.execute("""
            CREATE TABLE politicas_proyecto (
                proyecto_id INTEGER PRIMARY KEY,
                dominios TEXT NOT NULL,
                puertos TEXT NOT NULL,
                protocolos TEXT NOT NULL,

                FOREIGN KEY (proyecto_id)
                    REFERENCES proyectos(id)
                    ON DELETE RESTRICT
            )
        """)
        conexion.commit()

        integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        errores_fk = conexion.execute("PRAGMA foreign_key_check").fetchall()

        if integridad != "ok" or errores_fk:
            raise RuntimeError(
                "Alerta de integridad tras la migracion. Restaura el respaldo."
            )

        print("Tabla 'politicas_proyecto' creada correctamente.")
        print(f"Integridad SQLite: {integridad} | Errores FK: {len(errores_fk)}")


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 36")
    print("MIGRACION SEGURA DE POLITICAS")
    print("==============================")

    aplicar_migracion_politicas()