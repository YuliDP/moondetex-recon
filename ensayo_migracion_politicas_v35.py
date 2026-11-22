import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from base_datos import DB


# =====================================
# MOONDETEX - CLASE 35
# ENSAYO DE ALMACENAMIENTO PERMANENTE
# BASE ORIGINAL: SOLO LECTURA
# =====================================

def ensayar_migracion():

    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontro la base de datos."
        )

    with TemporaryDirectory(
        prefix="ensayo_politicas_",
        dir=DB.parent
    ) as temporal:

        copia = Path(temporal) / "moondetex_ensayo.db"

        # Abrir la base original en modo lectura
        with closing(
            sqlite3.connect(
                DB.as_uri() + "?mode=ro",
                uri=True
            )
        ) as original:

            # Crear una copia consistente de SQLite
            with closing(sqlite3.connect(copia)) as ensayo:
                original.backup(ensayo)

                ensayo.execute(
                    "PRAGMA foreign_keys = ON"
                )

                # Crear la tabla SOLO en la copia
                ensayo.execute("""
                    CREATE TABLE politicas_proyecto (
                        proyecto_id INTEGER PRIMARY KEY,
                        dominios TEXT NOT NULL,
                        puertos TEXT NOT NULL,
                        protocolos TEXT NOT NULL,
                        fecha TEXT DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (proyecto_id)
                            REFERENCES proyectos(id)
                    )
                """)

                ensayo.commit()

                # Comprobar los proyectos existentes
                cantidad = ensayo.execute(
                    "SELECT COUNT(*) FROM proyectos"
                ).fetchone()[0]

                # Comprobar que la tabla nueva exista
                tabla = ensayo.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' "
                    "AND name = 'politicas_proyecto'"
                ).fetchone()

                print("Proyectos conservados:", cantidad)
                print(
                    "Tabla de politicas creada:",
                    tabla is not None
                )

                politicas = ensayo.execute(
                    "SELECT COUNT(*) "
                    "FROM politicas_proyecto"
                ).fetchone()[0]

                print("Politicas iniciales:", politicas)

    print("COPIA TEMPORAL ELIMINADA")
    print("BASE ORIGINAL: SIN MODIFICACIONES")


# =====================================
# EJECUTAR LABORATORIO
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("ENSAYO DE MIGRACION SQLITE")
    print("==============================")

    ensayar_migracion()
