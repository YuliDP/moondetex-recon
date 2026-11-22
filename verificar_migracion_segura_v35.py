import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from base_datos import DB


# =====================================
# MOONDETEX - CLASE 35
# VERIFICACION SEGURA DE MIGRACION
# ORIGINAL: SOLO LECTURA
# =====================================

def contar_registros(conexion):

    tablas = conexion.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()

    resultado = {}

    for (nombre,) in tablas:

        # Proteger los nombres de tabla
        nombre_sql = nombre.replace('"', '""')

        cantidad = conexion.execute(
            f'SELECT COUNT(*) FROM "{nombre_sql}"'
        ).fetchone()[0]

        resultado[nombre] = cantidad

    return resultado


def verificar_migracion_segura():

    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontro moondetex.db."
        )

    with TemporaryDirectory(
        prefix="ensayo_seguro_",
        dir=DB.parent
    ) as temporal:

        copia = Path(temporal) / "copia_prueba.db"

        # Abrir la base original solo para leer
        with closing(
            sqlite3.connect(
                DB.as_uri() + "?mode=ro",
                uri=True
            )
        ) as original:

            with closing(
                sqlite3.connect(copia)
            ) as ensayo:

                # Copiar la base original
                original.backup(ensayo)

                ensayo.execute(
                    "PRAGMA foreign_keys = ON"
                )

                # Contar los datos ANTES
                antes = contar_registros(ensayo)

                if "politicas_proyecto" in antes:
                    raise ValueError(
                        "La tabla de politicas ya existe."
                    )

                # Crear la tabla SOLO EN LA COPIA
                ensayo.execute("""
                    CREATE TABLE politicas_proyecto (
                        proyecto_id INTEGER PRIMARY KEY,
                        dominios TEXT NOT NULL,
                        puertos TEXT NOT NULL,
                        protocolos TEXT NOT NULL,
                        fecha TEXT DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (proyecto_id)
                            REFERENCES proyectos(id)
                            ON DELETE RESTRICT
                    )
                """)

                ensayo.commit()

                # Contar los datos DESPUES
                despues = contar_registros(ensayo)

                # La tabla nueva debe estar vacia
                politicas = despues.pop(
                    "politicas_proyecto"
                )

                conservados = (antes == despues)

                # Comprobar integridad general
                integridad = ensayo.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]

                # Comprobar claves foraneas
                errores_fk = ensayo.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()

                print("\nTABLAS ORIGINALES:")

                for nombre, cantidad in antes.items():
                    print(
                        f"{nombre}: {cantidad} registros"
                    )

                print("\nRESULTADOS DEL ENSAYO")
                print("==============================")

                print(
                    "Registros conservados:",
                    conservados
                )

                print(
                    "Politicas nuevas:",
                    politicas
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
                    not conservados
                    or politicas != 0
                    or integridad != "ok"
                    or errores_fk
                ):
                    raise RuntimeError(
                        "El ensayo requiere revision."
                    )

                print(
                    "RESULTADO: ENSAYO APROBADO"
                )

    print("COPIA TEMPORAL ELIMINADA")
    print("BASE ORIGINAL: SIN MODIFICACIONES")


if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("VERIFICACION DE MIGRACION SEGURA")
    print("==============================")

    verificar_migracion_segura()
