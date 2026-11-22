import hashlib
import json
import socket
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from base_datos import DB
from gatekeeper_v37 import autorizar_objetivo
from orquestador_bounty_v39 import (
    _abrir_conexion_escritura,
    _comparar_con_anterior,
)
from sensor_http_v38 import (
    ControladorVelocidad,
    _ConexionHTTPFijada,
    _ConexionHTTPSFijada,
    _validar_ruta_http,
    _validar_ticket_autorizacion,
)


# =====================================
# MOONDETEX - CLASE 43
# RECONOCIMIENTO DE SUPERFICIE Y COOKIES
# =====================================

def analizar_cookies_http(host, protocolo, lista_set_cookie):
    """Evalua atributos defensivos HttpOnly, Secure y SameSite en Set-Cookie."""
    observaciones = []

    for cruda in lista_set_cookie:
        if not isinstance(cruda, str) or "=" not in cruda:
            continue

        partes = [p.strip() for p in cruda.split(";") if p.strip()]
        nombre_cookie = partes[0].split("=", 1)[0].strip()
        if not nombre_cookie:
            continue

        atributos = {p.lower() for p in partes[1:]}
        samesite_valores = [
            p.split("=", 1)[1].strip().lower()
            for p in partes[1:]
            if p.lower().startswith("samesite=")
        ]

        if "httponly" not in atributos:
            observaciones.append({
                "clave": f"{host}:cookie_no_httponly:{nombre_cookie}",
                "titulo": f"Cookie sin bandera HttpOnly ({nombre_cookie})",
                "detalle": (
                    f"La cookie '{nombre_cookie}' puede ser leida desde JavaScript "
                    "(impacto ante XSS)."
                ),
            })

        if protocolo == "https" and "secure" not in atributos:
            observaciones.append({
                "clave": f"{host}:cookie_no_secure:{nombre_cookie}",
                "titulo": f"Cookie sin bandera Secure ({nombre_cookie})",
                "detalle": (
                    f"La cookie '{nombre_cookie}' no restringe su envio unicamente "
                    "a conexiones cifradas HTTPS."
                ),
            })

        if not samesite_valores:
            observaciones.append({
                "clave": f"{host}:cookie_no_samesite:{nombre_cookie}",
                "titulo": f"Cookie sin atributo SameSite ({nombre_cookie})",
                "detalle": (
                    f"La cookie '{nombre_cookie}' no define politica SameSite "
                    "contra peticiones entre sitios (CSRF)."
                ),
            })
        elif "none" in samesite_valores and "secure" not in atributos:
            observaciones.append({
                "clave": f"{host}:cookie_samesite_none_insecure:{nombre_cookie}",
                "titulo": f"Cookie con SameSite=None sin Secure ({nombre_cookie})",
                "detalle": (
                    f"La cookie '{nombre_cookie}' usa SameSite=None sin bandera Secure."
                ),
            })

    return observaciones


def analizar_robots_txt(host, estado_http, cuerpo_texto, content_type=""):
    """Extrae rutas Disallow y Sitemap de /robots.txt evitando falsos 200 HTML."""
    if estado_http != 200 or "text/html" in content_type.lower():
        return []

    rutas_disallow = []
    sitemaps = []

    for linea in cuerpo_texto.splitlines():
        limpia = linea.split("#", 1)[0].strip()
        if not limpia or ":" not in limpia:
            continue

        clave, valor = limpia.split(":", 1)
        directiva = clave.strip().lower()
        dato = valor.strip()

        if directiva == "disallow" and dato and dato != "/":
            if dato not in rutas_disallow:
                rutas_disallow.append(dato)
        elif directiva == "sitemap" and dato:
            if dato not in sitemaps:
                sitemaps.append(dato)

    observaciones = []
    if rutas_disallow:
        muestra = ", ".join(rutas_disallow[:12])
        extra = f" (+{len(rutas_disallow) - 12} mas)" if len(rutas_disallow) > 12 else ""
        observaciones.append({
            "clave": f"{host}:robots_disallow_routes",
            "titulo": f"Rutas restringidas detectadas en robots.txt ({len(rutas_disallow)})",
            "detalle": f"Directivas Disallow encontradas: {muestra}{extra}",
        })

    if sitemaps:
        observaciones.append({
            "clave": f"{host}:robots_sitemaps",
            "titulo": f"Sitemaps declarados en robots.txt ({len(sitemaps)})",
            "detalle": f"URLs de mapa del sitio: {', '.join(sitemaps[:5])}",
        })

    return observaciones


