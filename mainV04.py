if nombre == "Dashboard":
        total = len(obtener_proyectos())
        tarjeta = ctk.CTkFrame(principal, fg_color=PANEL, corner_radius=16)
        tarjeta.pack(fill="x", pady=16)
        escribir_titulo(tarjeta, "Proyectos guardados", 20, LAVANDA)
        ctk.CTkLabel(
            tarjeta, text=str(total),
            font=("Segoe UI", 46, "bold"), text_color=ROSA
        ).pack(pady=(0, 20))
        escribir_titulo(principal, "MOONDETEX V0.4", 18, ROSA)
        ctk.CTkLabel(
            principal, text="El módulo de análisis aún no está implementado.",
            text_color=GRIS
        ).pack(anchor="w", padx=18)

    elif nombre == "Proyectos":
        formulario = ctk.CTkFrame(principal, fg_color=PANEL, corner_radius=16)
        formulario.pack(fill="x", pady=(5, 14))
        escribir_titulo(formulario, "Nuevo proyecto", 18, ROSA)

        entrada_nombre = ctk.CTkEntry(
            formulario, placeholder_text="Nombre (ej. Laboratorio web)", height=36
        )
        entrada_nombre.pack(fill="x", padx=18, pady=5)

        entrada_alcance = ctk.CTkEntry(
            formulario, placeholder_text="Alcance autorizado (ej. mi laboratorio local)",
            height=36
        )
        entrada_alcance.pack(fill="x", padx=18, pady=5)

        entrada_notas = ctk.CTkTextbox(formulario, height=65)
        entrada_notas.pack(fill="x", padx=18, pady=5)
        ctk.CTkButton(
            formulario, text="Guardar proyecto", command=guardar_proyecto,
            fg_color=MORADO, hover_color="#5030BF", height=38
        ).pack(pady=(8, 16))

        escribir_titulo(principal, "Mis proyectos", 18, LAVANDA)
        lista = ctk.CTkScrollableFrame(principal, fg_color=PANEL)
        lista.pack(fill="both", expand=True, pady=(2, 8))
        proyectos = obtener_proyectos()

        if not proyectos:
            ctk.CTkLabel(
                lista, text="Aún no tienes proyectos guardados.", text_color=GRIS
            ).pack(pady=20)

        for identificador, titulo, alcance, notas, fecha in proyectos:
            fila = ctk.CTkFrame(lista, fg_color="#2B293B", corner_radius=10)
            fila.pack(fill="x", padx=8, pady=5)
            ctk.CTkButton(
                fila, text="Eliminar", width=75, height=30,
                fg_color="#5A3555", hover_color="#753D65",
                command=lambda pid=identificador: eliminar_proyecto(pid)
            ).pack(side="right", padx=10, pady=10)
            ctk.CTkLabel(
                fila, text=titulo, text_color=BLANCO,
                font=("Segoe UI", 14, "bold"), anchor="w"
            ).pack(anchor="w", padx=12, pady=(9, 0))
            ctk.CTkLabel(
                fila, text=f"Alcance: {alcance}  |  Fecha: {fecha}",
                text_color=GRIS, anchor="w", wraplength=480, justify="left"
            ).pack(anchor="w", padx=12, pady=(0, 9))
            if notas:
                ctk.CTkLabel(
                    fila, text=f"Notas: {notas}", text_color=LAVANDA,
                    anchor="w", wraplength=480, justify="left"
                ).pack(anchor="w", padx=12, pady=(0, 8))

    else:
        tarjeta = ctk.CTkFrame(principal, fg_color=PANEL, corner_radius=16)
        tarjeta.pack(fill="both", expand=True, pady=16)
        ctk.CTkLabel(
            tarjeta, text="Módulo en desarrollo",
            font=("Segoe UI", 22, "bold"), text_color=LAVANDA
        ).pack(expand=True)


iniciar_base_datos()
ctk.set_appearance_mode("dark")
ventana = ctk.CTk()
ventana.title("MOONDETEX V0.4")
ventana.geometry("1100x740")
ventana.minsize(900, 640)
ventana.configure(fg_color=FONDO)
ventana.grid_columnconfigure(1, weight=1)
ventana.grid_rowconfigure(0, weight=1)

menu = ctk.CTkFrame(ventana, width=230, fg_color=PANEL, corner_radius=0)
menu.grid(row=0, column=0, sticky="nsew")
menu.grid_propagate(False)

logo_archivo = CARPETA / "moondetex_logo.png"
if logo_archivo.is_file():
    try:
        with Image.open(logo_archivo) as img:
            imagen = img.copy()
        logo = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(110, 110))
        ctk.CTkLabel(menu, text="", image=logo).pack(pady=(20, 5))
    except (OSError, ValueError):
        pass

ctk.CTkLabel(
    menu, text="MOONDETEX", font=("Segoe UI", 23, "bold"), text_color=ROSA
).pack(pady=(15, 3))
ctk.CTkLabel(
    menu, text="SECURITY RESEARCH", font=("Segoe UI", 10), text_color=LAVANDA
).pack(pady=(0, 24))

principal = ctk.CTkFrame(ventana, fg_color=FONDO, corner_radius=0)
principal.grid(row=0, column=1, sticky="nsew", padx=25, pady=22)

secciones = [
    "Dashboard", "Proyectos", "Análisis",
    "Hallazgos", "Reportes", "Configuración"
]
botones = {}
for nombre in secciones:
    boton = ctk.CTkButton(
        menu, text=nombre, height=43, anchor="w",
        fg_color="transparent", hover_color="#39304F",
        text_color=BLANCO, corner_radius=10,
        command=lambda seccion=nombre: mostrar_pantalla(seccion)
    )
    boton.pack(fill="x", padx=15, pady=4)
    botones[nombre] = boton
