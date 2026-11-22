import sqlite3
import json

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from lector_politicas_v35 import cargar_politica
from politica_objetivos_v35 import aplicar_politica_local


# =====================================
# MOONDETEX - CLASE 35
# VERIFICADOR DE POLITICAS GUARDADAS
# =====================================

def verificar_objetivo_guardado(
    conexion,
    proyecto_id,
    url,
    resolver
):

    # 1. Cargar la politica del proyecto
    politica = cargar_politica(
        conexion,
        proyecto_id
    )

    # 2. Bloquear proyectos sin politica
    if politica is None:
        raise ValueError(
            "El proyecto no tiene una politica configurada."
        )

    # 3. Aplicar los controles de seguridad
    return aplicar_politica_local(
        url,
        politica,
        resolver
    )


# =====================================
# LABORATORIO CON SQLITE TEMPORAL
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35")
    print("VERIFICACION CON POLITICAS GUARDADAS")
    print("==============================")

    with TemporaryDirectory() as temporal:

        db = Path(temporal) / "laboratorio.db"

        # Crear datos ficticios
        with closing(sqlite3.connect(db)) as conexion:

            conexion.execute("PRAGMA foreign_keys = ON")

            conexion.execute("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL
                )
            """)

            conexion.execute("""
                CREATE TABLE politicas_proyecto (
                    proyecto_id INTEGER PRIMARY KEY,
                    dominios TEXT NOT NULL,
                    puertos TEXT NOT NULL,
                    protocolos TEXT NOT NULL,
                    FOREIGN KEY (proyecto_id)
                        REFERENCES proyectos(id)
                )
            """)

            conexion.executemany(
                "INSERT INTO proyectos VALUES (?, ?)",
                [
                    (1, "Laboratorio Web"),
                    (2, "Laboratorio API")
                ]
            )

            # Solo el proyecto 2 tiene politica
            conexion.execute(
                """
                INSERT INTO politicas_proyecto
                VALUES (?, ?, ?, ?)
                """,
                (
                    2,
                    json.dumps(["example.net"]),
                    json.dumps([8443]),
                    json.dumps(["https"])
                )
            )

            conexion.commit()

        # DNS completamente simulado
        def resolver_simulado(dominio):

            respuestas = {
                "example.net": ["1.1.1.1"]
            }

            return respuestas.get(dominio, [])

        casos = [
            (
                "API autorizada",
                2,
                "https://example.net:8443/docs"
            ),
            (
                "Puerto incorrecto",
                2,
                "https://example.net"
            ),
            (
                "Proyecto sin politica",
                1,
                "https://example.org"
            ),
            (
                "Proyecto inexistente",
                99,
                "https://example.net:8443"
            )
        ]

        # Abrir SQLite exclusivamente en lectura
        with closing(
            sqlite3.connect(
                db.as_uri() + "?mode=ro",
                uri=True
            )
        ) as conexion:

            for nombre, proyecto_id, url in casos:

                try:
                    resultado = verificar_objetivo_guardado(
                        conexion,
                        proyecto_id,
                        url,
                        resolver_simulado
                    )

                    print("\nPERMITIDO:", nombre)
                    print("Puerto:", resultado["puerto"])
                    print("IP:", resultado["ips"])

                except ValueError as error:

                    print("\nRECHAZADO:", nombre)
                    print("Motivo:", error)

    print("\nBASE TEMPORAL ELIMINADA")
