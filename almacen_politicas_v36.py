"""Almacen de politicas sobre una conexion proporcionada por el llamador.

No abre bases de datos ni crea tablas. Requiere proyectos y politicas_proyecto.
Cada escritura usa un SAVEPOINT: si existe una transaccion externa, queda
pendiente de su commit o rollback. Sin transaccion externa, RELEASE confirma
solo la operacion actual. La conexion permanece abierta.
"""

import json
from contextlib import contextmanager
from uuid import uuid4

from guardado_seguro_politicas_v35 import validar_politica
from lector_politicas_v35 import cargar_politica


@contextmanager
def _operacion_atomica(conexion):
    # Identificador interno, independiente de cualquier entrada del usuario.
    nombre = "politica_" + uuid4().hex
    conexion.execute(f"SAVEPOINT {nombre}")
    try:
        yield
        conexion.execute(f"RELEASE SAVEPOINT {nombre}")
    except BaseException:
        conexion.execute(f"ROLLBACK TO SAVEPOINT {nombre}")
        conexion.execute(f"RELEASE SAVEPOINT {nombre}")
        raise


def _comprobar_proyecto(conexion, proyecto_id):
    # No depender de PRAGMA foreign_keys para impedir politicas huerfanas.
    fila = conexion.execute(
        "SELECT id FROM proyectos WHERE id = ?", (proyecto_id,)
    ).fetchone()
    if fila is None:
        raise ValueError("El proyecto no existe.")


def _serializar(politica):
    return tuple(
        json.dumps(sorted(politica[clave]))
        for clave in ("dominios", "puertos", "protocolos")
    )


def guardar_politica_proyecto(conexion, proyecto_id, politica):
    """Crear una politica; una existente produce sqlite3.IntegrityError."""
    validar_politica(proyecto_id, politica)
    valores = _serializar(politica)
    with _operacion_atomica(conexion):
        _comprobar_proyecto(conexion, proyecto_id)
        conexion.execute(
            """
            INSERT INTO politicas_proyecto
                (proyecto_id, dominios, puertos, protocolos)
            VALUES (?, ?, ?, ?)
            """,
            (proyecto_id, *valores),
        )
    return True


def consultar_politica_proyecto(conexion, proyecto_id):
    """Leer y validar; None indica un proyecto existente sin politica."""
    return cargar_politica(conexion, proyecto_id)


def actualizar_politica_proyecto(conexion, proyecto_id, politica):
    """Actualizar una politica existente sin cambiar las de otros proyectos."""
    validar_politica(proyecto_id, politica)
    valores = _serializar(politica)
    with _operacion_atomica(conexion):
        _comprobar_proyecto(conexion, proyecto_id)
        cursor = conexion.execute(
            """
            UPDATE politicas_proyecto
            SET dominios = ?, puertos = ?, protocolos = ?
            WHERE proyecto_id = ?
            """,
            (*valores, proyecto_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("El proyecto no tiene una politica configurada.")
    return True
