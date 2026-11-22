import os
import sqlite3
import threading
from contextlib import closing
from tkinter import messagebox

import customtkinter as ctk

from almacen_politicas_v36 import consultar_politica_proyecto
from auditor_dns_v45 import ejecutar_auditoria_dns
from base_datos import DB
from enumerador_pasivo_v41 import (
    analizar_lote_subdominios,
    descubrir_subdominios_pasivos,
)
from inspector_tls_v44 import ejecutar_inspeccion_tls
from orquestador_bounty_v39 import ejecutar_analisis_bounty
from reportador_bounty_v42 import exportar_reporte_markdown
from sensor_http_v38 import ControladorVelocidad
from superficie_web_v43 import ejecutar_recon_superficie
from tema import BLANCO, FONDO, GRIS, LAVANDA, MORADO, PANEL, ROSA, TARJETA


# =====================================
# MOONDETEX V0.45
# PANEL GRAFICO DE BUG BOUNTY RECON
# =====================================

def _leer_proyectos_y_politicas():
    if not DB.is_file():
        return []
    with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as con:
        con.execute("PRAGMA query_only = ON")
        filas = con.execute(
            "SELECT id, nombre, alcance FROM proyectos ORDER BY id"
        ).fetchall()
        resultado = []
        for pid, nombre, alcance in filas:
            try:
                pol = consultar_politica_proyecto(con, pid)
            except ValueError:
                pol = None
            resultado.append((pid, nombre, alcance, pol))
        return resultado


