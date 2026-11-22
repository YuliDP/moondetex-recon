import sqlite3
from contextlib import closing

from almacen_politicas_v36 import (
    actualizar_politica_proyecto,
    consultar_politica_proyecto,
    guardar_politica_proyecto,
)
from auditor_dns_v45 import ejecutar_auditoria_dns
from base_datos import DB, conectar
from enumerador_pasivo_v41 import (
    analizar_lote_subdominios,
    descubrir_subdominios_pasivos,
)
from inspector_tls_v44 import ejecutar_inspeccion_tls
from orquestador_bounty_v39 import ejecutar_analisis_bounty
from reportador_bounty_v42 import (
    cambiar_estado_hallazgo,
    exportar_reporte_markdown,
)
from sensor_http_v38 import ControladorVelocidad
from superficie_web_v43 import ejecutar_recon_superficie


# =====================================
# MOONDETEX V0.45
# CONSOLA PRINCIPAL DE BUG BOUNTY
# =====================================

def _abrir_solo_lectura():
    if not DB.is_file():
        raise FileNotFoundError("No se encontro moondetex.db")
    conexion = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)
    conexion.execute("PRAGMA query_only = ON")
    return conexion


def _pedir_entero(mensaje):
    texto = input(mensaje).strip()
    if not texto.isdigit() or int(texto) <= 0:
        raise ValueError("Debes ingresar un numero entero positivo.")
    return int(texto)


def listar_proyectos():
    print("\n--- PROYECTOS REGISTRADOS ---")
    with closing(_abrir_solo_lectura()) as conexion:
        filas = conexion.execute(
            "SELECT id, nombre, alcance, fecha FROM proyectos ORDER BY id"
        ).fetchall()

        if not filas:
            print("Aun no hay proyectos registrados.")
            return

        for proyecto_id, nombre, alcance, fecha in filas:
            try:
                politica = consultar_politica_proyecto(conexion, proyecto_id)
                if politica is None:
                    estado_pol = "PENDIENTE (Analisis bloqueado)"
                else:
                    dominios = ", ".join(sorted(politica["dominios"]))
                    puertos = ", ".join(str(p) for p in sorted(politica["puertos"]))
                    estado_pol = f"ACTIVA -> Dominios: [{dominios}] | Puertos: [{puertos}]"
            except ValueError as error:
                estado_pol = f"INVALIDA ({error})"

            print(f"\nID: {proyecto_id} | {nombre}")
            print(f"  Alcance descrito: {alcance}")
            print(f"  Creado: {fecha}")
            print(f"  Politica: {estado_pol}")


def crear_proyecto():
    print("\n--- NUEVO PROYECTO DE BUG BOUNTY ---")
    nombre = input("Nombre del programa/proyecto: ").strip()
    alcance = input("Descripcion breve del alcance (ej. Programa H1 - *.empresa.com): ").strip()
    notas = input("Notas opcionales (Enter para omitir): ").strip()

    if not nombre or not alcance:
        raise ValueError("El nombre y el alcance son obligatorios.")

    with closing(conectar()) as conexion:
        with conexion:
            cursor = conexion.execute(
                "INSERT INTO proyectos (nombre, alcance, notas) VALUES (?, ?, ?)",
                (nombre, alcance, notas),
            )
            nuevo_id = cursor.lastrowid

    print(f"Proyecto creado correctamente con ID: {nuevo_id}")
    print("Recuerda configurar su politica en la opcion 3 antes de analizar.")


def configurar_politica():
    print("\n--- CONFIGURAR POLITICA DE ALCANCE ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")

    print("Ingresa los valores separados por coma (ej. example.com, *.example.com)")
    dom_raw = input("Dominios permitidos: ").strip()
    pue_raw = input("Puertos permitidos (ej. 80, 443): ").strip()
    pro_raw = input("Protocolos permitidos (http, https): ").strip()

    dominios = {d.strip().lower() for d in dom_raw.split(",") if d.strip()}
    protocolos = {p.strip().lower() for p in pro_raw.split(",") if p.strip()}

    puertos = set()
    for parte in pue_raw.split(","):
        limpio = parte.strip()
        if limpio:
            if not limpio.isdigit():
                raise ValueError(f"Puerto invalido: {limpio}")
            puertos.add(int(limpio))

    politica = {
        "dominios": dominios,
        "puertos": puertos,
        "protocolos": protocolos,
    }

    with closing(conectar()) as conexion:
        existente = consultar_politica_proyecto(conexion, proyecto_id)
        with conexion:
            if existente is None:
                guardar_politica_proyecto(conexion, proyecto_id, politica)
                print("Politica guardada correctamente. Analisis de red habilitado.")
            else:
                actualizar_politica_proyecto(conexion, proyecto_id, politica)
                print("Politica actualizada correctamente.")


