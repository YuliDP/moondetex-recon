"""Componente independiente de politicas. Importarlo no abre ventanas ni bases.

El llamador conserva la propiedad y la transaccion de la conexion SQLite.
El permiso de escritura debe ser True explicitamente; no se deduce del esquema,
del proyecto ni de su alcance. La fase A no integra este modulo con main.py.
"""

import argparse
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from almacen_politicas_v36 import (
    actualizar_politica_proyecto,
    consultar_politica_proyecto,
    guardar_politica_proyecto,
)
from guardado_seguro_politicas_v35 import validar_politica
from base_datos import conectar


TABLA_AUSENTE = "TABLA_AUSENTE"
PENDIENTE = "PENDIENTE"
CONFIGURADA = "CONFIGURADA"
INVALIDA = "INVALIDA"
ERROR_ALMACENAMIENTO = "ERROR_ALMACENAMIENTO"


def comprobar_almacenamiento(conexion):
    """Inspeccionar sin crear tablas ni cambiar configuracion de la conexion."""
    try:
        objeto = conexion.execute(
            "SELECT type FROM sqlite_master WHERE name = ?",
            ("politicas_proyecto",),
        ).fetchone()
        if objeto is None:
            return TABLA_AUSENTE, "Almacenamiento pendiente de migracion segura."
        if objeto[0] != "table":
            return ERROR_ALMACENAMIENTO, "politicas_proyecto no es una tabla."
        columnas = conexion.execute("PRAGMA table_info(politicas_proyecto)").fetchall()
        por_nombre = {fila[1]: fila for fila in columnas}
        claves = [fila[1] for fila in columnas if fila[5]]
        if (
            claves != ["proyecto_id"]
            or por_nombre["proyecto_id"][2].upper() != "INTEGER"
            or any(
                nombre not in por_nombre
                or por_nombre[nombre][2].upper() != "TEXT"
                or not por_nombre[nombre][3]
                for nombre in ("dominios", "puertos", "protocolos")
            )
        ):
            return ERROR_ALMACENAMIENTO, "El esquema de politicas es incompatible."
        return "DISPONIBLE", "Tabla disponible; esto no habilita el guardado."
    except sqlite3.Error as error:
        return ERROR_ALMACENAMIENTO, f"No se pudo consultar el almacenamiento: {error}"


def consultar_estado(conexion, proyecto_id):
    """Devolver estado, detalle y politica validada, sin escribir ni resolver DNS."""
    resultado = {"estado": ERROR_ALMACENAMIENTO, "detalle": "", "politica": None}
    if type(proyecto_id) is not int or proyecto_id <= 0:
        resultado["detalle"] = "ID de proyecto invalido."
        return resultado
    estado, detalle = comprobar_almacenamiento(conexion)
    if estado != "DISPONIBLE":
        resultado.update(estado=estado, detalle=detalle)
        return resultado
    try:
        proyecto = conexion.execute(
            "SELECT id FROM proyectos WHERE id = ?", (proyecto_id,)
        ).fetchone()
        if proyecto is None:
            resultado["detalle"] = "El proyecto no existe."
            return resultado
        try:
            politica = consultar_politica_proyecto(conexion, proyecto_id)
        except ValueError as error:
            resultado.update(estado=INVALIDA, detalle=str(error))
            return resultado
        resultado.update(
            estado=PENDIENTE if politica is None else CONFIGURADA,
            detalle="Sin politica configurada." if politica is None else "Politica validada.",
            politica=politica,
        )
    except sqlite3.Error as error:
        resultado["detalle"] = f"No se pudo consultar el proyecto o su politica: {error}"
    return resultado


def convertir_campos(proyecto_id, dominios_texto, puertos_texto, protocolos):
    """Convertir entradas explicitas. No agrega dominios, puertos ni protocolos."""
    if not isinstance(dominios_texto, str) or not isinstance(puertos_texto, str):
        raise ValueError("Los dominios y puertos deben ser texto.")
    partes = puertos_texto.split(",")
    if any(not parte.strip() or not parte.strip().isascii()
           or not parte.strip().isdecimal() for parte in partes):
        raise ValueError("Escribe puertos enteros separados por comas.")
    if not isinstance(protocolos, (set, list, tuple)):
        raise ValueError("Selecciona los protocolos explicitamente.")
    politica = {
        "dominios": [linea.strip() for linea in dominios_texto.splitlines() if linea.strip()],
        "puertos": [int(parte.strip()) for parte in partes],
        "protocolos": protocolos,
    }
    validar_politica(proyecto_id, politica)
    return {clave: set(valores) for clave, valores in politica.items()}

