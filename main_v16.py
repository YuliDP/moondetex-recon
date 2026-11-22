import json
import re
import sqlite3
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

# ==========================================
# MOONDETEX V0.6
# ==========================================

CARPETA = Path(__file__).resolve().parent
DB = CARPETA / "moondetex.db"
LOGO = CARPETA / "moondetex_logo.png"

FONDO = "#12121A"
PANEL = "#1E1E2E"
TARJETA = "#28263A"
MORADO = "#6C3BFF"
ROSA = "#FF4FA3"
LAVANDA = "#C9B6FF"
BLANCO = "#F5F2FF"
GRIS = "#B8B2D9"

ctk.set_appearance_mode("dark")


# ==========================================
# BASE DE DATOS
# ==========================================

def conectar():
    conexion = sqlite3.connect(DB)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def iniciar_bd():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS proyectos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                alcance TEXT NOT NULL,
                notas TEXT NOT NULL DEFAULT '',
                fecha TEXT NOT NULL DEFAULT
                    (datetime('now', 'localtime'))
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
                    (datetime('now', 'localtime')),
                FOREIGN KEY(proyecto_id)
                    REFERENCES proyectos(id)
                    ON DELETE CASCADE,
                UNIQUE(proyecto_id, clave)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS verificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER NOT NULL,
                resultado_json TEXT NOT NULL,
                fecha TEXT NOT NULL DEFAULT
                    (datetime('now', 'localtime')),
                FOREIGN KEY(proyecto_id)
                    REFERENCES proyectos(id)
                    ON DELETE CASCADE
            )
        """)


def obtener_proyectos():
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
        "¿Eliminar el proyecto y todos sus registros?"
    )

    if not confirmar:
        return

    with conectar() as con:
        con.execute(
            "DELETE FROM proyectos WHERE id = ?",
            (pid,)
        )

    mostrar("Proyectos")


def obtener_hallazgos():
    with conectar() as con:
        return con.execute("""
            SELECT p.nombre, h.titulo, h.detalle, h.fecha
            FROM hallazgos h
            JOIN proyectos p ON p.id = h.proyecto_id
            ORDER BY h.id DESC
        """).fetchall()


# ==========================================
# MOONDETEX V0.13
# GUARDAR ANALISIS CON HISTORIAL
# ==========================================

def guardar_hallazgos(pid, filas):

    with conectar() as con:

        # Obtener hallazgos anteriores
        antiguos = con.execute("""
            SELECT clave, titulo, detalle, estado
            FROM hallazgos
            WHERE proyecto_id = ?
        """, (pid,)).fetchall()

        # Conservar estados de hallazgos iguales
        estados = {
            (clave, detalle): estado
            for clave, titulo, detalle, estado in antiguos
        }

        # Comprobar si ya existe historial
        existe_historial = con.execute("""
            SELECT 1
            FROM historial_analisis
            WHERE proyecto_id = ?
            LIMIT 1
        """, (pid,)).fetchone()

        # Guardar los hallazgos antiguos
        # la primera vez que usamos el historial
        if antiguos and not existe_historial:

            cursor = con.execute("""
                INSERT INTO historial_analisis
                (proyecto_id, total_observaciones)
                VALUES (?, ?)
            """, (pid, len(antiguos)))

            id_anterior = cursor.lastrowid

            con.executemany("""
                INSERT INTO historial_observaciones
                (analisis_id, clave, titulo, detalle, estado)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (id_anterior, clave, titulo, detalle, estado)
                for clave, titulo, detalle, estado in antiguos
            ])

        # Registrar el nuevo analisis
        cursor = con.execute("""
            INSERT INTO historial_analisis
            (proyecto_id, total_observaciones)
            VALUES (?, ?)
        """, (pid, len(filas)))

        id_nuevo = cursor.lastrowid

        # Guardar una copia historica
        con.executemany("""
            INSERT INTO historial_observaciones
            (analisis_id, clave, titulo, detalle, estado)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (
                id_nuevo,
                clave,
                titulo,
                detalle,
                estados.get((clave, detalle), "Pendiente")
            )
            for clave, titulo, detalle in filas
        ])

        # Actualizar los hallazgos actuales
        con.execute(
            "DELETE FROM hallazgos WHERE proyecto_id = ?",
            (pid,)
        )

        con.executemany("""
            INSERT INTO hallazgos
            (proyecto_id, clave, titulo, detalle, estado)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (
                pid,
                clave,
                titulo,
                detalle,
                estados.get((clave, detalle), "Pendiente")
            )
            for clave, titulo, detalle in filas
        ])


   


def guardar_verificacion(pid, resultados):
    with conectar() as con:
        con.execute(
            "INSERT INTO verificaciones "
            "(proyecto_id, resultado_json) VALUES (?, ?)",
            (
                pid,
                json.dumps(
                    resultados,
                    ensure_ascii=False
                )
            )
        )


