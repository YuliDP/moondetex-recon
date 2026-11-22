"""Migracion explicita; importar o ejecutar este archivo no abre ninguna base.

El llamador proporciona una conexion sin transaccion y los siete nombres
originales. No se deducen nombres de tablas que no hemos inspeccionado.
Los campos TEXT contienen JSON validado por el almacen/lector existentes.
"""

from pathlib import Path
import sqlite3

from comparar_datos_migracion_v35 import obtener_huellas


ESQUEMA_POLITICAS = """CREATE TABLE politicas_proyecto (
    proyecto_id INTEGER PRIMARY KEY,
    dominios TEXT NOT NULL,
    puertos TEXT NOT NULL,
    protocolos TEXT NOT NULL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE RESTRICT
)"""


def verificar_integridad(conexion):
    """Exigir todos los resultados de integridad y relaciones correctos."""
    if conexion.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise RuntimeError("Error de integridad SQLite.")
    if conexion.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Relaciones inconsistentes.")


def obtener_manifiesto(conexion):
    """Capturar contenido, esquema completo y secuencias internas."""
    esquema = [list(fila) for fila in conexion.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "ORDER BY type, name"
    ).fetchall()]
    secuencias = None
    if any(fila[1] == "sqlite_sequence" for fila in esquema):
        secuencias = [list(fila) for fila in conexion.execute(
            "SELECT name, seq FROM sqlite_sequence ORDER BY name, seq"
        ).fetchall()]
    return {"tablas": obtener_huellas(conexion), "esquema": esquema,
            "secuencias": secuencias}


def verificar_conservacion(conexion, antes):
    """Permitir solamente la nueva tabla vacia con el DDL definitivo."""
    despues = obtener_manifiesto(conexion)
    nueva = despues["tablas"].pop("politicas_proyecto", None)
    objetos = [fila for fila in despues["esquema"]
               if fila[1] == "politicas_proyecto"]
    esperado = [["table", "politicas_proyecto", "politicas_proyecto",
                 ESQUEMA_POLITICAS]]
    if objetos != esperado or nueva is None or nueva["cantidad"] != 0:
        raise RuntimeError("La tabla nueva no coincide o no esta vacia.")
    despues["esquema"] = [fila for fila in despues["esquema"]
                           if fila[1] != "politicas_proyecto"]
    if despues != antes:
        raise RuntimeError("Cambio inesperado de datos, esquema o secuencias.")


def _validar_destino(conexion):
    # Defensa adicional: tampoco aceptar una conexion explicita a la base real.
    real = Path(__file__).resolve().parent / "moondetex.db"
    if conexion.execute("SELECT 1 FROM sqlite_temp_master LIMIT 1").fetchone():
        raise ValueError("No se admiten objetos temporales que oculten el esquema.")
    for _, nombre, archivo in conexion.execute("PRAGMA database_list"):
        if nombre not in ("main", "temp"):
            raise ValueError("No se admiten bases adjuntas.")
        if archivo:
            ruta = Path(archivo).resolve()
            if (ruta.name.lower() == "moondetex.db" or ruta == real
                    or (real.exists() and ruta.samefile(real))):
                raise ValueError("La base real esta excluida de esta fase.")


def migrar_politicas(conexion, *, tablas_originales):
    """Crear solo en un destino autorizado por el llamador; nunca abrir rutas.

Rechaza transacciones externas sin confirmarlas ni revertirlas. Restaura la
configuracion foreign_keys del llamador. Toda validacion final precede COMMIT.
"""
    if conexion.in_transaction:
        raise ValueError("Se requiere una conexion sin transaccion activa.")
    nombres = tuple(tablas_originales)
    if (len(nombres) != 7 or any(type(n) is not str for n in nombres)
            or len(set(nombres)) != 7 or "politicas_proyecto" in nombres
            or not {"proyectos", "hallazgos", "historial_analisis"}.issubset(nombres)):
        raise ValueError("Indica explicitamente las siete tablas originales.")
    _validar_destino(conexion)
    fk = conexion.execute("PRAGMA foreign_keys").fetchone()[0]
    try:
        conexion.execute("PRAGMA foreign_keys = ON")
        if conexion.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RuntimeError("No se pudieron activar las claves foraneas.")
        conexion.execute("BEGIN IMMEDIATE")
        if conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE name = ? COLLATE NOCASE",
            ("politicas_proyecto",),
        ).fetchone():
            raise ValueError("Ya existe un objeto politicas_proyecto.")
        verificar_integridad(conexion)
        antes = obtener_manifiesto(conexion)
        if set(antes["tablas"]) != set(nombres):
            raise ValueError("El inventario no coincide con las siete tablas.")
        columnas = conexion.execute("PRAGMA table_info(proyectos)").fetchall()
        claves = [fila for fila in columnas if fila[5]]
        if (len(claves) != 1 or claves[0][1] != "id"
                or claves[0][2].upper() != "INTEGER"):
            raise ValueError("Esquema incompatible: proyectos.id debe ser INTEGER PRIMARY KEY.")
        conexion.execute(ESQUEMA_POLITICAS)
        verificar_conservacion(conexion, antes)
        verificar_integridad(conexion)
        conexion.execute("COMMIT")
        return antes
    except BaseException:
        if conexion.in_transaction:
            conexion.execute("ROLLBACK")
        raise
    finally:
        conexion.execute("PRAGMA foreign_keys = ON" if fk else "PRAGMA foreign_keys = OFF")


if __name__ == "__main__":
    print("Sin acciones: se requiere una conexion explicita a una base de ensayo.")
