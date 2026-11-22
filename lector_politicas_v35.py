import sqlite3
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing

from guardado_seguro_politicas_v35 import validar_politica


# =====================================
# MOONDETEX - CLASE 35 (BLINDADO)
# LECTOR DE POLITICAS POR PROYECTO
# =====================================

def _rechazar_constante_json(valor):
    raise ValueError(
        f"Constante JSON no permitida en politica: {valor}"
    )


def _decodificar_lista_json(texto_crudo, campo):
    if not isinstance(texto_crudo, str):
        raise ValueError(
            f"El campo almacenado '{campo}' no es texto JSON."
        )

    try:
        datos = json.loads(
            texto_crudo,
            parse_constant=_rechazar_constante_json
        )
    except (ValueError, TypeError) as error:
        raise ValueError(
            f"La politica almacenada esta dañada en '{campo}'."
        ) from error

    if not isinstance(datos, list) or not datos:
        raise ValueError(
            f"La politica almacenada tiene datos invalidos en '{campo}'."
        )

    # Detectar manipulacion manual con elementos duplicados en SQLite
    try:
        conjunto = set(datos)
    except TypeError as error:
        raise ValueError(
            f"Elementos no validos en '{campo}'."
        ) from error

    if len(conjunto) != len(datos):
        raise ValueError(
            f"Se detectaron valores duplicados en '{campo}'."
        )

    return conjunto


def cargar_politica(conexion, proyecto_id):

    if type(proyecto_id) is not int or proyecto_id <= 0:
        raise ValueError("ID de proyecto invalido.")

    # Comprobar si el proyecto existe
    proyecto = conexion.execute(
        "SELECT id FROM proyectos WHERE id = ?",
        (proyecto_id,)
    ).fetchone()

    if proyecto is None:
        raise ValueError("El proyecto no existe.")

    # Buscar su politica
    fila = conexion.execute(
        """
        SELECT dominios, puertos, protocolos
        FROM politicas_proyecto
        WHERE proyecto_id = ?
        """,
        (proyecto_id,)
    ).fetchone()

    if fila is None:
        return None

    # Recuperar y verificar estructura JSON estricta
    politica = {
        "dominios": _decodificar_lista_json(fila[0], "dominios"),
        "puertos": _decodificar_lista_json(fila[1], "puertos"),
        "protocolos": _decodificar_lista_json(fila[2], "protocolos"),
    }

    # Aplicar exactamente las mismas reglas estrictas de guardado
    validar_politica(proyecto_id, politica)

    return politica


# =====================================
# LABORATORIO CON SQLITE TEMPORAL
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 35 (BLINDADO)")
    print("LECTURA DE POLITICAS POR PROYECTO")
    print("==============================")

    with TemporaryDirectory() as temporal:

        db = Path(temporal) / "laboratorio.db"

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
                    (1, "Laboratorio Pendiente"),
                    (2, "Laboratorio Bug Bounty Wildcard"),
                    (3, "Laboratorio Manipulado en DB")
                ]
            )

            # Proyecto 2: politica valida con wildcard Bug Bounty
            conexion.execute(
                """
                INSERT INTO politicas_proyecto
                VALUES (?, ?, ?, ?)
                """,
                (
                    2,
                    json.dumps(["*.example.net", "example.net"]),
                    json.dumps([443, 8443]),
                    json.dumps(["https"])
                )
            )

            # Proyecto 3: simulacion de alteracion directa en SQLite (IP interna)
            conexion.execute(
                """
                INSERT INTO politicas_proyecto
                VALUES (?, ?, ?, ?)
                """,
                (
                    3,
                    json.dumps(["127.0.0.1"]),
                    json.dumps([443]),
                    json.dumps(["https"])
                )
            )

            conexion.commit()

        # Abrir la base temporal en solo lectura
        with closing(
            sqlite3.connect(
                db.as_uri() + "?mode=ro",
                uri=True
            )
        ) as conexion:

            for proyecto_id in (1, 2, 3, 99):

                print("\nPROYECTO:", proyecto_id)

                try:
                    politica = cargar_politica(
                        conexion, proyecto_id
                    )

                    if politica is None:
                        print("POLITICA: PENDIENTE")
                        print("ANALISIS: BLOQUEADO")

                    else:
                        print("POLITICA: ENCONTRADA")
                        print("Dominios:", politica["dominios"])
                        print("Puertos:", politica["puertos"])
                        print("Protocolos:", politica["protocolos"])

                except ValueError as error:
                    print("RECHAZADO:", error)

    print("\nBASE TEMPORAL ELIMINADA")