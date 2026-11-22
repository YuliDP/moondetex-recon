
import sqlite3
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

# =====================================
# MOONDETEX V0.5
# =====================================

CARPETA = Path(__file__).resolve().parent
DB = CARPETA / "moondetex.db"
LOGO = CARPETA / "moondetex_logo.png"

# Colores oficiales
FONDO = "#12121A"
PANEL = "#1E1E2E"
TARJETA = "#28263A"
MORADO = "#6C3BFF"
ROSA = "#FF4FA3"
LAVANDA = "#C9B6FF"
BLANCO = "#F5F2FF"
GRIS = "#B8B2D9"

ctk.set_appearance_mode("dark")


# =====================================
# BASE DE DATOS
# =====================================

def conectar():
    conexion = sqlite3.connect(DB)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def inicializar_bd():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS proyectos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                alcance TEXT NOT NULL,
                notas TEXT NOT NULL DEFAULT '',
                fecha TEXT NOT NULL DEFAULT
                    (datetime('now','localtime'))
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS hallazgos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER NOT NULL,
                clave TEXT NOT NULL,
                titulo TEXT NOT NULL,
                detalle TEXT NOT NULL,
                fecha TEXT NOT NULL DEFAULT
                    (datetime('now','localtime')),
                FOREIGN KEY (proyecto_id)
                    REFERENCES proyectos(id)
                    ON DELETE CASCADE,
                UNIQUE(proyecto_id, clave)
            )
        """)


def proyectos():
    with conectar() as con:
        return con.execute(
            "SELECT id, nombre, alcance, notas, fecha "
            "FROM proyectos ORDER BY id DESC"
        ).fetchall()


def guardar_proyecto(nombre, alcance, notas):
    with conectar() as con:
        con.execute(
            "INSERT INTO proyectos "
            "(nombre, alcance, notas) VALUES (?, ?, ?)",
            (nombre, alcance, notas)
        )


def eliminar_proyecto(pid):
    confirmar = messagebox.askyesno(
        "MOONDETEX",
        "¿Eliminar este proyecto y sus observaciones?"
    )

    if not confirmar:
        return

    with conectar() as con:
        con.execute(
            "DELETE FROM proyectos WHERE id = ?",
            (pid,)
        )

    mostrar("Proyectos")


def consultar_hallazgos():
    with conectar() as con:
        return con.execute("""
            SELECT p.nombre, h.titulo, h.detalle, h.fecha
            FROM hallazgos h
            JOIN proyectos p ON p.id = h.proyecto_id
            ORDER BY h.id DESC
        """).fetchall()


# =====================================
# MOTOR DE ANALISIS
# =====================================

def analizar_cabeceras(texto):

    lineas = [
        linea.strip()
        for linea in texto.splitlines()
        if linea.strip()
    ]

    if not lineas or not lineas[0].upper().startswith("HTTP/"):
        raise ValueError(
            "La respuesta debe empezar por HTTP/1.1 o HTTP/2."
        )

    cabeceras = {}

    for linea in lineas[1:]:
        if ":" in linea:
            nombre, valor = linea.split(":", 1)
            cabeceras[nombre.strip().lower()] = valor.strip()

    if "content-type" not in cabeceras:
        raise ValueError(
            "Incluye Content-Type para aplicar las reglas."
        )

    observaciones = []

    tipo = cabeceras["content-type"].lower()

    # Las reglas siguientes son para HTML
    if "text/html" not in tipo:
        return observaciones

    # Revisar Content Security Policy
    csp = cabeceras.get(
        "content-security-policy", ""
    )

    if not csp:
        observaciones.append((
            "csp",
            "Política CSP no observada",
            "No aparece Content-Security-Policy. "
            "Revisar si la aplicación HTML necesita CSP."
        ))

    # Revisar restricciones de marcos
    tiene_frame_ancestors = (
        "frame-ancestors" in csp.lower()
    )

    tiene_xframe = (
        "x-frame-options" in cabeceras
    )

    if not tiene_frame_ancestors and not tiene_xframe:
        observaciones.append((
            "frames",
            "Restricción de marcos no observada",
            "No aparecen frame-ancestors ni "
            "X-Frame-Options. Revisar si la página "
            "debe permitir su inserción en marcos."
        ))

    # Revisar protección contra MIME sniffing
    nosniff = cabeceras.get(
        "x-content-type-options", ""
    ).lower()

    if nosniff != "nosniff":
        observaciones.append((
            "nosniff",
            "X-Content-Type-Options por revisar",
            "No aparece X-Content-Type-Options: "
            "nosniff. Comprobar la configuración."
        ))

    return observaciones


def guardar_observaciones(pid, observaciones):

    # Sustituir observaciones anteriores del proyecto
    with conectar() as con:

        con.execute(
            "DELETE FROM hallazgos WHERE proyecto_id = ?",
            (pid,)
        )

        con.executemany(
            "INSERT INTO hallazgos "
            "(proyecto_id, clave, titulo, detalle) "
            "VALUES (?, ?, ?, ?)",
            [
                (pid, clave, titulo, detalle)
                for clave, titulo, detalle in observaciones
            ]
        )


# =====================================
# INICIAR BASE DE DATOS
# =====================================

inicializar_bd()


# =====================================
# VENTANA PRINCIPAL
# =====================================

ventana = ctk.CTk()

ventana.title("MOONDETEX V0.5")
ventana.geometry("1100x720")
ventana.minsize(900, 600)
ventana.configure(fg_color=FONDO)

ventana.grid_rowconfigure(0, weight=1)
ventana.grid_columnconfigure(1, weight=1)


# =====================================
# MENU LATERAL
# =====================================

menu = ctk.CTkFrame(
    ventana,
    fg_color=PANEL,
    width=220,
    corner_radius=0
)

menu.grid(row=0, column=0, sticky="nsew")
menu.grid_propagate(False)


# =====================================
# LOGO LUNAR
# =====================================

if LOGO.is_file():

    try:
        with Image.open(LOGO) as archivo:
            imagen = archivo.convert("RGBA")

        logo = ctk.CTkImage(
            light_image=imagen,
            dark_image=imagen,
            size=(105, 105)
        )

        ctk.CTkLabel(
            menu,
            image=logo,
            text=""
        ).pack(pady=(22, 5))

    except (OSError, ValueError):
        ctk.CTkLabel(
            menu,
            text="MOON",
            text_color=LAVANDA
        ).pack(pady=30)

else:
    ctk.CTkLabel(
        menu,
        text="MOON",
        text_color=LAVANDA
    ).pack(pady=30)


ctk.CTkLabel(
    menu,
    text="MOONDETEX",
    font=("Segoe UI", 21, "bold"),
    text_color=ROSA
).pack(pady=3)

ctk.CTkLabel(
    menu,
    text="SECURITY RESEARCH",
    font=("Segoe UI", 10),
    text_color=LAVANDA
).pack(pady=(0, 25))


# =====================================
# PANEL PRINCIPAL
# =====================================

principal = ctk.CTkFrame(
    ventana,
    fg_color="transparent"
)

principal.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=25,
    pady=22
)


secciones = [
    "Dashboard",
    "Proyectos",
    "Análisis",
    "Hallazgos",
    "Reportes",
    "Configuración"
]

botones = {}


# =====================================
# FUNCIONES DE INTERFAZ
# =====================================

def encabezado(titulo, descripcion):

    ctk.CTkLabel(
        principal,
        text=titulo,
        text_color=BLANCO,
        font=("Segoe UI", 29, "bold")
    ).pack(anchor="w", pady=(5, 3))

    ctk.CTkLabel(
        principal,
        text=descripcion,
        text_color=GRIS,
        font=("Segoe UI", 12)
    ).pack(anchor="w", pady=(0, 18))


def crear_tarjeta(padre, titulo, detalle):

    tarjeta = ctk.CTkFrame(
        padre,
        fg_color=TARJETA,
        corner_radius=12
    )

    tarjeta.pack(
        fill="x",
        padx=10,
        pady=6
    )

    ctk.CTkLabel(
        tarjeta,
        text=titulo,
        text_color=LAVANDA,
        font=("Segoe UI", 15, "bold"),
        anchor="w"
    ).pack(
        fill="x",
        padx=14,
        pady=(10, 2)
    )

    ctk.CTkLabel(
        tarjeta,
        text=detalle,
        text_color=GRIS,
        justify="left",
        anchor="w",
        wraplength=530
    ).pack(
        fill="x",
        padx=14,
        pady=(0, 10)
    )

    return tarjeta


# =====================================
# DASHBOARD
# =====================================

def pantalla_dashboard():

    encabezado(
        "Dashboard",
        "Resumen general de MOONDETEX"
    )

    tarjeta = ctk.CTkFrame(
        principal,
        fg_color=PANEL,
        corner_radius=16
    )

    tarjeta.pack(fill="both", expand=True)

    ctk.CTkLabel(
        tarjeta,
        text="Bienvenida a MOONDETEX",
        text_color=ROSA,
        font=("Segoe UI", 25, "bold")
    ).pack(pady=(65, 12))

    ctk.CTkLabel(
        tarjeta,
        text="VULNERABILITY DETECTION & ANALYSIS",
        text_color=LAVANDA
    ).pack(pady=8)

    total_proyectos = len(proyectos())
    total_hallazgos = len(consultar_hallazgos())

    ctk.CTkLabel(
        tarjeta,
        text=(
            f"Proyectos: {total_proyectos}   |   "
            f"Observaciones: {total_hallazgos}"
        ),
        text_color=BLANCO,
        font=("Segoe UI", 16)
    ).pack(pady=25)

    ctk.CTkButton(
        tarjeta,
        text="ABRIR ANÁLISIS",
        fg_color=MORADO,
        hover_color="#5030BF",
        command=lambda: mostrar("Análisis")
    ).pack(pady=10)

    ctk.CTkLabel(
        tarjeta,
        text=(
            "Primera versión de análisis sin conexión. "
            "Solo ejemplos de laboratorio."
        ),
        text_color=GRIS,
        wraplength=480
    ).pack(pady=18)


# =====================================
# PANTALLA PROYECTOS
# =====================================

def pantalla_proyectos():

    encabezado(
        "Proyectos",
        "Organiza tus laboratorios autorizados"
    )

    formulario = ctk.CTkFrame(
        principal,
        fg_color=PANEL,
        corner_radius=14
    )

    formulario.pack(fill="x", pady=(0, 12))

    ctk.CTkLabel(
        formulario,
        text="Crear nuevo proyecto",
        text_color=ROSA,
        font=("Segoe UI", 17, "bold")
    ).pack(anchor="w", padx=15, pady=(12, 6))

    nombre = ctk.CTkEntry(
        formulario,
        placeholder_text="Nombre del proyecto",
        fg_color=TARJETA
    )
    nombre.pack(fill="x", padx=15, pady=4)

    alcance = ctk.CTkEntry(
        formulario,
        placeholder_text="Alcance autorizado o laboratorio",
        fg_color=TARJETA
    )
    alcance.pack(fill="x", padx=15, pady=4)

    notas = ctk.CTkEntry(
        formulario,
        placeholder_text="Notas opcionales",
        fg_color=TARJETA
    )
    notas.pack(fill="x", padx=15, pady=4)

    def guardar():

        n = nombre.get().strip()
        a = alcance.get().strip()

        if not n or not a:
            messagebox.showwarning(
                "MOONDETEX",
                "Escribe el nombre y el alcance."
            )
            return

        guardar_proyecto(
            n,
            a,
            notas.get().strip()
        )

        mostrar("Proyectos")

    ctk.CTkButton(
        formulario,
        text="GUARDAR PROYECTO",
        fg_color=MORADO,
        hover_color="#5030BF",
        command=guardar
    ).pack(anchor="e", padx=15, pady=12)

    ctk.CTkLabel(
        principal,
        text="Mis proyectos",
        text_color=BLANCO,
        font=("Segoe UI", 17, "bold")
    ).pack(anchor="w")

    lista = ctk.CTkScrollableFrame(
        principal,
        fg_color=PANEL
    )
    lista.pack(fill="both", expand=True, pady=(5, 0))

    registros = proyectos()

    if not registros:
        ctk.CTkLabel(
            lista,
            text="Todavía no tienes proyectos.",
            text_color=GRIS
        ).pack(pady=20)

    for pid, n, a, nota, fecha in registros:

        tarjeta = crear_tarjeta(
            lista,
            n,
            f"Alcance: {a}\n{nota}\nCreado: {fecha}"
        )

        ctk.CTkButton(
            tarjeta,
            text="Eliminar",
            width=85,
            fg_color="#49304B",
            hover_color="#684062",
            command=lambda ident=pid: eliminar_proyecto(ident)
        ).pack(
            anchor="e",
            padx=12,
            pady=(0, 10)
        )


# =====================================
# PANTALLA ANALISIS
# =====================================

def pantalla_analisis():

    encabezado(
        "Análisis",
        "Comprobación educativa de cabeceras HTTP"
    )

    registros = proyectos()

    contenedor = ctk.CTkFrame(
        principal,
        fg_color=PANEL,
        corner_radius=14
    )

    contenedor.pack(fill="both", expand=True)

    if not registros:
        ctk.CTkLabel(
            contenedor,
            text="Primero crea un proyecto.",
            text_color=LAVANDA
        ).pack(pady=30)
        return

    opciones = {
        f"{pid} | {n}": pid
        for pid, n, _, _, _ in registros
    }

    ctk.CTkLabel(
        contenedor,
        text="Proyecto de laboratorio",
        text_color=BLANCO
    ).pack(anchor="w", padx=18, pady=(15, 5))

    selector = ctk.CTkOptionMenu(
        contenedor,
        values=list(opciones),
        fg_color=MORADO,
        button_color="#5030BF",
        width=320
    )

    selector.pack(anchor="w", padx=18)

    ctk.CTkLabel(
        contenedor,
        text="Respuesta HTTP de ejemplo",
        text_color=BLANCO
    ).pack(anchor="w", padx=18, pady=(16, 6))

    entrada = ctk.CTkTextbox(
        contenedor,
        height=155,
        fg_color=TARJETA,
        text_color=BLANCO
    )

    entrada.pack(fill="x", padx=18)

    ejemplo = (
        "HTTP/1.1 200 OK\n"
        "Content-Type: text/html; charset=UTF-8\n"
        "X-Content-Type-Options: nosniff\n"
        "Server: laboratorio-local\n"
    )

    entrada.insert("1.0", ejemplo)

    ctk.CTkLabel(
        contenedor,
        text=(
            "Este análisis solo revisa el texto pegado. "
            "No se conecta a sitios web. "
            "Los resultados requieren revisión humana."
        ),
        text_color=GRIS,
        wraplength=560,
        justify="left"
    ).pack(anchor="w", padx=18, pady=12)

    def ejecutar_analisis():

        texto = entrada.get("1.0", "end-1c")

        try:
            observaciones = analizar_cabeceras(texto)

        except ValueError as error:
            messagebox.showwarning(
                "Datos incompletos",
                str(error)
            )
            return

        pid = opciones[selector.get()]

        guardar_observaciones(
            pid,
            observaciones
        )

        messagebox.showinfo(
            "Análisis terminado",
            f"Observaciones: {len(observaciones)}.\n"
            "Consulta la sección Hallazgos."
        )

        mostrar("Hallazgos")

    ctk.CTkButton(
        contenedor,
        text="ANALIZAR EJEMPLO",
        fg_color=MORADO,
        hover_color="#5030BF",
        height=42,
        command=ejecutar_analisis
    ).pack(pady=5)


# =====================================
# PANTALLA HALLAZGOS
# =====================================

def pantalla_hallazgos():

    encabezado(
        "Hallazgos",
        "Observaciones del último análisis de cada proyecto"
    )

    lista = ctk.CTkScrollableFrame(
        principal,
        fg_color=PANEL
    )

    lista.pack(fill="both", expand=True)

    hallazgos = consultar_hallazgos()

    if not hallazgos:
        ctk.CTkLabel(
            lista,
            text="No hay observaciones guardadas.",
            text_color=GRIS
        ).pack(pady=25)

    for nombre, titulo, detalle, fecha in hallazgos:

        crear_tarjeta(
            lista,
            f"{titulo} | {nombre}",
            f"{detalle}\n"
            f"Revisado: {fecha}\n"
            "Estado: necesita revisión humana"
        )


# =====================================
# SISTEMA DE NAVEGACION
# =====================================

def mostrar(nombre):

    for widget in principal.winfo_children():
        widget.destroy()

    for seccion, boton in botones.items():

        color = (
            MORADO
            if seccion == nombre
            else "transparent"
        )

        boton.configure(fg_color=color)

    if nombre == "Dashboard":
        pantalla_dashboard()

    elif nombre == "Proyectos":
        pantalla_proyectos()

    elif nombre == "Análisis":
        pantalla_analisis()

    elif nombre == "Hallazgos":
        pantalla_hallazgos()

    else:
        encabezado(
            nombre,
            "Módulo previsto para una versión posterior"
        )

        panel = ctk.CTkFrame(
            principal,
            fg_color=PANEL
        )

        panel.pack(fill="both", expand=True)

        ctk.CTkLabel(
            panel,
            text="Módulo en desarrollo",
            text_color=LAVANDA,
            font=("Segoe UI", 22, "bold")
        ).pack(pady=100)


# =====================================
# CREAR BOTONES DEL MENU
# =====================================

for seccion in secciones:

    boton = ctk.CTkButton(
        menu,
        text=seccion,
        fg_color="transparent",
        hover_color="#39304F",
        text_color=BLANCO,
        anchor="w",
        height=42,
        command=lambda s=seccion: mostrar(s)
    )

    boton.pack(
        fill="x",
        padx=15,
        pady=4
    )

    botones[seccion] = boton


# =====================================
# EJECUTAR MOONDETEX
# =====================================

mostrar("Dashboard")

ventana.mainloop()