def lanzar_analisis():
    print("\n--- EJECUTAR ANALISIS SEGURO (BUG BOUNTY) ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")
    protocolo = (input("Protocolo [https]: ").strip().lower()) or "https"
    host = input("Dominio objetivo concreto (ej. www.example.com): ").strip().lower()
    puerto_txt = input("Puerto [443]: ").strip() or "443"

    if not puerto_txt.isdigit():
        raise ValueError("El puerto debe ser un numero.")
    puerto = int(puerto_txt)

    ruta = input("Ruta HTTP [/]: ").strip() or "/"
    identificador = (
        input("Cabecera X-Bug-Bounty [MoonDetex-Research]: ").strip()
        or "MoonDetex-Research"
    )

    print("\nValidando alcance, resolviendo DNS y consultando objetivo...")
    controlador = ControladorVelocidad(intervalo_segundos=1.5)

    resultado = ejecutar_analisis_bounty(
        proyecto_id=proyecto_id,
        protocolo=protocolo,
        host=host,
        puerto=puerto,
        ruta=ruta,
        metodo="HEAD",
        identificador_bounty=identificador,
        controlador_tasa=controlador,
    )

    print("\n=== RESULTADO DEL ANALISIS ===")
    print(f"Analisis ID:        #{resultado['analisis_id']}")
    print(f"IP fijada usada:    {resultado['ip_conectada']}")
    print(f"Codigo HTTP:        {resultado['estado_http']}")
    print(f"Evidencia SHA-256:  {resultado['huella_sha256'][:24]}...")
    print(f"Hallazgos actuales: {resultado['total_observaciones']}")

    dif = resultado["diferencias"]
    if dif is None:
        print("Comparacion:        Primer analisis registrado para este proyecto.")
    else:
        print(f"Comparado con #{dif['analisis_anterior_id']}:")
        print(f"  + Nuevas:     {dif['nuevas'] or 'Ninguna'}")
        print(f"  ~ Cambiadas:  {dif['cambiadas'] or 'Ninguna'}")
        print(f"  - Ausentes:   {dif['ausentes'] or 'Ninguna'}")


def _mostrar_hallazgos_proyecto(proyecto_id):
    with closing(_abrir_solo_lectura()) as conexion:
        filas = conexion.execute(
            """
            SELECT id, clave, titulo, detalle, estado, fecha
            FROM hallazgos
            WHERE proyecto_id = ?
            ORDER BY id
            """,
            (proyecto_id,),
        ).fetchall()

        if not filas:
            print("No hay hallazgos registrados para este proyecto.")
            return False

        for hid, clave, titulo, detalle, estado, fecha in filas:
            print(f"\n[#{hid}] ({estado}) {titulo}")
            print(f"  Clave:   {clave}")
            print(f"  Detalle: {detalle}")
            print(f"  Fecha:   {fecha}")
        return True


def ver_hallazgos():
    print("\n--- HALLAZGOS REGISTRADOS ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")
    _mostrar_hallazgos_proyecto(proyecto_id)


