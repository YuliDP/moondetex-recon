# =====================================
# MOONDETEX V0.20
# GESTOR DE PROYECTOS
# =====================================

from contextlib import closing
from base_datos import conectar


# CONSULTAR PROYECTOS GUARDADOS
def obtener_proyectos():

    with closing(conectar()) as con:

        proyectos = con.execute("""
            SELECT id, nombre, alcance, notas, fecha
            FROM proyectos
            ORDER BY id DESC
        """).fetchall()

    return proyectos



# =====================================
# MOONDETEX V0.20
# ELIMINAR PROYECTOS
# =====================================

def eliminar_proyecto_bd(proyecto_id):

    # Validar el identificador
    if not isinstance(proyecto_id, int) or proyecto_id <= 0:
        raise ValueError(
            "El identificador del proyecto no es válido."
        )

    # Abrir la conexión
    with closing(conectar()) as con:

        # Ejecutar dentro de una transacción
        with con:

            cursor = con.execute(
                "DELETE FROM proyectos WHERE id = ?",
                (proyecto_id,)
            )

            eliminado = cursor.rowcount > 0

    return eliminado

