import sqlite3
import hashlib

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from base_datos import DB


# =====================================
# MOONDETEX - CLASE 35
# COMPARACION DE DATOS EN MIGRACION
# ORIGINAL: SOLO LECTURA
# =====================================

def obtener_huellas(conexion):

    tablas = conexion.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()

    resultados = {}

    for (nombre,) in tablas:

        nombre_seguro = nombre.replace('"', '""')

        consulta = (
            f'SELECT * FROM "{nombre_seguro}"'
        )

        huellas_filas = []

        for fila in conexion.execute(consulta):

            contenido = repr(tuple(fila)).encode(
                "utf-8"
            )

            huella = hashlib.sha256(
                contenido
            ).digest()

            huellas_filas.append(huella)

        # Evitar diferencias por el orden de las filas
        huellas_filas.sort()

        resumen = hashlib.sha256()

        for huella in huellas_filas:
            resumen.update(huella)

        resultados[nombre] = {
            "cantidad": len(huellas_filas),
            "huella": resumen.hexdigest()
        }

    return resultados


def comparar_migracion():

    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontro moondetex.db."
        )

    with TemporaryDirectory(
        prefix="comparacion_migracion_",
        dir=DB.parent
    ) as temporal:

        copia = Path(temporal) / "ensayo.db"

        # Abrir la base original solo para lectura
        with closing(
            sqlite3.connect(
                DB.as_uri() + "?mode=ro",
                uri=True
            )
        ) as original:

            with closing(
                sqlite3.connect(copia)
            ) as ensayo:

                # Crear copia consistente
                original.backup(ensayo)

                ensayo.execute(
                    "PRAGMA foreign_keys = ON"
                )

                # Huellas antes de la migracion
                antes = obtener_huellas(ensayo)

                if "politicas_proyecto" in antes:
                    raise ValueError(
                        "La tabla de politicas ya existe."
                    )

                # Crear tabla solo en la copia
                ensayo.execute("""
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

                ensayo.commit()

                # Huellas despues de la migracion
                despues = obtener_huellas(ensayo)

                nueva = despues.pop(
                    "politicas_proyecto",
                    None
                )

                datos_conservados = (
                    antes == despues
                )

                tabla_vacia = (
                    nueva is not None
                    and nueva["cantidad"] == 0
                )

                integridad = ensayo.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]

                errores_fk = ensayo.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()

                print("\nRESULTADOS DE COMPARACION")
                print("==============================")

                print(
                    "Tablas originales comparadas:",
                    len(antes)
                )

                print(
                    "Contenido conservado:",
                    datos_conservados
                )

                print(
                    "Tabla nueva vacia:",
                    tabla_vacia
                )

                print(
                    "Integridad SQLite:",
                    integridad
                )

                print(
                    "Errores de claves foraneas:",
                    len(errores_fk)
                )

                if (
                    not datos_conservados
                    or not tabla_vacia
                    or integridad != "ok"
                    or errores_fk
                ):
                    raise RuntimeError(
                        "La comparacion requiere revision."
                    )

                print(
                    "RESULTADO: COMPARACION APROBADA"
                )

    print("COPIA TEMPORAL ELIMINADA")
    print("BASE ORIGINAL: SIN MODIFICACIONES")


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("COMPARACION SEGURA DE DATOS")
    print("==============================")

    comparar_migracion()