def obtener_verificaciones():
    with conectar() as con:
        return con.execute("""
            SELECT p.nombre, v.resultado_json, v.fecha
            FROM verificaciones v
            JOIN proyectos p ON p.id = v.proyecto_id
            ORDER BY v.id DESC
        """).fetchall()


# ==========================================
# MOTOR DE ANALISIS HTTP
# ==========================================

REGLAS = [
    ("csp", "Política CSP"),
    ("marcos", "Protección de marcos"),
    ("nosniff", "Control de tipos MIME")
]


def extraer_cabeceras(texto):
    lineas = texto.replace(
        "\r\n", "\n"
    ).split("\n")

    patron = r"^HTTP/(?:1\.[01]|[23])\s+\d{3}(?:\s|$)"

    if not lineas or not re.match(
        patron,
        lineas[0].strip(),
        re.IGNORECASE
    ):
        raise ValueError(
            "El texto debe empezar con "
            "'HTTP/1.1 200 OK' o similar."
        )

    cabeceras = {}

    for linea in lineas[1:]:
        if not linea.strip():
            break

        if ":" not in linea:
            raise ValueError(
                "Cabecera incorrecta: " + linea[:70]
            )

        nombre, valor = linea.split(":", 1)
        nombre = nombre.strip().lower()

        if not re.fullmatch(
            r"[a-z0-9!#$%&'*+.^_`|~-]+",
            nombre
        ):
            raise ValueError(
                "Nombre de cabecera no válido."
            )

        cabeceras[nombre] = valor.strip()

    if "content-type" not in cabeceras:
        raise ValueError(
            "Falta la cabecera Content-Type."
        )

    return cabeceras


def evaluar(texto):
    cab = extraer_cabeceras(texto)

    tipo = cab["content-type"].lower()

    if "text/html" not in tipo:
        return {
            clave: None
            for clave, _ in REGLAS
        }

    csp = cab.get(
        "content-security-policy", ""
    )

    directivas = [
        x.strip().lower()
        for x in csp.split(";")
    ]

    frame_ancestors = any(
        x == "frame-ancestors"
        or x.startswith("frame-ancestors ")
        for x in directivas
    )

    xframe = cab.get(
        "x-frame-options", ""
    ).upper()

    marcos = (
        frame_ancestors
        or xframe in ("DENY", "SAMEORIGIN")
    )

    nosniff = cab.get(
        "x-content-type-options", ""
    ).lower() == "nosniff"

    return {
        "csp": bool(csp.strip()),
        "marcos": marcos,
        "nosniff": nosniff
    }


def analizar(texto):
    estados = evaluar(texto)

    detalles = {
        "csp":
            "No se observó Content-Security-Policy.",
        "marcos":
            "No se observó una restricción válida "
            "de marcos en las cabeceras.",
        "nosniff":
            "No se observó "
            "X-Content-Type-Options: nosniff."
    }

    resultado = []

    for clave, titulo in REGLAS:
        if estados[clave] is False:
            resultado.append((
                clave,
                titulo + " por revisar",
                detalles[clave]
            ))

    return resultado


# ==========================================
# MOTOR DE COMPARACION
# ==========================================

def comparar(antes, despues):
    estado_antes = evaluar(antes)
    estado_despues = evaluar(despues)

    resultados = []

    for clave, titulo in REGLAS:
        a = estado_antes[clave]
        d = estado_despues[clave]

        if a is None or d is None:
            estado = "No comparable"

        elif not a and d:
            estado = "Mejora observada"

        elif a and not d:
            estado = "Posible regresión"

        elif not a and not d:
            estado = "Pendiente de revisión"

        else:
            estado = "Presente en ambas muestras"

        resultados.append({
            "control": titulo,
            "estado": estado
        })

    return resultados

from motor_http import analizar, comparar
from gestor_evidencias import registrar_evidencia

# ==========================================
# EJEMPLOS DE LABORATORIO
# ==========================================


EJEMPLO_ANTES = (
    "HTTP/1.1 200 OK\n"
    "Content-Type: text/html; charset=UTF-8\n"
    "Server: laboratorio-local\n"
)

EJEMPLO_DESPUES = (
    "HTTP/1.1 200 OK\n"
    "Content-Type: text/html; charset=UTF-8\n"
    "Content-Security-Policy: "
    "default-src 'self'; frame-ancestors 'none'\n"
    "X-Content-Type-Options: nosniff\n"
)


# ==========================================
# PREPARAR BASE DE DATOS
# ==========================================

iniciar_bd()


# ==========================================
# VENTANA PRINCIPAL
# ==========================================

ventana = ctk.CTk()