def analizar_security_txt(host, estado_http, cuerpo_texto, content_type=""):
    """Verifica la publicacion de /.well-known/security.txt (RFC 9116)."""
    es_texto_plano = "text/html" not in content_type.lower()
    contactos = []
    politicas = []

    if estado_http == 200 and es_texto_plano:
        for linea in cuerpo_texto.splitlines():
            limpia = linea.strip()
            if not limpia or limpia.startswith("#") or ":" not in limpia:
                continue
            clave, valor = limpia.split(":", 1)
            campo = clave.strip().lower()
            dato = valor.strip()
            if campo == "contact" and dato:
                contactos.append(dato)
            elif campo == "policy" and dato:
                politicas.append(dato)

    if contactos or politicas:
        resumen = []
        if contactos:
            resumen.append(f"Contact: {', '.join(contactos[:3])}")
        if politicas:
            resumen.append(f"Policy: {', '.join(politicas[:2])}")
        return [{
            "clave": f"{host}:security_txt_present",
            "titulo": "Archivo security.txt (RFC 9116) publicado",
            "detalle": " | ".join(resumen),
        }]

    return [{
        "clave": f"{host}:missing_security_txt",
        "titulo": "Ausencia de /.well-known/security.txt",
        "detalle": (
            "El dominio no publica un archivo security.txt valido con "
            "canales de contacto para divulgacion responsable."
        ),
    }]


def _leer_recurso_pasivo(
    ticket,
    ruta,
    identificador_bounty="MoonDetex-Research",
    controlador_tasa=None,
    timeout=10,
    max_bytes=32768,
):
    _validar_ticket_autorizacion(ticket)
    _validar_ruta_http(ruta)

    if controlador_tasa is not None:
        controlador_tasa.esperar()

    protocolo = ticket["protocolo"]
    host = ticket["host"]
    puerto = ticket["puerto"]
    ip_fijada = ticket["ip_fijada"]

    if protocolo == "https":
        conexion = _ConexionHTTPSFijada(host, puerto, ip_fijada, timeout=timeout)
    else:
        conexion = _ConexionHTTPFijada(host, puerto, ip_fijada, timeout=timeout)

    cabeceras_envio = {
        "Host": host,
        "User-Agent": "MoonDetex-SurfaceRecon/0.43 (Authorized Bug Bounty Recon)",
        "X-Bug-Bounty": identificador_bounty,
        "Accept": "text/plain,text/html;q=0.9,*/*;q=0.8",
        "Connection": "close",
    }

    try:
        conexion.request("GET", ruta, headers=cabeceras_envio)
        respuesta = conexion.getresponse()
        estado = respuesta.status
        content_type = respuesta.getheader("Content-Type", "")
        cookies = respuesta.headers.get_all("Set-Cookie") or []
        cuerpo = respuesta.read(max_bytes).decode("utf-8", errors="replace")
    finally:
        conexion.close()

    return {
        "ruta": ruta,
        "estado_http": estado,
        "content_type": content_type,
        "cookies": cookies,
        "cuerpo": cuerpo,
    }


