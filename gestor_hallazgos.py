from contextlib import closing
from base_datos import conectar

# =====================================
# MOONDETEX V0.20
# GESTOR DE HALLAZGOS
# =====================================

def obtener_hallazgos():

    with closing(conectar()) as conexion:

        hallazgos = conexion.execute("""
            SELECT
                p.nombre,
                h.titulo,
                h.detalle,
                h.fecha
            FROM hallazgos AS h
            JOIN proyectos AS p
                ON p.id = h.proyecto_id
            ORDER BY h.id DESC
        """).fetchall()

    return hallazgos



# =====================================
# MOONDETEX V0.20
# CONSULTAR HALLAZGOS CON ESTADO
# =====================================


def obtener_hallazgos_con_estado():

    with closing(conectar()) as conexion:

        hallazgos = conexion.execute("""
            SELECT
                h.id,
                p.nombre,
                h.titulo,
                h.detalle,
                h.fecha,
                h.estado
            FROM hallazgos AS h
            JOIN proyectos AS p
                ON p.id = h.proyecto_id
            ORDER BY h.id DESC
        """).fetchall()

    return hallazgos




# =====================================
# MOONDETEX V0.20
# ACTUALIZAR ESTADO DE HALLAZGOS
# =====================================

def actualizar_estado_hallazgo(hallazgo_id, nuevo_estado):

    # Estados permitidos
    estados_validos = (
        "Pendiente",
        "Revisado",
        "Descartado"
    )

    # Validar estado
    if nuevo_estado not in estados_validos:
        raise ValueError(
            "El estado seleccionado no es válido."
        )

    # Conectar con SQLite
    with closing(conectar()) as conexion:

        with conexion:

            cursor = conexion.execute("""
                UPDATE hallazgos
                SET estado = ?
                WHERE id = ?
            """, (nuevo_estado, hallazgo_id))

            actualizado = cursor.rowcount > 0

    return actualizado