def enumerar_y_analizar_lote():
    print("\n--- ENUMERACION PASIVA (crt.sh) Y ESCANEO POR LOTES ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")
    dominio_base = input("Dominio base a consultar (ej. example.org): ").strip().lower()

    print("\nConsultando registros publicos de Certificate Transparency...")
    subdominios = descubrir_subdominios_pasivos(proyecto_id, dominio_base)

    if not subdominios:
        print("No se encontraron subdominios nuevos dentro de la politica del proyecto.")
        return

    print(f"\nSubdominios autorizados encontrados ({len(subdominios)}):")
    for idx, sub in enumerate(subdominios, start=1):
        print(f"  {idx}. {sub}")

    confirmar = input("\n¿Ejecutar analisis HTTP seguro sobre este lote? [s/N]: ").strip().lower()
    if confirmar != "s":
        print("Escaneo por lotes cancelado. No se envio trafico al objetivo.")
        return

    protocolo = (input("Protocolo [https]: ").strip().lower()) or "https"
    puerto_txt = input("Puerto [443]: ").strip() or "443"
    if not puerto_txt.isdigit():
        raise ValueError("El puerto debe ser un numero.")
    puerto = int(puerto_txt)

    identificador = (
        input("Cabecera X-Bug-Bounty [MoonDetex-Research]: ").strip()
        or "MoonDetex-Research"
    )

    print("\nIniciando escaneo controlado (pausa de 2.0s entre objetivos)...")
    resumen = analizar_lote_subdominios(
        proyecto_id=proyecto_id,
        subdominios=subdominios,
        protocolo=protocolo,
        puerto=puerto,
        ruta="/",
        identificador_bounty=identificador,
        intervalo_segundos=2.0,
    )

    print("\n=== RESUMEN DEL ESCANEO POR LOTES ===")
    for item in resumen:
        if item["estado"] == "ANALIZADO":
            print(
                f"  [OK]      {item['host']} -> HTTP {item['estado_http']} "
                f"(Analisis #{item['analisis_id']}, Hallazgos: {item['total_observaciones']})"
            )
        else:
            print(f"  [OMITIDO] {item['host']} -> {item['motivo']}")


def triaje_hallazgo():
    print("\n--- TRIAJE DE HALLAZGOS ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")

    if not _mostrar_hallazgos_proyecto(proyecto_id):
        return

    hallazgo_id = _pedir_entero("\nID del hallazgo a clasificar (ej. 41): ")

    estados = {
        "1": "Pendiente",
        "2": "Revisado",
        "3": "Falso Positivo",
        "4": "Reportable",
    }
    print("\nSelecciona el nuevo estado:")
    for num, nombre in estados.items():
        print(f"  {num}. {nombre}")

    opcion_estado = input("Estado [1-4]: ").strip()
    if opcion_estado not in estados:
        raise ValueError("Debes elegir una opcion entre 1 y 4.")

    nuevo_estado = estados[opcion_estado]
    cambiar_estado_hallazgo(proyecto_id, hallazgo_id, nuevo_estado)
    print(f"Hallazgo #{hallazgo_id} actualizado a: {nuevo_estado}")


def generar_reporte():
    print("\n--- EXPORTAR INFORME TECNICO (MARKDOWN) ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")
    resp = input("¿Incluir hallazgos en estado 'Pendiente'? [s/N]: ").strip().lower()
    incluir_pendientes = resp == "s"

    ruta_reporte = exportar_reporte_markdown(
        proyecto_id=proyecto_id,
        incluir_pendientes=incluir_pendientes,
    )
    print("\nInforme generado correctamente:")
    print(f"  Archivo: {ruta_reporte}")