def guardar_desde_campos(
    conexion, proyecto_id, dominios_texto, puertos_texto, protocolos,
    permitir_guardado=True,
):
    """Barrera de escritura tambien para llamadas que omitan la interfaz visual."""
    #if permitir_guardado is not True:
      #  raise PermissionError("Guardado bloqueado: configuracion no habilitada.")
    estado = consultar_estado(conexion, proyecto_id)
    if estado["estado"] in (TABLA_AUSENTE, ERROR_ALMACENAMIENTO):
        raise ValueError(estado["detalle"])
    politica = convertir_campos(proyecto_id, dominios_texto, puertos_texto, protocolos)
    with closing(conectar()) as con_rw:
        with con_rw:
            if estado["estado"] == PENDIENTE:
                guardar_politica_proyecto(con_rw, proyecto_id, politica)
            else:
                actualizar_politica_proyecto(con_rw, proyecto_id, politica)
    return consultar_estado(conexion, proyecto_id)
           

def crear_formulario(
    contenedor, conexion, proyecto_id, nombre_proyecto,
    permitir_guardado=True, al_guardar=None, *, ctk_modulo=None, mensajes=None,
    paleta=None,
):
    """Abrir un formulario. Los widgets y mensajes admiten dobles en pruebas."""
    if ctk_modulo is None:
        import customtkinter as ctk_modulo
    if mensajes is None:
        from tkinter import messagebox as mensajes

    def colores(**roles):
        if paleta is None:
            return {}
        return {opcion: paleta[rol] for opcion, rol in roles.items()}

    ventana = ctk_modulo.CTkToplevel(contenedor, **colores(fg_color="FONDO"))
    ventana.title("Configurar politica")
    ventana.geometry("620x650")
    ventana.minsize(520, 560)
    ventana.transient(contenedor)
    panel = ctk_modulo.CTkScrollableFrame(ventana, **colores(fg_color="PANEL"))
    panel.pack(fill="both", expand=True, padx=12, pady=12)

    def etiqueta(texto):
        widget = ctk_modulo.CTkLabel(
            panel, text=texto, wraplength=480, justify="left",
            **colores(text_color="LAVANDA")
        )
        widget.pack(anchor="w", padx=10, pady=5)
        return widget

   
    etiqueta(f"Proyecto: {nombre_proyecto} | ID: {proyecto_id}")
    estado = consultar_estado(conexion, proyecto_id)
    estado_visual = etiqueta(f"{estado['estado']}: {estado['detalle']}")
    etiqueta("Configurar una politica no habilita conexiones de red.")
    # if permitir_guardado is not True:
    #     etiqueta("Guardado bloqueado. Se requiere habilitacion explicita tras la migracion segura.")
    if estado["estado"] == INVALIDA:
        etiqueta("Los datos invalidos no se precargan. Para repararlos, introduce todos los valores.")

    etiqueta("Dominios exactos autorizados (uno por linea):")
    dominios = ctk_modulo.CTkTextbox(
        panel, height=110, **colores(fg_color="TARJETA", text_color="BLANCO")
    )
    dominios.pack(fill="x", padx=10, pady=5)
    etiqueta("Puertos autorizados (separados por comas):")
    puertos = ctk_modulo.CTkEntry(
        panel, **colores(fg_color="TARJETA", text_color="BLANCO", border_color="LAVANDA")
    )
    puertos.pack(fill="x", padx=10, pady=5)
    etiqueta("Protocolos autorizados:")
    variables = {}
    for protocolo in ("http", "https"):
        variable = ctk_modulo.BooleanVar(master=ventana, value=False)
        variables[protocolo] = variable
        ctk_modulo.CTkCheckBox(
            panel, text=protocolo.upper(), variable=variable,
            **colores(fg_color="MORADO", hover_color="MORADO", text_color="LAVANDA")
        ).pack(anchor="w", padx=10, pady=5)

    politica = estado["politica"]
    if politica is not None:
        dominios.insert("1.0", "\n".join(sorted(politica["dominios"])))
        puertos.insert(0, ", ".join(str(p) for p in sorted(politica["puertos"])))
        for protocolo, variable in variables.items():
            variable.set(protocolo in politica["protocolos"])

    def guardar():
        # Comprobar antes de leer widgets, abrir otra operacion o invocar el almacen.
        #if permitir_guardado is not True:
            #mensajes.showwarning("Politicas", "Guardado bloqueado.", parent=ventana)
            #return False
        try:
            nuevo = guardar_desde_campos(
                conexion, proyecto_id, dominios.get("1.0", "end-1c"), puertos.get(),
                [p for p, variable in variables.items() if variable.get()],
                permitir_guardado=permitir_guardado,
            )
        except (ValueError, PermissionError, sqlite3.Error) as error:
            mensajes.showerror("No se guardo la politica", str(error), parent=ventana)
            return False
        estado_visual.configure(text=f"{nuevo['estado']}: {nuevo['detalle']}")
        mensajes.showinfo("Politicas", "Politica guardada.", parent=ventana)
        if al_guardar is not None:
            al_guardar(nuevo)
        return True

    habilitado = permitir_guardado is True and estado["estado"] not in (
        TABLA_AUSENTE, ERROR_ALMACENAMIENTO,
    )
    boton_guardar = ctk_modulo.CTkButton(
        panel, text="Guardar politica", command=guardar,
        state="normal",
        **colores(fg_color="MORADO", hover_color="MORADO", text_color="BLANCO",
                  text_color_disabled="GRIS"),
    )
    boton_guardar.pack(padx=10, pady=10)
    boton_cancelar = ctk_modulo.CTkButton(
        panel, text="Cancelar", command=ventana.destroy,
        **colores(fg_color="MORADO", hover_color="MORADO", text_color="BLANCO")
    )
    boton_cancelar.pack(padx=10, pady=5)
    return {
        "ventana": ventana, "estado": estado_visual,
        "dominios": dominios, "puertos": puertos, "protocolos": variables,
        "boton_guardar": boton_guardar, "boton_cancelar": boton_cancelar,
        "guardar": guardar,
    }