ventana.title("MOONDETEX V0.15")
ventana.geometry("1180x780")
ventana.minsize(940, 650)
ventana.configure(fg_color=FONDO)

ventana.grid_columnconfigure(1, weight=1)
ventana.grid_rowconfigure(0, weight=1)


# ==========================================
# MENU LATERAL
# ==========================================

menu = ctk.CTkFrame(
    ventana,
    width=220,
    fg_color=PANEL,
    corner_radius=0
)

menu.grid(
    row=0,
    column=0,
    sticky="nsew"
)

menu.grid_propagate(False)


# LOGO
if LOGO.is_file():
    try:
        with Image.open(LOGO) as archivo:
            imagen = archivo.convert("RGBA")

        imagen_logo = ctk.CTkImage(
            light_image=imagen,
            dark_image=imagen,
            size=(105, 105)
        )

        ctk.CTkLabel(
            menu,
            image=imagen_logo,
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
    text_color=ROSA,
    font=("Segoe UI", 21, "bold")
).pack(pady=3)

ctk.CTkLabel(
    menu,
    text="SECURITY RESEARCH",
    text_color=LAVANDA,
    font=("Segoe UI", 10)
).pack(pady=(0, 22))


# PANEL PRINCIPAL
principal = ctk.CTkFrame(
    ventana,
    fg_color="transparent"
)

principal.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=24,
    pady=22
)


SECCIONES = [
    "Dashboard",
    "Proyectos",
    "Análisis",
    "Hallazgos",
    "Verificación",
    "Historial",
    "Reportes",
    "Configuración"
]


   

botones = {}

# ==========================================
# COMPONENTES DE LA INTERFAZ
# ==========================================

def encabezado(titulo, subtitulo):
    ctk.CTkLabel(
        principal,
        text=titulo,
        text_color=BLANCO,
        font=("Segoe UI", 29, "bold")
    ).pack(anchor="w", pady=(3, 3))

    ctk.CTkLabel(
        principal,
        text=subtitulo,
        text_color=GRIS,
        font=("Segoe UI", 12)
    ).pack(anchor="w", pady=(0, 18))


def panel_scroll():
    marco = ctk.CTkScrollableFrame(
        principal,
        fg_color=PANEL,
        corner_radius=14
    )

    marco.pack(
        fill="both",
        expand=True
    )

    return marco


def tarjeta(contenedor, titulo, detalle):
    marco = ctk.CTkFrame(
        contenedor,
        fg_color=TARJETA,
        corner_radius=10
    )

    marco.pack(
        fill="x",
        padx=10,
        pady=6
    )

    ctk.CTkLabel(
        marco,
        text=titulo,
        text_color=LAVANDA,
        font=("Segoe UI", 15, "bold"),
        anchor="w"
    ).pack(fill="x", padx=14, pady=(10, 3))

    ctk.CTkLabel(
        marco,
        text=detalle,
        text_color=GRIS,
        justify="left",
        anchor="w",
        wraplength=650
    ).pack(fill="x", padx=14, pady=(0, 10))

    return marco


def selector_proyectos(contenedor):
    registros = obtener_proyectos()

    if not registros:
        ctk.CTkLabel(
            contenedor,
            text="Primero crea un proyecto.",
            text_color=LAVANDA
        ).pack(pady=30)

        return None, None

    opciones = {
        f"{pid} | {nombre}": pid
        for pid, nombre, *_ in registros
    }

    selector = ctk.CTkOptionMenu(
        contenedor,
        values=list(opciones),
        fg_color=MORADO,
        button_color="#5030BF",
        width=350
    )

    selector.pack(
        anchor="w",
        padx=18,
        pady=(12, 6)
    )

    return selector, opciones


# ==========================================
# DASHBOARD
# ==========================================

def pantalla_dashboard():
    encabezado(
        "Dashboard",
        "Resumen general de MOONDETEX"
    )

    p = ctk.CTkFrame(
        principal,
        fg_color=PANEL,
        corner_radius=15
    )

    p.pack(fill="both", expand=True)

    ctk.CTkLabel(
        p,
        text="Bienvenida a MOONDETEX",
        text_color=ROSA,
        font=("Segoe UI", 25, "bold")
    ).pack(pady=(65, 14))

    ctk.CTkLabel(
        p,
        text="VULNERABILITY DETECTION & ANALYSIS",
        text_color=LAVANDA
    ).pack(pady=5)

    total_proyectos = len(obtener_proyectos())
    total_hallazgos = len(obtener_hallazgos())
    total_verificaciones = len(obtener_verificaciones())

    ctk.CTkLabel(
        p,
        text=(
            f"Proyectos: {total_proyectos}   |   "
            f"Observaciones: {total_hallazgos}   |   "
            f"Comparaciones: {total_verificaciones}"
        ),
        text_color=BLANCO,
        font=("Segoe UI", 15)
    ).pack(pady=30)

    ctk.CTkButton(
        p,
        text="ABRIR VERIFICACIÓN",
        fg_color=MORADO,
        hover_color="#5030BF",
        height=42,
        command=lambda: mostrar("Verificación")
    ).pack(pady=10)

    ctk.CTkLabel(
        p,
        text="Análisis local educativo de seguridad HTTP",
        text_color=GRIS
    ).pack(pady=15)


