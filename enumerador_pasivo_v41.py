import json
import socket
import sqlite3
import urllib.parse
import urllib.request
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from base_datos import DB
from gatekeeper_v37 import host_en_alcance
from guardado_seguro_politicas_v35 import validar_dominio_alcance
from lector_politicas_v35 import cargar_politica
from orquestador_bounty_v39 import ejecutar_analisis_bounty
from sensor_http_v38 import ControladorVelocidad, _crear_contexto_ssl


# =====================================
# MOONDETEX - CLASE 41
# ENUMERADOR PASIVO (CT LOGS) Y LOTES
# =====================================

def _consultar_crtsh(dominio_base, timeout=20):
    consulta = urllib.parse.quote(f"%.{dominio_base}")
    url = f"https://crt.sh/?q={consulta}&output=json"

    peticion = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MoonDetex-PassiveRecon/0.41",
            "Accept": "application/json",
        },
    )

    contexto_ssl = _crear_contexto_ssl()
    with urllib.request.urlopen(
        peticion, timeout=timeout, context=contexto_ssl
    ) as respuesta:
        cuerpo = respuesta.read().decode("utf-8", errors="replace")

    if not cuerpo.strip():
        return []

    datos = json.loads(cuerpo)
    if not isinstance(datos, list):
        raise ValueError("Respuesta inesperada desde Certificate Transparency.")
    return datos


def _base_relacionada_con_politica(dominio_base, dominios_permitidos):
    for regla in dominios_permitidos:
        raiz_regla = regla[2:] if regla.startswith("*.") else regla
        if (
            dominio_base == raiz_regla
            or dominio_base.endswith("." + raiz_regla)
            or raiz_regla.endswith("." + dominio_base)
        ):
            return True
    return False


def descubrir_subdominios_pasivos(
    proyecto_id,
    dominio_base,
    db_ruta=DB,
    consultor_ct=None,
):
    if type(dominio_base) is not str or not dominio_base.strip():
        raise ValueError("Debes indicar un dominio base valido.")

    limpio = dominio_base.strip().lower()
    if limpio.startswith("*."):
        limpio = limpio[2:]

    validar_dominio_alcance(limpio)

    if not db_ruta.is_file():
        raise FileNotFoundError("No se encontro la base de datos.")

    with closing(
        sqlite3.connect(db_ruta.as_uri() + "?mode=ro", uri=True)
    ) as conexion:
        conexion.execute("PRAGMA query_only = ON")
        politica = cargar_politica(conexion, proyecto_id)

    if politica is None:
        raise ValueError(
            "El proyecto no tiene politica configurada. Enumeracion bloqueada."
        )

    if not _base_relacionada_con_politica(limpio, politica["dominios"]):
        raise ValueError(
            f"El dominio base '{limpio}' no corresponde al alcance del proyecto."
        )

    obtener_registros = (
        consultor_ct if consultor_ct is not None else _consultar_crtsh
    )
    registros = obtener_registros(limpio)

    candidatos = set()
    for fila in registros:
        if not isinstance(fila, dict):
            continue
        for campo in ("common_name", "name_value"):
            valor = fila.get(campo)
            if not isinstance(valor, str):
                continue
            for linea in valor.splitlines():
                host = linea.strip().lower().rstrip(".")
                if not host or "*" in host or "@" in host:
                    continue
                candidatos.add(host)

    # Filtrar estrictamente contra las reglas de alcance del proyecto
    autorizados = []
    for host in sorted(candidatos):
        try:
            validar_dominio_alcance(host)
            if host_en_alcance(host, politica["dominios"]):
                autorizados.append(host)
        except ValueError:
            continue

    return autorizados


def analizar_lote_subdominios(
    proyecto_id,
    subdominios,
    protocolo="https",
    puerto=443,
    ruta="/",
    identificador_bounty="MoonDetex-Research",
    intervalo_segundos=2.0,
    db_ruta=DB,
    resolvedor=None,
    ejecutor_http=None,
):
    if not subdominios:
        raise ValueError("La lista de subdominios para analizar esta vacia.")

    controlador = ControladorVelocidad(intervalo_segundos=intervalo_segundos)
    resumen = []

    for host in subdominios:
        try:
            resultado = ejecutar_analisis_bounty(
                proyecto_id=proyecto_id,
                protocolo=protocolo,
                host=host,
                puerto=puerto,
                ruta=ruta,
                metodo="HEAD",
                identificador_bounty=identificador_bounty,
                controlador_tasa=controlador,
                db_ruta=db_ruta,
                resolvedor=resolvedor,
                ejecutor_http=ejecutor_http,
            )
            resumen.append({
                "host": host,
                "estado": "ANALIZADO",
                "analisis_id": resultado["analisis_id"],
                "estado_http": resultado["estado_http"],
                "total_observaciones": resultado["total_observaciones"],
                "diferencias": resultado["diferencias"],
            })
        except Exception as error:
            resumen.append({
                "host": host,
                "estado": "OMITIDO",
                "motivo": str(error),
            })

    return resumen