def renderizar_panel_bug_bounty(contenedor):
    """Dibuja la vista completa de Bug Bounty dentro del marco principal."""
    for hijo in contenedor.winfo_children():
        hijo.destroy()

    cabecera = ctk.CTkFrame(contenedor, fg_color="transparent")
    cabecera.pack(fill="x", padx=22, pady=(18, 8))

    ctk.CTkLabel(
        cabecera,
        text="Bug Bounty Recon",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color=BLANCO,
    ).pack(anchor="w")

    ctk.CTkLabel(
        cabecera,
        text="Gatekeeper anti-SSRF, IP Pinning, crt.sh, Superficie Web, TLS X.509, DNS y Reportes SHA-256",
        font=ctk.CTkFont(size=13),
        text_color=LAVANDA,
    ).pack(anchor="w", pady=(2, 0))

    scroll = ctk.CTkScrollableFrame(contenedor, fg_color="transparent")
    scroll.pack(fill="both", expand=True, padx=14, pady=(4, 14))

    datos_proyectos = _leer_proyectos_y_politicas()
    if not datos_proyectos:
        ctk.CTkLabel(
            scroll,
            text="No hay proyectos registrados. Crea uno primero en la pestaña Proyectos.",
            text_color=LAVANDA,
            font=ctk.CTkFont(size=14),
        ).pack(pady=40)
        return

    mapa_proyectos = {
        f"ID {pid} | {nombre}": (pid, nombre, alcance, pol)
        for pid, nombre, alcance, pol in datos_proyectos
    }
    estado_lote = {"subdominios": []}

    # -------------------------------------------------
    # TARJETA 1: SELECCION DE PROYECTO Y POLITICA
    # -------------------------------------------------
    card_proj = ctk.CTkFrame(scroll, fg_color=TARJETA, corner_radius=12)
    card_proj.pack(fill="x", padx=8, pady=6)

    ctk.CTkLabel(
        card_proj,
        text="1. Proyecto y Politica de Alcance Autorizada",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=BLANCO,
    ).pack(anchor="w", padx=16, pady=(12, 6))

    fila_sel = ctk.CTkFrame(card_proj, fg_color="transparent")
    fila_sel.pack(fill="x", padx=16, pady=(0, 6))

    var_proyecto = ctk.StringVar(value=list(mapa_proyectos.keys())[0])
    menu_proyectos = ctk.CTkOptionMenu(
        fila_sel,
        variable=var_proyecto,
        values=list(mapa_proyectos.keys()),
        fg_color=MORADO,
        button_color="#5030BF",
        width=360,
    )
    menu_proyectos.pack(side="left")

    lbl_politica = ctk.CTkLabel(
        card_proj,
        text="",
        font=ctk.CTkFont(size=12),
        text_color=LAVANDA,
        justify="left",
    )
    lbl_politica.pack(anchor="w", padx=16, pady=(2, 12))

    def refrescar_info_politica(*_args):
        datos_act = _leer_proyectos_y_politicas()
        mapa_proyectos.clear()
        for pid, nom, alc, pol in datos_act:
            mapa_proyectos[f"ID {pid} | {nom}"] = (pid, nom, alc, pol)

        seleccion = var_proyecto.get()
        if seleccion not in mapa_proyectos and mapa_proyectos:
            seleccion = list(mapa_proyectos.keys())[0]
            var_proyecto.set(seleccion)

        _, _, alc, pol = mapa_proyectos[seleccion]
        if pol is None:
            lbl_politica.configure(
                text=f"Alcance: {alc}  |  Politica: PENDIENTE (Configurala en 'Proyectos' antes de escanear)",
                text_color=ROSA,
            )
        else:
            doms = ", ".join(sorted(pol["dominios"]))
            puertos = ", ".join(str(p) for p in sorted(pol["puertos"]))
            protos = ", ".join(sorted(pol["protocolos"]))
            lbl_politica.configure(
                text=f"Politica ACTIVA  |  Dominios: [{doms}]  |  Puertos: [{puertos}]  |  Protocolos: [{protos}]",
                text_color=LAVANDA,
            )

    menu_proyectos.configure(command=refrescar_info_politica)
    refrescar_info_politica()

    # -------------------------------------------------
    # TARJETA 2: PARAMETROS Y SENSORES PASIVOS
    # -------------------------------------------------
    card_ops = ctk.CTkFrame(scroll, fg_color=TARJETA, corner_radius=12)
    card_ops.pack(fill="x", padx=8, pady=6)

    ctk.CTkLabel(
        card_ops,
        text="2. Objetivo y Motores de Reconocimiento Seguro",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=BLANCO,
    ).pack(anchor="w", padx=16, pady=(12, 8))

    grid_inputs = ctk.CTkFrame(card_ops, fg_color="transparent")
    grid_inputs.pack(fill="x", padx=16, pady=(0, 8))

    # Fila 1: Protocolo, Dominio, Puerto
    ctk.CTkLabel(grid_inputs, text="Protocolo:", text_color=GRIS).grid(row=0, column=0, sticky="w", padx=(0, 6))
    var_proto = ctk.StringVar(value="https")
    ctk.CTkOptionMenu(
        grid_inputs,
        variable=var_proto,
        values=["https", "http"],
        fg_color=PANEL,
        button_color=MORADO,
        width=95,
    ).grid(row=0, column=1, sticky="w", padx=(0, 14))

    ctk.CTkLabel(grid_inputs, text="Dominio objetivo / base:", text_color=GRIS).grid(row=0, column=2, sticky="w", padx=(0, 6))
    ent_host = ctk.CTkEntry(
        grid_inputs,
        placeholder_text="ej. example.org",
        fg_color=PANEL,
        border_color=MORADO,
        text_color=BLANCO,
        width=230,
    )
    ent_host.insert(0, "example.org")
    ent_host.grid(row=0, column=3, sticky="w", padx=(0, 14))

    ctk.CTkLabel(grid_inputs, text="Puerto:", text_color=GRIS).grid(row=0, column=4, sticky="w", padx=(0, 6))
    ent_puerto = ctk.CTkEntry(
        grid_inputs,
        fg_color=PANEL,
        border_color=MORADO,
        text_color=BLANCO,
        width=75,
    )
    ent_puerto.insert(0, "443")
    ent_puerto.grid(row=0, column=5, sticky="w")

    # Fila 2: Ruta y Cabecera X-Bug-Bounty
    ctk.CTkLabel(grid_inputs, text="Ruta HTTP:", text_color=GRIS).grid(row=1, column=0, sticky="w", pady=(10, 0), padx=(0, 6))
    ent_ruta = ctk.CTkEntry(
        grid_inputs,
        fg_color=PANEL,
        border_color=MORADO,
        text_color=BLANCO,
        width=95,
    )
    ent_ruta.insert(0, "/")
    ent_ruta.grid(row=1, column=1, sticky="w", pady=(10, 0), padx=(0, 14))

    ctk.CTkLabel(grid_inputs, text="X-Bug-Bounty:", text_color=GRIS).grid(row=1, column=2, sticky="w", pady=(10, 0), padx=(0, 6))
    ent_bounty = ctk.CTkEntry(
        grid_inputs,
        fg_color=PANEL,
        border_color=MORADO,
        text_color=BLANCO,
        width=230,
    )
    ent_bounty.insert(0, "MoonDetex-Research")
    ent_bounty.grid(row=1, column=3, sticky="w", pady=(10, 0), padx=(0, 14))

    # Botonera de sensores
    fila_btns_1 = ctk.CTkFrame(card_ops, fg_color="transparent")
    fila_btns_1.pack(fill="x", padx=16, pady=(6, 4))

    fila_btns_2 = ctk.CTkFrame(card_ops, fg_color="transparent")
    fila_btns_2.pack(fill="x", padx=16, pady=(4, 12))

    botones_accion = []

    def _set_botones_habilitados(habilitado):
        estado = "normal" if habilitado else "disabled"
        for b in botones_accion:
            b.configure(state=estado)
        if habilitado and estado_lote["subdominios"]:
            btn_lote.configure(state="normal")
        else:
            btn_lote.configure(state="disabled")

    def _escribir_salida(texto, limpiar=False):
        if not contenedor.winfo_exists():
            return
        caja_salida.configure(state="normal")
        if limpiar:
            caja_salida.delete("1.0", "end")
        caja_salida.insert("end", texto + "\n")
        caja_salida.see("end")
        caja_salida.configure(state="disabled")

    def _obtener_parametros():
        pid = mapa_proyectos[var_proyecto.get()][0]
        proto = var_proto.get().strip().lower()
        host = ent_host.get().strip().lower()
        puerto_txt = ent_puerto.get().strip()
        ruta = ent_ruta.get().strip() or "/"
        ident = ent_bounty.get().strip() or "MoonDetex-Research"

        if not host:
            raise ValueError("Debes escribir un dominio objetivo o base.")
        if not puerto_txt.isdigit():
            raise ValueError("El puerto debe ser un numero entero.")
        return pid, proto, host, int(puerto_txt), ruta, ident

    def _lanzar_en_hilo(titulo_tarea, funcion_tarea):
        try:
            params = _obtener_parametros()
        except Exception as err:
            messagebox.showwarning("Validacion", str(err))
            return

        _set_botones_habilitados(False)
        _escribir_salida(f">>> Iniciando: {titulo_tarea}...", limpiar=True)

        def worker():
            try:
                lineas_resultado = funcion_tarea(*params)
                if contenedor.winfo_exists():
                    contenedor.after(0, lambda: _escribir_salida("\n".join(lineas_resultado)))
            except Exception as exc:
                if contenedor.winfo_exists():
                    contenedor.after(0, lambda: _escribir_salida(f"\n[BLOQUEADO / ERROR]: {exc}"))
            finally:
                if contenedor.winfo_exists():
                    contenedor.after(0, lambda: _set_botones_habilitados(True))

        threading.Thread(target=worker, daemon=True).start()

    # --- Accion 1: Analisis HTTP Seguro (Clase 39) ---
    def tarea_http(pid, proto, host, puerto, ruta, ident):
        ctrl = ControladorVelocidad(intervalo_segundos=1.5)
        res = ejecutar_analisis_bounty(
            proyecto_id=pid,
            protocolo=proto,
            host=host,
            puerto=puerto,
            ruta=ruta,
            metodo="HEAD",
            identificador_bounty=ident,
            controlador_tasa=ctrl,
        )
        salida = [
            f"Analisis ID:        #{res['analisis_id']}",
            f"IP fijada usada:    {res['ip_conectada']}",
            f"Codigo HTTP:        {res['estado_http']}",
            f"Evidencia SHA-256:  {res['huella_sha256']}",
            f"Hallazgos actuales: {res['total_observaciones']}",
        ]
        dif = res["diferencias"]
        if dif:
            salida.append(f"Comparado con #{dif['analisis_anterior_id']}:")
            salida.append(f"  + Nuevas:    {dif['nuevas'] or 'Ninguna'}")
            salida.append(f"  ~ Cambiadas: {dif['cambiadas'] or 'Ninguna'}")
            salida.append(f"  - Ausentes:  {dif['ausentes'] or 'Ninguna'}")
        return salida

    # --- Accion 2: Superficie Estandar y Cookies (Clase 43) ---
    def tarea_superficie(pid, proto, host, puerto, _ruta, ident):
        res = ejecutar_recon_superficie(
            proyecto_id=pid,
            protocolo=proto,
            host=host,
            puerto=puerto,
            identificador_bounty=ident,
            intervalo_segundos=1.5,
        )
        salida = [
            f"Analisis ID:        #{res['analisis_id']}",
            f"IP fijada usada:    {res['ip_conectada']}",
            f"Estados HTTP:       {res['estados']}",
            f"Evidencia SHA-256:  {res['huella_sha256']}",
            f"Hallazgos actuales: {res['total_observaciones']}",
        ]
        for obs in res["observaciones"]:
            salida.append(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")
        return salida

    # --- Accion 3: Inspector TLS y SANs (Clase 44) ---
    def tarea_tls(pid, _proto, host, puerto, _ruta, _ident):
        res = ejecutar_inspeccion_tls(
            proyecto_id=pid,
            host=host,
            puerto=puerto,
            intervalo_segundos=1.5,
        )
        cert = res["resumen_certificado"]
        salida = [
            f"Analisis ID:        #{res['analisis_id']}",
            f"IP fijada usada:    {res['ip_conectada']}",
            f"Protocolo TLS:      {cert['version_tls']}",
            f"Emisor:             {cert['emisor']}",
            f"Expira:             {cert['expira']}",
            f"SANs en alcance:    {cert['sans_en_alcance']} (fuera omitidos: {cert['sans_fuera_alcance_total']})",
            f"Evidencia SHA-256:  {res['huella_sha256']}",
            f"Hallazgos actuales: {res['total_observaciones']}",
        ]
        for obs in res["observaciones"]:
            salida.append(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")
        return salida

    # --- Accion 4: Auditoria Pasiva DNS (Clase 45) ---
    def tarea_dns(pid, _proto, host, _puerto, _ruta, _ident):
        res = ejecutar_auditoria_dns(
            proyecto_id=pid,
            host=host,
            intervalo_segundos=0.8,
        )
        regs = res["registros_dns"]
        salida = [
            f"Analisis ID:        #{res['analisis_id']}",
            f"Dominio auditado:   {res['host']}",
            f"SPF:                {regs['spf'] or 'No publicado'}",
            f"DMARC:              {regs['dmarc'] or 'No publicado'}",
            f"CAA:                {regs['caa'] or 'No publicado'}",
            f"Evidencia SHA-256:  {res['huella_sha256']}",
            f"Hallazgos actuales: {res['total_observaciones']}",
        ]
        for obs in res["observaciones"]:
            salida.append(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")
        return salida

    # --- Accion 5: Enumeracion Pasiva crt.sh (Clase 41) ---
    def tarea_crtsh(pid, _proto, host, _puerto, _ruta, _ident):
        subs = descubrir_subdominios_pasivos(pid, host)
        estado_lote["subdominios"] = subs
        if not subs:
            return ["No se encontraron subdominios nuevos dentro de la politica del proyecto."]
        salida = [f"Subdominios autorizados encontrados ({len(subs)}):"]
        for i, s in enumerate(subs, 1):
            salida.append(f"  {i}. {s}")
        salida.append("\nPulsa 'Analizar Lote Descubierto' si deseas escanearlos con pausa de 2.0s.")
        return salida

    # --- Accion 6: Escaneo del Lote Descubierto (Clase 41) ---
    def tarea_lote(pid, proto, _host, puerto, _ruta, ident):
        subs = list(estado_lote["subdominios"])
        resumen = analizar_lote_subdominios(
            proyecto_id=pid,
            subdominios=subs,
            protocolo=proto,
            puerto=puerto,
            ruta="/",
            identificador_bounty=ident,
            intervalo_segundos=2.0,
        )
        salida = ["=== RESUMEN DEL ESCANEO POR LOTES ==="]
        for item in resumen:
            if item["estado"] == "ANALIZADO":
                salida.append(
                    f"  [OK]      {item['host']} -> HTTP {item['estado_http']} "
                    f"(Analisis #{item['analisis_id']}, Hallazgos: {item['total_observaciones']})"
                )
            else:
                salida.append(f"  [OMITIDO] {item['host']} -> {item['motivo']}")
        return salida

    btn_http = ctk.CTkButton(
        fila_btns_1,
        text="Analisis HTTP Seguro",
        fg_color=MORADO,
        hover_color="#5030BF",
        command=lambda: _lanzar_en_hilo("Analisis HTTP Seguro", tarea_http),
    )
    btn_http.pack(side="left", padx=(0, 8))

    btn_sup = ctk.CTkButton(
        fila_btns_1,
        text="Cookies, robots y security.txt",
        fg_color=MORADO,
        hover_color="#5030BF",
        command=lambda: _lanzar_en_hilo("Auditoria de Superficie Estandar", tarea_superficie),
    )
    btn_sup.pack(side="left", padx=(0, 8))

    btn_tls = ctk.CTkButton(
        fila_btns_1,
        text="Certificado TLS y SANs",
        fg_color=MORADO,
        hover_color="#5030BF",
        command=lambda: _lanzar_en_hilo("Inspeccion Pasiva TLS", tarea_tls),
    )
    btn_tls.pack(side="left", padx=(0, 8))

    btn_dns = ctk.CTkButton(
        fila_btns_1,
        text="Seguridad DNS (SPF/DMARC/CAA)",
        fg_color=MORADO,
        hover_color="#5030BF",
        command=lambda: _lanzar_en_hilo("Auditoria Pasiva de Seguridad DNS", tarea_dns),
    )
    btn_dns.pack(side="left")

    btn_crt = ctk.CTkButton(
        fila_btns_2,
        text="1. Enumerar crt.sh (Pasivo)",
        fg_color=ROSA,
        hover_color="#D93B87",
        text_color=BLANCO,
        command=lambda: _lanzar_en_hilo("Enumeracion Pasiva crt.sh", tarea_crtsh),
    )
    btn_crt.pack(side="left", padx=(0, 8))

    btn_lote = ctk.CTkButton(
        fila_btns_2,
        text="2. Analizar Lote Descubierto",
        fg_color="#5030BF",
        hover_color=MORADO,
        state="disabled",
        command=lambda: _lanzar_en_hilo("Escaneo Controlado por Lotes", tarea_lote),
    )
    btn_lote.pack(side="left", padx=(0, 14))

    var_incluir_pend = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(
        fila_btns_2,
        text="Incluir Pendientes",
        variable=var_incluir_pend,
        text_color=GRIS,
        fg_color=MORADO,
    ).pack(side="left", padx=(0, 8))

    def exportar_md_gui():
        try:
            pid = mapa_proyectos[var_proyecto.get()][0]
            ruta_md = exportar_reporte_markdown(
                proyecto_id=pid,
                incluir_pendientes=var_incluir_pend.get(),
            )
            _escribir_salida(
                f"Informe tecnico exportado correctamente:\n  {ruta_md}",
                limpiar=True,
            )
            if messagebox.askyesno(
                "Informe Generado",
                f"Reporte guardado en:\n{ruta_md}\n\n¿Deseas abrir la carpeta de reportes?",
            ):
                os.startfile(ruta_md.parent)
        except Exception as exc:
            messagebox.showerror("Error al exportar", str(exc))

    btn_md = ctk.CTkButton(
        fila_btns_2,
        text="Exportar Informe .md",
        fg_color=PANEL,
        border_width=1,
        border_color=LAVANDA,
        hover_color="#39304F",
        text_color=BLANCO,
        command=exportar_md_gui,
    )
    btn_md.pack(side="left")

    botones_accion.extend([btn_http, btn_sup, btn_tls, btn_dns, btn_crt, btn_md])

    # -------------------------------------------------
    # TARJETA 3: SALIDA FORENSE EN VIVO
    # -------------------------------------------------
    card_out = ctk.CTkFrame(scroll, fg_color=TARJETA, corner_radius=12)
    card_out.pack(fill="both", expand=True, padx=8, pady=6)

    ctk.CTkLabel(
        card_out,
        text="3. Salida Forense y Cadena de Custodia (SHA-256)",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color=BLANCO,
    ).pack(anchor="w", padx=16, pady=(12, 6))

    caja_salida = ctk.CTkTextbox(
        card_out,
        fg_color=FONDO,
        text_color=BLANCO,
        font=ctk.CTkFont(family="Consolas", size=12),
        height=230,
        corner_radius=8,
    )
    caja_salida.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    caja_salida.insert(
        "1.0",
        "Listo. Selecciona un proyecto con politica activa y ejecuta un sensor seguro.\n"
        "Nota: Puedes clasificar tus hallazgos en la pestaña 'Hallazgos' antes de exportar el informe .md.\n",
    )
    caja_salida.configure(state="disabled")