# ==========================================
# PROYECTOS
# ==========================================

def pantalla_proyectos():
    encabezado(
        "Proyectos",
        "Organiza laboratorios propios o autorizados"
    )

    f = ctk.CTkFrame(
        principal,
        fg_color=PANEL,
        corner_radius=14
    )

    f.pack(fill="x", pady=(0, 12))

    ctk.CTkLabel(
        f,
        text="Crear proyecto",
        text_color=ROSA,
        font=("Segoe UI", 17, "bold")
    ).pack(anchor="w", padx=15, pady=9)

    nombre = ctk.CTkEntry(
        f,
        placeholder_text="Nombre del proyecto",
        fg_color=TARJETA
    )

    alcance = ctk.CTkEntry(
        f,
        placeholder_text="Alcance autorizado o laboratorio",
        fg_color=TARJETA
    )

    notas = ctk.CTkEntry(
        f,
        placeholder_text="Notas opcionales",
        fg_color=TARJETA
    )

    for campo in (nombre, alcance, notas):
        campo.pack(fill="x", padx=15, pady=4)

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
        f,
        text="GUARDAR PROYECTO",
        command=guardar,
        fg_color=MORADO,
        hover_color="#5030BF"
    ).pack(anchor="e", padx=15, pady=12)

    lista = panel_scroll()

    registros = obtener_proyectos()

    if not registros:
        ctk.CTkLabel(
            lista,
            text="Todavía no hay proyectos.",
            text_color=GRIS
        ).pack(pady=25)

    for pid, n, a, nota, fecha in registros:
        t = tarjeta(
            lista,
            n,
            f"Alcance: {a}\n{nota}\nCreado: {fecha}"
        )

        ctk.CTkButton(
            t,
            text="Eliminar",
            width=90,
            fg_color="#49304B",
            hover_color="#684062",
            command=lambda ident=pid: eliminar_proyecto(ident)
        ).pack(
            anchor="e",
            padx=14,
            pady=(0, 10)
        )


# ==========================================
# ANALISIS HTTP
# ==========================================

def pantalla_analisis():
    encabezado(
        "Análisis",
        "Inspección local de cabeceras HTTP"
    )

    p = panel_scroll()

    selector, opciones = selector_proyectos(p)

    if selector is None:
        return

    ctk.CTkLabel(
        p,
        text="Respuesta HTTP de laboratorio:",
        text_color=BLANCO
    ).pack(anchor="w", padx=18, pady=(8, 6))

    caja = ctk.CTkTextbox(
        p,
        height=185,
        fg_color=TARJETA
    )

    caja.pack(fill="x", padx=18)

    caja.insert("1.0", EJEMPLO_ANTES)

    ctk.CTkLabel(
        p,
        text=(
            "Este módulo revisa texto local. "
            "No confirma vulnerabilidades."
        ),
        text_color=GRIS
    ).pack(anchor="w", padx=18, pady=12)

    def ejecutar():
        try:
            filas = analizar(
                caja.get("1.0", "end-1c")
            )

        except ValueError as error:
            messagebox.showwarning(
                "Ejemplo incorrecto",
                str(error)
            )
            return

        pid = opciones[selector.get()]

        guardar_hallazgos(pid, filas)
        registrar_evidencia(
            pid,
            caja.get("1.0", "end-1c")
        )
        

        messagebox.showinfo(
            "MOONDETEX",
            f"Observaciones guardadas: {len(filas)}"
        )

        mostrar("Hallazgos")

    ctk.CTkButton(
        p,
        text="ANALIZAR TEXTO",
        fg_color=MORADO,
        hover_color="#5030BF",
        height=42,
        command=ejecutar
    ).pack(pady=14)


# ==========================================
# HALLAZGOS
# ==========================================


# ==========================================
# MOONDETEX - CLASE 12
# HALLAZGOS CON ESTADOS EDITABLES
# ==========================================

