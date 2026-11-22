import customtkinter as ctk
from tkinter import messagebox


# COLORES DE MOONDETEX
FONDO = "#12121A"
PANEL = "#1E1E2E"
MORADO = "#6C3BFF"
LAVANDA = "#C9B6FF"
ROSA = "#FF4FA3"
BLANCO = "#F5F2FF"

# CONFIGURACION
ctk.set_appearance_mode("dark")

# CREAR VENTANA
ventana = ctk.CTk()
ventana.title("MOONDETEX V0.2")
ventana.geometry("760x500")
ventana.minsize(640, 440)
ventana.configure(fg_color=FONDO)

# FUNCION DEL BOTON
def comprobar():
    messagebox.showinfo(
        "MOONDETEX",
        "¡MOONDETEX funciona correctamente!"
    )

# PANEL PRINCIPAL
panel = ctk.CTkFrame(
    ventana,
    fg_color=PANEL,
    corner_radius=18
)

panel.pack(
    fill="both",
    expand=True,
    padx=25,
    pady=25
)

# CONTENIDO
contenido = ctk.CTkFrame(
    panel,
    fg_color="transparent"
)

contenido.pack(expand=True)




# LUNA DE MOONDETEX
from PIL import Image
from pathlib import Path
ruta = Path(__file__).resolve().parent / "moondetex_logo.png"
imagen_luna = ctk.CTkImage(
    light_image=Image.open(ruta),
    dark_image=Image.open(ruta),
    size=(125, 125)
)

ctk.CTkLabel(
    contenido,
    image=imagen_luna,
    text="",
    fg_color="transparent"
).pack(pady=(0, 10))



# TITULO
ctk.CTkLabel(
    contenido,
    text="MOONDETEX",
    font=("Segoe UI", 36, "bold"),
    text_color=ROSA
).pack(pady=10)

# FRASE
ctk.CTkLabel(
    contenido,
    text="VULNERABILITY DETECTION & ANALYSIS",
    font=("Segoe UI", 13),
    text_color=LAVANDA
).pack(pady=15)

# BOTON MORADO ELEGANTE
ctk.CTkButton(
    contenido,
    text="COMPROBAR FUNCIONAMIENTO",
    command=comprobar,
    width=300,
    height=50,
    corner_radius=14,
    fg_color="#6C3BFF",
    hover_color="#5A30D6",
    text_color="white",
    font=("Segoe UI", 13, "bold")
).pack()

# PIE DE PAGINA
ctk.CTkLabel(
    panel,
    text="MOONDETEX | SECURITY RESEARCH",
    font=("Segoe UI", 10),
    text_color=LAVANDA
).pack(side="bottom", pady=15)

# EJECUTAR PROGRAMA
ventana.mainloop()

  