# =====================================
# LABORATORIO OFFLINE (SIN INTERNET)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 41")
    print("ENUMERACION PASIVA Y ESCANEO POR LOTES")
    print("======================================")

    # Simulamos respuesta sucia tipica de crt.sh con subdominios dentro y fuera de alcance
    def ct_simulado(dominio_base):
        return [
            {"common_name": "api.objetivo.com", "name_value": "api.objetivo.com\nauth.objetivo.com"},
            {"common_name": "*.objetivo.com", "name_value": "www.objetivo.com\nadmin@objetivo.com"},
            {"common_name": "api.objetivo.com", "name_value": "api.objetivo.com"},
            {"common_name": "objetivo.com", "name_value": "objetivo.com"},
            {"common_name": "evil.otro.com", "name_value": "evil.otro.com"},
        ]

    def dns_simulado(host, puerto):
        if host == "auth.objetivo.com":
            raise socket.gaierror("Subdominio historico sin registro DNS activo")
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", puerto))
        ]

    def sensor_simulado(ticket, ruta="/", metodo="HEAD", **_kwargs):
        return {
            "host": ticket["host"],
            "ip_conectada": ticket["ip_fijada"],
            "puerto": ticket["puerto"],
            "ruta": ruta,
            "estado_http": 200,
            "bytes_leidos": 0,
            "observaciones": [
                {
                    "clave": f"{ticket['host']}:missing_content-security-policy",
                    "titulo": "Falta Content-Security-Policy (CSP)",
                    "detalle": "El recurso no incluye la cabecera content-security-policy.",
                }
            ],
        }

    with TemporaryDirectory() as temporal:
        db_lab = Path(temporal) / "lotes_lab.db"

        with closing(sqlite3.connect(db_lab)) as con:
            con.execute("PRAGMA foreign_keys = ON")
            con.executescript("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    alcance TEXT NOT NULL,
                    notas TEXT NOT NULL DEFAULT '',
                    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                );
                CREATE TABLE politicas_proyecto (
                    proyecto_id INTEGER PRIMARY KEY,
                    dominios TEXT NOT NULL,
                    puertos TEXT NOT NULL,
                    protocolos TEXT NOT NULL,
                    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE RESTRICT
                );
                CREATE TABLE hallazgos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proyecto_id INTEGER NOT NULL,
                    clave TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    detalle TEXT NOT NULL,
                    fecha TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                    estado TEXT NOT NULL DEFAULT 'Pendiente',
                    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
                    UNIQUE(proyecto_id, clave)
                );
                CREATE TABLE historial_analisis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proyecto_id INTEGER NOT NULL,
                    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    total_observaciones INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE
                );
                CREATE TABLE historial_observaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analisis_id INTEGER NOT NULL,
                    clave TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    detalle TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'Pendiente',
                    FOREIGN KEY (analisis_id) REFERENCES historial_analisis(id) ON DELETE CASCADE
                );
                CREATE TABLE evidencias_http (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proyecto_id INTEGER NOT NULL,
                    contenido TEXT NOT NULL,
                    huella_sha256 TEXT NOT NULL,
                    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
                    UNIQUE (proyecto_id, huella_sha256)
                );
                CREATE TABLE historial_evidencias (
                    analisis_id INTEGER PRIMARY KEY,
                    evidencia_id INTEGER NOT NULL,
                    FOREIGN KEY (analisis_id) REFERENCES historial_analisis(id) ON DELETE CASCADE,
                    FOREIGN KEY (evidencia_id) REFERENCES evidencias_http(id) ON DELETE CASCADE
                );
            """)
            con.execute(
                "INSERT INTO proyectos (id, nombre, alcance) VALUES (?, ?, ?)",
                (1, "Programa Bug Bounty Lotes", "*.objetivo.com"),
            )
            con.execute(
                "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                (1, json.dumps(["*.objetivo.com"]), json.dumps([443]), json.dumps(["https"])),
            )
            con.commit()

        encontrados = descubrir_subdominios_pasivos(
            1, "objetivo.com", db_ruta=db_lab, consultor_ct=ct_simulado
        )
        print("SUBDOMINIOS FILTRADOS EN ALCANCE:", encontrados)

        resultados = analizar_lote_subdominios(
            proyecto_id=1,
            subdominios=encontrados,
            intervalo_segundos=0.2,
            db_ruta=db_lab,
            resolvedor=dns_simulado,
            ejecutor_http=sensor_simulado,
        )

        print("\n--- RESUMEN DEL ESCANEO POR LOTES ---")
        for item in resultados:
            if item["estado"] == "ANALIZADO":
                print(
                    f"[OK]      {item['host']} -> HTTP {item['estado_http']} "
                    f"(Analisis #{item['analisis_id']}, Hallazgos: {item['total_observaciones']})"
                )
            else:
                print(f"[OMITIDO] {item['host']} -> {item['motivo']}")