def pantalla_hallazgos():

    encabezado(
        "Hallazgos",
        "Observaciones, recomendaciones y estados"
    )

    p = panel_scroll()

    # CONSULTAR LOS HALLAZGOS Y SUS ESTADOS
    conexion = conectar()

    try:
        filas = conexion.execute("""
            SELECT
                h.id,
                p.nombre,
                h.titulo,
                h.detalle,
                h.fecha,
                h.estado
            FROM hallazgos h
            JOIN proyectos p
                ON p.id = h.proyecto_id
            ORDER BY h.id DESC
        """).fetchall()

    finally:
        conexion.close()

    if not filas:
        ctk.CTkLabel(
            p,
            text="No hay observaciones guardadas.",
            text_color=GRIS
        ).pack(pady=25)
        return

    # FUNCION PARA GUARDAR EL ESTADO
    def cambiar_estado(identificador, nuevo_estado):

        estados_validos = [
            "Pendiente",
            "Revisado",
            "Descartado"
        ]

        if nuevo_estado not in estados_validos:
            return

        conexion = conectar()

        try:
            conexion.execute(
                "UPDATE hallazgos "
                "SET estado = ? WHERE id = ?",
                (nuevo_estado, identificador)
            )
            conexion.commit()

        finally:
            conexion.close()

        messagebox.showinfo(
            "MOONDETEX",
            "Estado guardado correctamente."
        )

        mostrar("Hallazgos")

    # MOSTRAR LOS HALLAZGOS
    for ident, proyecto, titulo, detalle, fecha, estado in filas:

        texto = (titulo + " " + detalle).lower()

        if "fuente comodín (*)" in texto:

            prioridad = "MEDIA"
            motivo = (
                "La politica CSP permite "
                "un conjunto amplio de origenes."
            )
            recomendacion = (
                "Revisar los recursos necesarios "
                "y limitar los origenes permitidos."
            )

        elif "content-security-policy" in texto:

            prioridad = "INFORMATIVA"
            motivo = "No se observo una politica CSP."
            recomendacion = (
                "Evaluar si la aplicacion necesita "
                "una politica CSP adecuada."
            )

        elif "nosniff" in texto:

            prioridad = "INFORMATIVA"
            motivo = "No se observo el control MIME."
            recomendacion = (
                "Revisar X-Content-Type-Options: "
                "nosniff."
            )

        elif "marcos" in texto or "frame-ancestors" in texto:

            prioridad = "INFORMATIVA"
            motivo = (
                "No se observo una restriccion "
                "de marcos reconocida."
            )
            recomendacion = (
                "Revisar frame-ancestors o "
                "X-Frame-Options."
            )

        else:

            prioridad = "PENDIENTE"
            motivo = "Requiere revision adicional."
            recomendacion = (
                "Recopilar mas informacion "
                "antes de sacar conclusiones."
            )

        informacion = (
            f"Prioridad sugerida: {prioridad}\n"
            f"Motivo: {motivo}\n\n"
            f"OBSERVACION REGISTRADA:\n"
            f"{detalle}\n\n"
            f"RECOMENDACION:\n"
            f"{recomendacion}\n\n"
            f"Proyecto: {proyecto}\n"
            f"Fecha: {fecha}\n"
            f"Estado actual: {estado}\n"
            f"Confianza: sin validar manualmente"
        )

        # CREAR TARJETA
        marco = tarjeta(
            p,
            titulo,
            informacion
        )

        # SELECTOR DE ESTADO
        ctk.CTkLabel(
            marco,
            text="Cambiar estado:",
            text_color=LAVANDA
        ).pack(
            anchor="w",
            padx=14,
            pady=(5, 4)
        )

        selector = ctk.CTkOptionMenu(
            marco,
            values=[
                "Pendiente",
                "Revisado",
                "Descartado"
            ],
            fg_color=MORADO,
            button_color="#5030BF",
            button_hover_color="#6945D5",
            width=180
        )

        selector.set(estado)

        selector.pack(
            anchor="w",
            padx=14,
            pady=(0, 8)
        )

        # BOTON GUARDAR
        ctk.CTkButton(
            marco,
            text="GUARDAR ESTADO",
            fg_color=MORADO,
            hover_color="#5030BF",
            width=180,
            height=35,
            command=lambda i=ident, s=selector: cambiar_estado(
                i, s.get()
            )
        ).pack(
            anchor="w",
            padx=14,
            pady=(0, 15)
        )


    


# ==========================================
# VERIFICACION DE CONFIGURACIONES
# ==========================================