def ejecutar_recon_superficie(
    proyecto_id,
    protocolo,
    host,
    puerto,
    identificador_bounty="MoonDetex-Research",
    intervalo_segundos=1.5,
    db_ruta=DB,
    resolvedor=None,
    lector_http=None,
):
    # 1. Validacion obligatoria con Gatekeeper
    ticket = autorizar_objetivo(
        proyecto_id=proyecto_id,
        protocolo=protocolo,
        host=host,
        puerto=puerto,
        db_ruta=db_ruta,
        resolvedor=resolvedor,
    )

    controlador = ControladorVelocidad(intervalo_segundos=intervalo_segundos)
    leer = lector_http if lector_http is not None else _leer_recurso_pasivo

    # 2. Lectura pasiva de 3 puntos estandar
    resp_raiz = leer(
        ticket, "/",
        identificador_bounty=identificador_bounty,
        controlador_tasa=controlador,
    )
    resp_robots = leer(
        ticket, "/robots.txt",
        identificador_bounty=identificador_bounty,
        controlador_tasa=controlador,
    )
    resp_security = leer(
        ticket, "/.well-known/security.txt",
        identificador_bounty=identificador_bounty,
        controlador_tasa=controlador,
    )

    observaciones = []
    observaciones.extend(
        analizar_cookies_http(host, protocolo, resp_raiz["cookies"])
    )
    observaciones.extend(
        analizar_robots_txt(
            host,
            resp_robots["estado_http"],
            resp_robots["cuerpo"],
            resp_robots["content_type"],
        )
    )
    observaciones.extend(
        analizar_security_txt(
            host,
            resp_security["estado_http"],
            resp_security["cuerpo"],
            resp_security["content_type"],
        )
    )

    # 3. Construccion de evidencia forense SHA-256
    evidencia_obj = {
        "tipo": "superficie_estandar_v43",
        "proyecto_id": proyecto_id,
        "protocolo": protocolo,
        "host": host,
        "ip_conectada": ticket["ip_fijada"],
        "puerto": puerto,
        "estados": {
            "/": resp_raiz["estado_http"],
            "/robots.txt": resp_robots["estado_http"],
            "/.well-known/security.txt": resp_security["estado_http"],
        },
        "observaciones": sorted(observaciones, key=lambda x: x["clave"]),
    }
    contenido_evidencia = json.dumps(
        evidencia_obj, ensure_ascii=False, sort_keys=True, indent=2
    )
    huella_sha256 = hashlib.sha256(
        contenido_evidencia.encode("utf-8")
    ).hexdigest()

    # 4. Persistencia atomica en SQLite
    with closing(_abrir_conexion_escritura(db_ruta)) as conexion:
        with conexion:
            conexion.execute(
                """
                INSERT OR IGNORE INTO evidencias_http
                    (proyecto_id, contenido, huella_sha256)
                VALUES (?, ?, ?)
                """,
                (proyecto_id, contenido_evidencia, huella_sha256),
            )
            evidencia_id = conexion.execute(
                """
                SELECT id FROM evidencias_http
                WHERE proyecto_id = ? AND huella_sha256 = ?
                """,
                (proyecto_id, huella_sha256),
            ).fetchone()[0]

            cursor_analisis = conexion.execute(
                """
                INSERT INTO historial_analisis
                    (proyecto_id, total_observaciones)
                VALUES (?, ?)
                """,
                (proyecto_id, len(observaciones)),
            )
            analisis_id = cursor_analisis.lastrowid

            conexion.execute(
                """
                INSERT INTO historial_evidencias
                    (analisis_id, evidencia_id)
                VALUES (?, ?)
                """,
                (analisis_id, evidencia_id),
            )

            for obs in observaciones:
                conexion.execute(
                    """
                    INSERT INTO historial_observaciones
                        (analisis_id, clave, titulo, detalle, estado)
                    VALUES (?, ?, ?, ?, 'Pendiente')
                    """,
                    (analisis_id, obs["clave"], obs["titulo"], obs["detalle"]),
                )
                conexion.execute(
                    """
                    INSERT INTO hallazgos
                        (proyecto_id, clave, titulo, detalle, estado)
                    VALUES (?, ?, ?, ?, 'Pendiente')
                    ON CONFLICT(proyecto_id, clave) DO UPDATE SET
                        titulo = excluded.titulo,
                        detalle = excluded.detalle,
                        fecha = datetime('now', 'localtime')
                    """,
                    (proyecto_id, obs["clave"], obs["titulo"], obs["detalle"]),
                )

            diferencias = _comparar_con_anterior(
                conexion, proyecto_id, analisis_id
            )

    return {
        "analisis_id": analisis_id,
        "ip_conectada": ticket["ip_fijada"],
        "estados": evidencia_obj["estados"],
        "huella_sha256": huella_sha256,
        "total_observaciones": len(observaciones),
        "observaciones": observaciones,
        "diferencias": diferencias,
    }


# =====================================
# LABORATORIO OFFLINE (SIN INTERNET)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 43")
    print("SUPERFICIE ESTANDAR Y COOKIES (LABORATORIO)")
    print("===========================================")

    def dns_simulado(host, puerto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", puerto))
        ]

    def lector_simulado(ticket, ruta, **_kwargs):
        if ruta == "/":
            return {
                "ruta": "/",
                "estado_http": 200,
                "content_type": "text/html; charset=utf-8",
                "cookies": [
                    "session_id=xyz987; Path=/",
                    "__Host-csrf=token123; Path=/; Secure; HttpOnly; SameSite=Strict",
                ],
                "cuerpo": "<html><body>Portal</body></html>",
            }
        if ruta == "/robots.txt":
            return {
                "ruta": "/robots.txt",
                "estado_http": 200,
                "content_type": "text/plain",
                "cookies": [],
                "cuerpo": (
                    "User-agent: *\n"
                    "Disallow: /admin-portal/\n"
                    "Disallow: /api/v1/internal\n"
                    "Sitemap: https://api.objetivo.com/sitemap.xml\n"
                ),
            }
        return {
            "ruta": "/.well-known/security.txt",
            "estado_http": 200,
            "content_type": "text/plain",
            "cookies": [],
            "cuerpo": (
                "Contact: mailto:security@objetivo.com\n"
                "Policy: https://objetivo.com/security-policy\n"
            ),
        }

    with TemporaryDirectory() as temporal:
        db_lab = Path(temporal) / "superficie_lab.db"

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
                (1, "Programa Bug Bounty Superficie", "*.objetivo.com"),
            )
            con.execute(
                "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                (1, '["*.objetivo.com"]', '[443]', '["https"]'),
            )
            con.commit()

        res = ejecutar_recon_superficie(
            proyecto_id=1,
            protocolo="https",
            host="api.objetivo.com",
            puerto=443,
            intervalo_segundos=0.2,
            db_ruta=db_lab,
            resolvedor=dns_simulado,
            lector_http=lector_simulado,
        )

        print(f"Analisis ID: #{res['analisis_id']} | SHA256: {res['huella_sha256'][:16]}...")
        print("Estados HTTP:", res["estados"])
        print(f"\nHallazgos detectados ({res['total_observaciones']}):")
        for obs in res["observaciones"]:
            print(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")

