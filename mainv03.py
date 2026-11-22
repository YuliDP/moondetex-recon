
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
from PIL import Image

# =====================================
# MOONDETEX V0.3
# COLORES OFICIALES
# =====================================

FONDO = "#12121A"
PANEL = "#1E1E2E"
MORADO = "#6C3BFF"
ROSA = "#FF4FA3"
LAVANDA = "#C9B6FF"
BLANCO = "#F5F2FF"
GRIS = "#B8B2D9"

ctk.set_appearance_mode("dark")

# =====================================
# VENTANA PRINCIPAL
# =====================================

ventana = ctk.CTk()
ventana.title("MOONDETEX V0.3")
ventana.geometry("1050x650")
ventana.minsize(900, 550)
ventana.configure(fg_color=FONDO)

ventana.grid_columnconfigure(1, weight=1)
ventana.grid_rowconfigure(0, weight=1)

# =====================================
# MENU LATERAL
# =====================================

menu = ctk.CTkFrame(
    ventana,
    width=230,
    fg_color=PANEL,
    corner_radius=0
)
menu.grid(row=0, column=0, sticky="nsew")
menu.grid_propagate(False)

# LOGO
ruta_logo = (
    Path(__file__).resolve().parent
    / "moondetex_logo.png"
)

if ruta_logo.is_file():
    try:
        imagen = Image.open(ruta_logo)
        logo = ctk.CTkImage(
            light_image=imagen,
            dark_image=imagen,
            size=(100, 100)
        )

        ctk.CTkLabel(
            menu,
            text="",
            image=logo
        ).pack(pady=(25, 5))

    except Exception:
        ctk.CTkLabel(
            menu,
            text="MOONDETEX",
            text_color=ROSA,
            font=("Segoe UI", 20, "bold")
        ).pack(pady=35)
else:
    ctk.CTkLabel(
        menu,
        text="MOONDETEX",
        text_color=ROSA,
        font=("Segoe UI", 20, "bold")
    ).pack(pady=35)

ctk.CTkLabel(
    menu,
    text="MOONDETEX",
    font=("Segoe UI", 21, "bold"),
    text_color=ROSA
).pack(pady=(5, 3))

ctk.CTkLabel(
    menu,
    text="SECURITY RESEARCH",
    font=("Segoe UI", 10),
    text_color=LAVANDA
).pack(pady=(0, 25))

# =====================================
# PANEL DE CONTENIDO
# =====================================

principal = ctk.CTkFrame(
    ventana,
    fg_color=FONDO,
    corner_radius=0
)
principal.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=25,
    pady=25
)

# TEXTOS DE CADA SECCION
secciones = {
    "Dashboard": "Resumen general del proyecto.",
    "Proyectos": "Organiza tus investigaciones y laboratorios.",
    "Análisis": "Futuro módulo de análisis de seguridad.",
    "Hallazgos": "Consulta los resultados de seguridad.",
    "Reportes": "Genera informes de tus investigaciones.",
    "Configuración": "Personaliza MOONDETEX."
}

botones = {}

# =====================================
# FUNCION PARA CAMBIAR DE PANTALLA
# =====================================

def mostrar_pantalla(nombre):

    # Eliminar contenido anterior
    for elemento in principal.winfo_children():
        elemento.destroy()

    # Actualizar boton seleccionado
    for seccion, boton in botones.items():
        if seccion == nombre:
            boton.configure(fg_color=MORADO)
        else:
            boton.configure(fg_color="transparent")

    # TITULO
    ctk.CTkLabel(
        principal,
        text=nombre,
        font=("Segoe UI", 30, "bold"),
        text_color=BLANCO
    ).pack(anchor="w", pady=(15, 5))

    # DESCRIPCION
    ctk.CTkLabel(
        principal,
        text=secciones[nombre],
        font=("Segoe UI", 13),
        text_color=GRIS
    ).pack(anchor="w", pady=(0, 25))

    # CONTENEDOR CENTRAL
    contenido = ctk.CTkFrame(
        principal,
        fg_color=PANEL,
        corner_radius=16
    )
    contenido.pack(
        fill="both",
        expand=True
    )

    if nombre == "Dashboard":

        ctk.CTkLabel(
            contenido,
            text="Bienvenida a MOONDETEX",
            font=("Segoe UI", 23, "bold"),
            text_color=ROSA
        ).pack(pady=(50, 12))

        ctk.CTkLabel(
            contenido,
            text="VULNERABILITY DETECTION & ANALYSIS",
            text_color=LAVANDA,
            font=("Segoe UI", 13)
        ).pack(pady=10)

        ctk.CTkLabel(
            contenido,
            text="Proyectos: 0   |   Hallazgos: 0",
            text_color=BLANCO,
            font=("Segoe UI", 14)
        ).pack(pady=25)

        ctk.CTkButton(
            contenido,
            text="COMPROBAR INTERFAZ",
            fg_color=MORADO,
            hover_color="#5030BF",
            text_color=BLANCO,
            height=43,
            corner_radius=12,
            command=lambda: messagebox.showinfo(
                "MOONDETEX",
                "¡El Dashboard funciona correctamente!"
            )
        ).pack(pady=10)

    else:

        ctk.CTkLabel(
            contenido,
            text=nombre,
            font=("Segoe UI", 24, "bold"),
            text_color=LAVANDA
        ).pack(pady=(100, 15))

        ctk.CTkLabel(
            contenido,
            text="Módulo en desarrollo",
            font=("Segoe UI", 14),
            text_color=GRIS
        ).pack()

# =====================================
# BOTONES DEL MENU
# =====================================

for nombre in secciones:

    boton = ctk.CTkButton(
        menu,
        text=nombre,
        height=43,
        corner_radius=10,
        fg_color="transparent",
        hover_color="#39304F",
        text_color=BLANCO,
        anchor="w",
        font=("Segoe UI", 13),
        command=lambda n=nombre: mostrar_pantalla(n)
    )

    boton.pack(
        fill="x",
        padx=15,
        pady=4
    )

    botones[nombre] = boton

# =====================================
# MOSTRAR DASHBOARD AL INICIAR
# =====================================

mostrar_pantalla("Dashboard")

# MANTENER LA APLICACION ABIERTA
ventana.mainloop()