def pantalla_verificacion():
    encabezado(
        "Verificación",
        "Compara configuraciones antes y después"
    )

    p = panel_scroll()

    selector, opciones = selector_proyectos(p)

    if selector is None:
        return

    ctk.CTkLabel(
        p,
        text=(
            "Compara dos respuestas HTTP de laboratorio. "
            "No se realizan conexiones a Internet."
        ),
        text_color=GRIS,
        wraplength=650
    ).pack(anchor="w", padx=18, pady=(4, 10))

    columnas = ctk.CTkFrame(
        p,
        fg_color="transparent"
    )

    columnas.pack(fill="x", padx=13)

    columnas.grid_columnconfigure(0, weight=1)
    columnas.grid_columnconfigure(1, weight=1)

    cajas = []

    for columna, titulo, ejemplo in (
        (0, "ANTES", EJEMPLO_ANTES),
        (1, "DESPUÉS", EJEMPLO_DESPUES)
    ):
        marco = ctk.CTkFrame(
            columnas,
            fg_color="transparent"
        )

        marco.grid(
            row=0,
            column=columna,
            sticky="nsew",
            padx=5
        )

        ctk.CTkLabel(
            marco,
            text=titulo,
            text_color=LAVANDA,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        caja = ctk.CTkTextbox(
            marco,
            height=180,
            fg_color=TARJETA
        )

        caja.pack(fill="both", expand=True)
        caja.insert("1.0", ejemplo)

        cajas.append(caja)

    def ejecutar_comparacion():
        antes = cajas[0].get("1.0", "end-1c")
        despues = cajas[1].get("1.0", "end-1c")

        try:
            resultados = comparar(
                antes,
                despues
            )

        except ValueError as error:
            messagebox.showwarning(
                "Datos incorrectos",
                str(error)
            )
            return

        pid = opciones[selector.get()]

        guardar_verificacion(
            pid,
            resultados
        )

        mostrar("Verificación")

        messagebox.showinfo(
            "MOONDETEX",
            "Comparación guardada correctamente. "
            "Puedes revisar el historial."
        )

    ctk.CTkButton(
        p,
        text="COMPARAR Y GUARDAR",
        fg_color=MORADO,
        hover_color="#5030BF",
        height=42,
        command=ejecutar_comparacion
    ).pack(pady=16)

    ctk.CTkLabel(
        p,
        text="Historial de comparaciones",
        font=("Segoe UI", 17, "bold"),
        text_color=ROSA
    ).pack(anchor="w", padx=18, pady=(8, 7))

    registros = obtener_verificaciones()

    if not registros:
        ctk.CTkLabel(
            p,
            text="Todavía no hay comparaciones.",
            text_color=GRIS
        ).pack(pady=12)

    for proyecto, datos_json, fecha in registros:
        filas = json.loads(datos_json)

        detalle = "\n".join(
            f"• {fila['control']}: {fila['estado']}"
            for fila in filas
        )

        tarjeta(
            p,
            f"{proyecto} | {fecha}",
            detalle
        )

    ctk.CTkLabel(
        p,
        text=(
            "Las mejoras observadas no demuestran "
            "por sí solas que una vulnerabilidad "
            "haya sido confirmada o corregida."
        ),
        text_color=GRIS,
        wraplength=650
    ).pack(anchor="w", padx=18, pady=12)



# 
#
# ==========================================
# MOONDETEX V0.15
# COMPARADOR AVANZADO DE HISTORIAL
# ==========================================

def pantalla_historial():

    encabezado(
        "Historial",
        "Elige dos análisis del mismo proyecto para comparar"
    )

    p = panel_scroll()

    # CONSULTAR LA BASE DE DATOS
    with conectar() as con:

        registros = con.execute("""
            SELECT h.id, h.proyecto_id, p.nombre,
                   h.fecha, h.total_observaciones
            FROM historial_analisis h
            JOIN proyectos p ON p.id = h.proyecto_id
            ORDER BY h.id DESC
        """).fetchall()

        observaciones = con.execute("""
            SELECT analisis_id, clave, titulo, detalle, estado
            FROM historial_observaciones
            ORDER BY id
        """).fetchall()

    if not registros:
        ctk.CTkLabel(
            p,
            text="Todavía no hay análisis guardados.",
            text_color=GRIS
        ).pack(pady=25)
        return

    # ORGANIZAR OBSERVACIONES
    por_analisis = {}

    for aid, clave, titulo, detalle, estado in observaciones:
        por_analisis.setdefault(aid, {})[clave] = (
            titulo, detalle, estado
        )

    # ORGANIZAR ANALISIS POR PROYECTO
    por_proyecto = {}
    proyectos = {}

    for aid, pid, nombre, fecha, total in registros:

        proyectos[f"{pid} | {nombre}"] = pid

        por_proyecto.setdefault(pid, []).append(
            (aid, fecha)
        )

    # TITULO
    ctk.CTkLabel(
        p,
        text="Comparador de análisis",
        text_color=ROSA,
        font=("Segoe UI", 18, "bold")
    ).pack(anchor="w", padx=12, pady=(12, 8))

    # SELECCIONAR PROYECTO
    ctk.CTkLabel(
        p,
        text="Proyecto:",
        text_color=LAVANDA
    ).pack(anchor="w", padx=12)

    selector_proyecto = ctk.CTkOptionMenu(
        p,
        values=list(proyectos),
        fg_color=MORADO,
        button_color="#5030BF",
        width=350
    )

    selector_proyecto.pack(
        anchor="w",
        padx=12,
        pady=(4, 12)
    )

    # SELECCIONAR ANALISIS ANTERIOR
    ctk.CTkLabel(
        p,
        text="Análisis anterior:",
        text_color=LAVANDA
    ).pack(anchor="w", padx=12)

    selector_anterior = ctk.CTkOptionMenu(
        p,
        values=["Sin datos"],
        fg_color=MORADO,
        button_color="#5030BF",
        width=350
    )

    selector_anterior.pack(
        anchor="w",
        padx=12,
        pady=(4, 12)
    )

    # SELECCIONAR ANALISIS RECIENTE
    ctk.CTkLabel(
        p,
        text="Análisis más reciente:",
        text_color=LAVANDA
    ).pack(anchor="w", padx=12)

    selector_reciente = ctk.CTkOptionMenu(
        p,
        values=["Sin datos"],
        fg_color=MORADO,
        button_color="#5030BF",
        width=350
    )

    selector_reciente.pack(
        anchor="w",
        padx=12,
        pady=(4, 12)
    )

    # CONTENEDOR DE RESULTADOS
    resultados = ctk.CTkFrame(
        p,
        fg_color="transparent"
    )

    mapa_opciones = {}

    # ACTUALIZAR ANALISIS DISPONIBLES
    def actualizar_proyecto(nombre_proyecto):

        pid = proyectos[nombre_proyecto]

        lista = por_proyecto[pid]

        mapa_opciones.clear()

        mapa_opciones.update({
            f"#{aid} | {fecha}": aid
            for aid, fecha in lista
        })

        opciones = list(mapa_opciones)

        selector_anterior.configure(values=opciones)
        selector_reciente.configure(values=opciones)

        if len(opciones) > 1:
            selector_anterior.set(opciones[1])
        else:
            selector_anterior.set(opciones[0])

        selector_reciente.set(opciones[0])

        for elemento in resultados.winfo_children():
            elemento.destroy()

        if len(opciones) < 2:
            tarjeta(
                resultados,
                "Sin comparación",
                "Este proyecto necesita al menos dos análisis."
            )

    selector_proyecto.configure(
        command=actualizar_proyecto
    )

    # =====================================
    # COMPARAR LOS ANALISIS SELECCIONADOS
    # =====================================

    def comparar_seleccion():

        for elemento in resultados.winfo_children():
            elemento.destroy()

        anterior_id = mapa_opciones[
            selector_anterior.get()
        ]

        reciente_id = mapa_opciones[
            selector_reciente.get()
        ]

        if anterior_id >= reciente_id:

            tarjeta(
                resultados,
                "Selección incorrecta",
                "Elige dos análisis distintos: "
                "uno anterior y otro posterior."
            )

            return

        antes = por_analisis.get(
            anterior_id, {}
        )

        despues = por_analisis.get(
            reciente_id, {}
        )

        claves_antes = set(antes)
        claves_despues = set(despues)

        nuevas = claves_despues - claves_antes

        desaparecidas = claves_antes - claves_despues

        comunes = claves_antes & claves_despues

        cambiadas = {
            clave for clave in comunes
            if antes[clave][:2] != despues[clave][:2]
        }

        persistentes = comunes - cambiadas

        # RESUMEN
        resumen = (
            f"Anterior: #{anterior_id} | "
            f"Reciente: #{reciente_id}\n"
            f"Nuevas: {len(nuevas)}\n"
            f"Persistentes sin cambios: {len(persistentes)}\n"
            f"Persistentes con cambios: {len(cambiadas)}\n"
            f"Ya no observadas: {len(desaparecidas)}\n\n"
            "Las observaciones ausentes no necesariamente "
            "están corregidas."
        )

        tarjeta(
            resultados,
            "Resultado de la comparación",
            resumen
        )

        # DETALLES DE CAMBIOS
        for etiqueta, claves, datos in (
            ("Nueva", nuevas, despues),
            ("Con cambios", cambiadas, despues),
            ("Ya no observada", desaparecidas, antes)
        ):

            for clave in sorted(claves):

                titulo, detalle, _ = datos[clave]

                tarjeta(
                    resultados,
                    f"{etiqueta}: {titulo}",
                    detalle
                )

    # BOTON COMPARAR
    ctk.CTkButton(
        p,
        text="COMPARAR ANÁLISIS",
        command=comparar_seleccion,
        fg_color=MORADO,
        hover_color="#5030BF",
        height=40
    ).pack(
        anchor="w",
        padx=12,
        pady=(2, 15)
    )

    resultados.pack(
        fill="x",
        padx=2,
        pady=(0, 12)
    )

    # CARGAR PROYECTO INICIAL
    actualizar_proyecto(
        next(iter(proyectos))
    )

    # =====================================
    # HISTORIAL COMPLETO
    # =====================================

    ctk.CTkLabel(
        p,
        text="Todos los análisis guardados",
        text_color=ROSA,
        font=("Segoe UI", 18, "bold")
    ).pack(
        anchor="w",
        padx=12,
        pady=(12, 5)
    )

    for aid, pid, nombre, fecha, total in registros:

        datos = por_analisis.get(aid, {})

        if datos:

            contenido = "\n\n".join(
                f"{titulo}\n{detalle}\n"
                f"Estado al guardar: {estado}"
                for titulo, detalle, estado in datos.values()
            )
 
        else:
            contenido = "Sin observaciones registradas."

        
        
        # Crear la tarjeta del análisis
        marco = tarjeta(
            p,
            f"Análisis #{aid} | {nombre}",
            f"Fecha: {fecha}\n"
            f"Observaciones: {total}\n\n"
            + contenido
        )

        # Buscar la evidencia vinculada
        with conectar() as con:
            evidencia = con.execute("""
                SELECT e.contenido, e.huella_sha256
                FROM historial_evidencias he
                JOIN evidencias_http e
                    ON e.id = he.evidencia_id
                WHERE he.analisis_id = ?
            """, (aid,)).fetchone()

        if evidencia:

            texto_original, huella = evidencia

            # Abrir ventana de evidencia
            def abrir_evidencia(
                texto=texto_original,
                sha=huella,
                numero=aid
            ):

                ventana_evidencia = ctk.CTkToplevel(
                    ventana
                )

                ventana_evidencia.title(
                    f"MOONDETEX | Evidencia #{numero}"
                )

                ventana_evidencia.geometry("750x500")
                ventana_evidencia.configure(
                    fg_color=FONDO
                )

                ctk.CTkLabel(
                    ventana_evidencia,
                    text=f"Evidencia del análisis #{numero}",
                    font=("Segoe UI", 22, "bold"),
                    text_color=ROSA
                ).pack(pady=(20, 10))

                ctk.CTkLabel(
                    ventana_evidencia,
                    text=f"SHA-256:\n{sha}",
                    text_color=LAVANDA,
                    wraplength=680
                ).pack(padx=20, pady=10)

                caja = ctk.CTkTextbox(
                    ventana_evidencia,
                    fg_color=PANEL,
                    text_color=BLANCO,
                    font=("Consolas", 12)
                )

                caja.pack(
                    fill="both",
                    expand=True,
                    padx=20,
                    pady=(10, 20)
                )

                caja.insert("1.0", texto)
                caja.configure(state="disabled")

                ventana_evidencia.lift()

            # Botón dentro de la tarjeta
            ctk.CTkButton(
                marco,
                text="VER EVIDENCIA HTTP",
                command=abrir_evidencia,
                fg_color=MORADO,
                hover_color="#5030BF",
                width=190,
                height=35
            ).pack(
                anchor="w",
                padx=14,
                pady=(0, 12)
            )

        else:

            ctk.CTkLabel(
                marco,
                text="Sin evidencia HTTP vinculada",
                text_color=GRIS
            ).pack(
                anchor="w",
                padx=14,
                pady=(0, 12)
            )




# ==========================================
# NAVEGACION
# ==========================================

def mostrar(nombre):

    for elemento in principal.winfo_children():
        elemento.destroy()

    for titulo, boton in botones.items():
        if titulo == nombre:
            boton.configure(fg_color=MORADO)
        else:
            boton.configure(fg_color="transparent")

    pantallas = {
        "Dashboard": pantalla_dashboard,
        "Proyectos": pantalla_proyectos,
        "Análisis": pantalla_analisis,
        "Hallazgos": pantalla_hallazgos,
        "Verificación": pantalla_verificacion,
        "Historial": pantalla_historial

    }

    if nombre in pantallas:
        pantallas[nombre]()

    else:
        encabezado(
            nombre,
            "Disponible en versiones posteriores"
        )

        ctk.CTkLabel(
            principal,
            text="Módulo en desarrollo",
            text_color=LAVANDA
        ).pack(pady=60)


# ==========================================
# BOTONES LATERALES
# ==========================================

for seccion in SECCIONES:

    boton = ctk.CTkButton(
        menu,
        text=seccion,
        fg_color="transparent",
        hover_color="#39304F",
        text_color=BLANCO,
        anchor="w",
        height=40,
        command=lambda s=seccion: mostrar(s)
    )

    boton.pack(
        fill="x",
        padx=15,
        pady=3
    )

    botones[seccion] = boton


# ==========================================
# INICIAR MOONDETEX
# ==========================================

mostrar("Dashboard")

ventana.mainloop()