def auditar_superficie_estandar():
    print("\n--- AUDITORIA DE COOKIES, ROBOTS.TXT Y SECURITY.TXT ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")
    protocolo = (input("Protocolo [https]: ").strip().lower()) or "https"
    host = input("Dominio objetivo concreto (ej. example.org): ").strip().lower()
    puerto_txt = input("Puerto [443]: ").strip() or "443"

    if not puerto_txt.isdigit():
        raise ValueError("El puerto debe ser un numero.")
    puerto = int(puerto_txt)

    identificador = (
        input("Cabecera X-Bug-Bounty [MoonDetex-Research]: ").strip()
        or "MoonDetex-Research"
    )

    print("\nInspeccionando /, /robots.txt y /.well-known/security.txt (pausa de 1.5s)...")
    resultado = ejecutar_recon_superficie(
        proyecto_id=proyecto_id,
        protocolo=protocolo,
        host=host,
        puerto=puerto,
        identificador_bounty=identificador,
        intervalo_segundos=1.5,
    )

    print("\n=== RESULTADO DE SUPERFICIE ESTANDAR ===")
    print(f"Analisis ID:        #{resultado['analisis_id']}")
    print(f"IP fijada usada:    {resultado['ip_conectada']}")
    print(f"Estados HTTP:       {resultado['estados']}")
    print(f"Evidencia SHA-256:  {resultado['huella_sha256'][:24]}...")
    print(f"Hallazgos actuales: {resultado['total_observaciones']}")

    for obs in resultado["observaciones"]:
        print(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")


def inspeccionar_tls_objetivo():
    print("\n--- INSPECCION PASIVA DE CERTIFICADO TLS Y SANs ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")
    host = input("Dominio objetivo concreto (ej. example.org): ").strip().lower()
    puerto_txt = input("Puerto HTTPS [443]: ").strip() or "443"

    if not puerto_txt.isdigit():
        raise ValueError("El puerto debe ser un numero.")
    puerto = int(puerto_txt)

    print("\nConectando por IP fijada y leyendo certificado X.509...")
    resultado = ejecutar_inspeccion_tls(
        proyecto_id=proyecto_id,
        host=host,
        puerto=puerto,
        intervalo_segundos=1.5,
    )

    cert = resultado["resumen_certificado"]
    print("\n=== RESULTADO DE INSPECCION TLS ===")
    print(f"Analisis ID:        #{resultado['analisis_id']}")
    print(f"IP fijada usada:    {resultado['ip_conectada']}")
    print(f"Protocolo TLS:      {cert['version_tls']}")
    print(f"Emisor:             {cert['emisor']}")
    print(f"Expira:             {cert['expira']}")
    print(
        f"SANs en alcance:    {cert['sans_en_alcance']} "
        f"(fuera de alcance omitidos: {cert['sans_fuera_alcance_total']})"
    )
    print(f"Evidencia SHA-256:  {resultado['huella_sha256'][:24]}...")
    print(f"Hallazgos actuales: {resultado['total_observaciones']}")

    for obs in resultado["observaciones"]:
        print(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")


def auditar_dns_objetivo():
    print("\n--- AUDITORIA PASIVA DE SEGURIDAD DNS (SPF, DMARC Y CAA) ---")
    proyecto_id = _pedir_entero("ID del proyecto: ")
    host = input("Dominio objetivo concreto (ej. example.org): ").strip().lower()

    print("\nConsultando registros publicos TXT y CAA via DNS-over-HTTPS...")
    resultado = ejecutar_auditoria_dns(
        proyecto_id=proyecto_id,
        host=host,
        intervalo_segundos=0.8,
    )

    regs = resultado["registros_dns"]
    print("\n=== RESULTADO DE AUDITORIA DNS ===")
    print(f"Analisis ID:        #{resultado['analisis_id']}")
    print(f"Dominio auditado:   {resultado['host']}")
    print(f"SPF:                {regs['spf'] or 'No publicado'}")
    print(f"DMARC:              {regs['dmarc'] or 'No publicado'}")
    print(f"CAA:                {regs['caa'] or 'No publicado'}")
    print(f"Evidencia SHA-256:  {resultado['huella_sha256'][:24]}...")
    print(f"Hallazgos actuales: {resultado['total_observaciones']}")

    for obs in resultado["observaciones"]:
        print(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")


def menu_principal():
    opciones = {
        "1": ("Listar proyectos y politicas", listar_proyectos),
        "2": ("Crear nuevo proyecto", crear_proyecto),
        "3": ("Configurar o actualizar politica de alcance", configurar_politica),
        "4": ("Ejecutar analisis HTTP seguro", lanzar_analisis),
        "5": ("Ver hallazgos de un proyecto", ver_hallazgos),
        "6": ("Enumerar subdominios pasivos y analizar lote", enumerar_y_analizar_lote),
        "7": ("Clasificar hallazgo (Triaje)", triaje_hallazgo),
        "8": ("Exportar informe tecnico (.md)", generar_reporte),
        "9": ("Auditar cookies, robots.txt y security.txt", auditar_superficie_estandar),
        "10": ("Inspeccionar certificado TLS y SANs", inspeccionar_tls_objetivo),
        "11": ("Auditar seguridad DNS (SPF, DMARC y CAA)", auditar_dns_objetivo),
    }

    while True:
        print("\n========================================")
        print("         MOONDETEX - BUG BOUNTY         ")
        print("========================================")
        for clave, (descripcion, _) in opciones.items():
            print(f"  {clave}. {descripcion}")
        print("  0. Salir")

        eleccion = input("\nElige una opcion: ").strip()

        if eleccion == "0":
            print("Hasta luego, Yuli.")
            break

        if eleccion not in opciones:
            print("Opcion no valida.")
            continue

        try:
            opciones[eleccion][1]()
        except Exception as error:
            print(f"\n[BLOQUEADO / ERROR]: {error}")


if __name__ == "__main__":
    menu_principal()
