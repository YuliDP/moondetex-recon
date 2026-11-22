from contextlib import closing
from base_datos import conectar

# =====================================
# MOONDETEX V0.20
# GESTOR DE PROYECTOS
# =====================================


# CONSULTAR PROYECTOS
def obtener_proyectos():

    with closing(conectar()) as con:

        proyectos = con.execute("""
            SELECT id, nombre, alcance, notas, fecha
            FROM proyectos
            ORDER BY id DESC
        """).fetchall()

    return proyectos


# GUARDAR PROYECTOS
def guardar_proyecto(nombre, alcance, notas):

    nombre = nombre.strip()
    alcance = alcance.strip()
    notas = notas.strip()

    if not nombre or not alcance:
        raise ValueError(
            "El nombre y el alcance son obligatorios."
        )

    with closing(conectar()) as con:

        with con:

            cursor = con.execute("""
                INSERT INTO proyectos
                (nombre, alcance, notas)
                VALUES (?, ?, ?)
            """, (nombre, alcance, notas))

            proyecto_id = cursor.lastrowid

    return proyecto_id


# ELIMINAR PROYECTOS
def eliminar_proyecto_bd(proyecto_id):

    if not isinstance(proyecto_id, int) or proyecto_id <= 0:
        raise ValueError(
            "El identificador del proyecto no es válido."
        )

    with closing(conectar()) as con:

        with con:

            cursor = con.execute(
                "DELETE FROM proyectos WHERE id = ?",
                (proyecto_id,)
            )

            eliminado = cursor.rowcount > 0

    return eliminado