@contextmanager
def laboratorio_temporal(escenario="normal"):
    """Crear explicitamente un laboratorio desechable, nunca una base existente."""
    if escenario not in ("normal", "sin-tabla", "esquema-invalido"):
        raise ValueError("Escenario de laboratorio desconocido.")
    with TemporaryDirectory(prefix="moondetex_interfaz_v36_") as temporal:
        archivo = Path(temporal) / "laboratorio.db"
        with closing(sqlite3.connect(archivo)) as conexion:
            conexion.execute("PRAGMA foreign_keys = ON")
            conexion.execute("CREATE TABLE proyectos (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL)")
            conexion.executemany(
                "INSERT INTO proyectos VALUES (?, ?)",
                [(1, "Pendiente ficticio"), (2, "Configurado ficticio"), (3, "Invalido ficticio")],
            )
            if escenario == "esquema-invalido":
                conexion.execute("CREATE TABLE politicas_proyecto (proyecto_id INTEGER)")
            elif escenario == "normal":
                conexion.execute("""
                    CREATE TABLE politicas_proyecto (
                        proyecto_id INTEGER PRIMARY KEY,
                        dominios TEXT NOT NULL,
                        puertos TEXT NOT NULL,
                        protocolos TEXT NOT NULL,
                        FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE RESTRICT
                    )
                """)
            conexion.commit()
            if escenario == "normal":
                # Datos ficticios del laboratorio; nunca valores por defecto del formulario.
                guardar_politica_proyecto(conexion, 2, {
                    "dominios": {"example.org"}, "puertos": {443}, "protocolos": {"https"},
                })
                conexion.execute(
                    "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                    (3, "JSON_INVALIDO", "[443]", '["https"]'),
                )
                conexion.commit()
            yield conexion


def ejecutar_laboratorio(escenario="normal", permitir_guardado=True):
    """Vista manual independiente. El permiso solo afecta al SQLite temporal."""
    import customtkinter as ctk

    with laboratorio_temporal(escenario) as conexion:
        raiz = ctk.CTk()
        raiz.title("MOONDETEX | Laboratorio temporal de politicas")
        raiz.geometry("740x460")
        ctk.CTkLabel(
            raiz, text="LABORATORIO TEMPORAL | Proyectos ficticios | Sin conexiones de red"
        ).pack(pady=12)
        ctk.CTkLabel(
            raiz, text="Escritura temporal habilitada" if permitir_guardado else "Guardado bloqueado"
        ).pack(pady=5)
        etiquetas = {}

        def refrescar(_resultado=None):
            for identificador, etiqueta in etiquetas.items():
                estado = consultar_estado(conexion, identificador)
                etiqueta.configure(text=f"{estado['estado']}: {estado['detalle']}")

        for proyecto_id, nombre in conexion.execute("SELECT id, nombre FROM proyectos ORDER BY id"):
            fila = ctk.CTkFrame(raiz)
            fila.pack(fill="x", padx=15, pady=8)
            ctk.CTkLabel(fila, text=f"{proyecto_id} | {nombre}").pack(anchor="w", padx=10)
            etiquetas[proyecto_id] = ctk.CTkLabel(fila, text="", wraplength=650)
            etiquetas[proyecto_id].pack(anchor="w", padx=10)
            ctk.CTkButton(
                fila, text="Configurar politica",
                command=lambda pid=proyecto_id, n=nombre: crear_formulario(
                    raiz, conexion, pid, n, permitir_guardado=permitir_guardado,
                    al_guardar=refrescar,
                ),
            ).pack(anchor="e", padx=10, pady=5)
        refrescar()
        raiz.mainloop()


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description="Solo laboratorio SQLite temporal.")
    argumentos.add_argument(
        "--escenario", choices=("normal", "sin-tabla", "esquema-invalido"), default="normal"
    )
    argumentos.add_argument("--permitir-guardado-temporal", action="store_true")
    opciones = argumentos.parse_args()
    ejecutar_laboratorio(opciones.escenario, opciones.permitir_guardado_temporal)
