import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from laboratorio_politicas_sqlite_v35 import (
    crear_tablas,
    consultar_politica
)
from guardado_seguro_politicas_v35 import (
    guardar_politica_validada
)


# =====================================
# MOONDETEX - CLASE 35
# INTEGRIDAD REFERENCIAL DE POLITICAS
# BASE DE DATOS TEMPORAL
# =====================================

def ejecutar_laboratorio():

    with TemporaryDirectory() as temporal:

        db = Path(temporal) / "laboratorio.db"

        with closing(sqlite3.connect(db)) as conexion:

            # Activar proteccion de claves foraneas
            conexion.execute(
                "PRAGMA foreign_keys = ON"
            )

            crear_tablas(conexion)

            # Crear dos proyectos ficticios
            conexion.executemany(
                "INSERT INTO proyectos (id, nombre) "
                "VALUES (?, ?)",
                [
                    (1, "Laboratorio Web"),
                    (2, "Laboratorio API")
                ]
            )
            conexion.commit()

            politica = {
                "dominios": {"example.org"},
                "puertos": {443},
                "protocolos": {"https"}
            }

            # CASO 1: PROYECTO EXISTENTE

            guardar_politica_validada(
                conexion, 1, politica
            )

            print("CASO 1: Politica guardada correctamente")

            # CASO 2: PROYECTO INEXISTENTE

            try:
                guardar_politica_validada(
                    conexion, 99, politica
                )

            except sqlite3.IntegrityError:
                conexion.rollback()
                print("CASO 2: Proyecto inexistente rechazado")

            # CASO 3: POLITICA DUPLICADA

            try:
                guardar_politica_validada(
                    conexion, 1, politica
                )

            except sqlite3.IntegrityError:
                conexion.rollback()
                print("CASO 3: Politica duplicada rechazada")

            # CASO 4: PROYECTO SIN POLITICA

            pendiente = consultar_politica(
                conexion, 2
            )

            print(
                "CASO 4: Proyecto 2 sin politica:",
                pendiente is None
            )

            # CASO 5: ELIMINACION NO PERMITIDA

            try:
                conexion.execute(
                    "DELETE FROM proyectos WHERE id = ?",
                    (1,)
                )
                conexion.commit()

            except sqlite3.IntegrityError:
                conexion.rollback()
                print("CASO 5: Eliminacion protegida")

            # CASO 6: COMPROBAR DATOS CONSERVADOS

            conservada = consultar_politica(
                conexion, 1
            )

            existe = conexion.execute(
                "SELECT COUNT(*) FROM proyectos "
                "WHERE id = 1"
            ).fetchone()[0]

            print(
                "CASO 6: Datos conservados:",
                conservada == politica and existe == 1
            )

    print("BASE TEMPORAL ELIMINADA")


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("INTEGRIDAD REFERENCIAL")
    print("==============================")

    ejecutar_laboratorio()
