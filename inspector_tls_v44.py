import hashlib
import json
import socket
import sqlite3
import ssl
import time
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from base_datos import DB
from gatekeeper_v37 import autorizar_objetivo, host_en_alcance
from guardado_seguro_politicas_v35 import validar_dominio_alcance
from lector_politicas_v35 import cargar_politica
from orquestador_bounty_v39 import (
    _abrir_conexion_escritura,
    _comparar_con_anterior,
)
from sensor_http_v38 import ControladorVelocidad, _crear_contexto_ssl


# =====================================
# MOONDETEX - CLASE 44
# INSPECTOR PASIVO DE CERTIFICADOS TLS
# =====================================

def _extraer_campo_x509(tupla_rdn, clave_buscada="commonName"):
    if not tupla_rdn:
        return ""
    for rdn in tupla_rdn:
        for clave, valor in rdn:
            if clave == clave_buscada:
                return valor
    return ""


def analizar_certificado_tls(
    host,
    info_tls,
    dominios_permitidos=None,
    timestamp_actual=None,
):
    """Evalua version TLS, validez temporal y SANs en alcance de un certificado."""
    observaciones = []
    version_tls = info_tls.get("version_tls") or "Desconocida"
    cert = info_tls.get("certificado") or {}
    error_verif = info_tls.get("error_verificacion")

    # 1. Certificado no confiable / error de cadena
    if error_verif:
        observaciones.append({
            "clave": f"{host}:tls_verification_failed",
            "titulo": "Certificado TLS no confiable o invalido",
            "detalle": f"Fallo de validacion TLS: {error_verif}",
        })

    # 2. Protocolos TLS obsoletos
    if version_tls in ("SSLv2", "SSLv3", "TLSv1", "TLSv1.1"):
        observaciones.append({
            "clave": f"{host}:tls_weak_protocol",
            "titulo": f"Protocolo TLS obsoleto negociado ({version_tls})",
            "detalle": (
                f"El servidor negocio {version_tls}, considerado inseguro "
                "frente a TLS 1.2 o TLS 1.3."
            ),
        })

    # 3. Vigencia temporal (notAfter)
    not_after = cert.get("notAfter")
    if isinstance(not_after, str) and not_after:
        ahora = time.time() if timestamp_actual is None else float(timestamp_actual)
        expiracion_ts = ssl.cert_time_to_seconds(not_after)
        dias_restantes = int((expiracion_ts - ahora) // 86400)

        if dias_restantes < 0:
            observaciones.append({
                "clave": f"{host}:tls_cert_expired",
                "titulo": "Certificado TLS expirado",
                "detalle": f"El certificado vencio hace {abs(dias_restantes)} dias ({not_after}).",
            })
        elif dias_restantes <= 30:
            observaciones.append({
                "clave": f"{host}:tls_cert_expiring_soon",
                "titulo": f"Certificado TLS proximo a expirar ({dias_restantes} dias)",
                "detalle": f"Fecha de expiracion declarada: {not_after}",
            })

    # 4. Extraccion y filtrado de Subject Alternative Names (SAN)
    sans_crudos = cert.get("subjectAltName") or ()
    sans_dns = sorted({
        valor.strip().lower().rstrip(".")
        for tipo, valor in sans_crudos
        if tipo == "DNS" and isinstance(valor, str) and valor.strip()
    })

    sans_en_alcance = []
    sans_fuera_alcance = []

    for san in sans_dns:
        if san == host:
            continue
        if dominios_permitidos:
            try:
                validar_dominio_alcance(san)
                if host_en_alcance(san, dominios_permitidos):
                    sans_en_alcance.append(san)
                else:
                    sans_fuera_alcance.append(san)
            except ValueError:
                sans_fuera_alcance.append(san)
        else:
            sans_en_alcance.append(san)

    if sans_en_alcance:
        muestra = ", ".join(sans_en_alcance[:12])
        extra = f" (+{len(sans_en_alcance) - 12} mas)" if len(sans_en_alcance) > 12 else ""
        observaciones.append({
            "clave": f"{host}:tls_san_in_scope",
            "titulo": f"Subdominios adicionales en alcance via SAN ({len(sans_en_alcance)})",
            "detalle": (
                f"SANs autorizados en el certificado: {muestra}{extra} "
                f"(fuera de alcance omitidos: {len(sans_fuera_alcance)})"
            ),
        })

    emisor = _extraer_campo_x509(cert.get("issuer"), "organizationName") or _extraer_campo_x509(
        cert.get("issuer"), "commonName"
    )
    sujeto = _extraer_campo_x509(cert.get("subject"), "commonName")

    resumen_cert = {
        "version_tls": version_tls,
        "cifrado": info_tls.get("cifrado"),
        "sujeto_cn": sujeto,
        "emisor": emisor,
        "expira": not_after or "Desconocida",
        "sans_en_alcance": sans_en_alcance,
        "sans_fuera_alcance_total": len(sans_fuera_alcance),
    }

    return observaciones, resumen_cert


def _inspeccionar_tls_remoto(ticket, controlador_tasa=None, timeout=10):
    if controlador_tasa is not None:
        controlador_tasa.esperar()

    host = ticket["host"]
    puerto = ticket["puerto"]
    ip_fijada = ticket["ip_fijada"]

    contexto_estricto = _crear_contexto_ssl()
    error_verificacion = None

    try:
        sock = socket.create_connection((ip_fijada, puerto), timeout=timeout)
        with closing(
            contexto_estricto.wrap_socket(sock, server_hostname=host)
        ) as tls_sock:
            return {
                "version_tls": tls_sock.version(),
                "cifrado": tls_sock.cipher(),
                "certificado": tls_sock.getpeercert(),
                "error_verificacion": None,
            }
    except ssl.SSLCertVerificationError as error:
        error_verificacion = str(error)

    # Si fallo la verificacion, leer metadatos sin validar cadena para reportar el motivo
    contexto_lectura = ssl._create_unverified_context()
    sock = socket.create_connection((ip_fijada, puerto), timeout=timeout)
    with closing(
        contexto_lectura.wrap_socket(sock, server_hostname=host)
    ) as tls_sock:
        return {
            "version_tls": tls_sock.version(),
            "cifrado": tls_sock.cipher(),
            "certificado": tls_sock.getpeercert(),
            "error_verificacion": error_verificacion,
        }


def ejecutar_inspeccion_tls(
    proyecto_id,
    host,
    puerto=443,
    intervalo_segundos=1.5,
    db_ruta=DB,
    resolvedor=None,
    inspector_tls=None,
):
    # 1. Validacion obligatoria con Gatekeeper en modo HTTPS
    ticket = autorizar_objetivo(
        proyecto_id=proyecto_id,
        protocolo="https",
        host=host,
        puerto=puerto,
        db_ruta=db_ruta,
        resolvedor=resolvedor,
    )

    with closing(
        sqlite3.connect(db_ruta.as_uri() + "?mode=ro", uri=True)
    ) as con_ro:
        con_ro.execute("PRAGMA query_only = ON")
        politica = cargar_politica(con_ro, proyecto_id)

    dominios_permitidos = politica["dominios"] if politica else set()

    controlador = ControladorVelocidad(intervalo_segundos=intervalo_segundos)
    inspeccionar = (
        inspector_tls if inspector_tls is not None else _inspeccionar_tls_remoto
    )

    info_tls = inspeccionar(ticket, controlador_tasa=controlador)
    observaciones, resumen_cert = analizar_certificado_tls(
        host=host,
        info_tls=info_tls,
        dominios_permitidos=dominios_permitidos,
    )

    # 2. Evidencia forense SHA-256
    evidencia_obj = {
        "tipo": "inspeccion_tls_v44",
        "proyecto_id": proyecto_id,
        "host": host,
        "ip_conectada": ticket["ip_fijada"],
        "puerto": puerto,
        "resumen_certificado": resumen_cert,
        "observaciones": sorted(observaciones, key=lambda x: x["clave"]),
    }
    contenido_evidencia = json.dumps(
        evidencia_obj, ensure_ascii=False, sort_keys=True, indent=2
    )
    huella_sha256 = hashlib.sha256(
        contenido_evidencia.encode("utf-8")
    ).hexdigest()

    # 3. Persistencia en SQLite
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
        "resumen_certificado": resumen_cert,
        "huella_sha256": huella_sha256,
        "total_observaciones": len(observaciones),
        "observaciones": observaciones,
        "diferencias": diferencias,
    }


# =====================================
# LABORATORIO OFFLINE (SIN INTERNET)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 44")
    print("INSPECTOR PASIVO DE CERTIFICADOS TLS (LABORATORIO)")
    print("==================================================")

    def dns_simulado(host, puerto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", puerto))
        ]

    # Simular un certificado que vence en 12 dias y comparte SANs dentro y fuera de alcance
    fecha_proxima = time.strftime(
        "%b %d %H:%M:%S %Y GMT",
        time.gmtime(time.time() + 12 * 86400),
    )

    def tls_simulado(ticket, **_kwargs):
        return {
            "version_tls": "TLSv1.3",
            "cifrado": ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256),
            "error_verificacion": None,
            "certificado": {
                "subject": ((("commonName", "api.objetivo.com"),),),
                "issuer": ((("organizationName", "Let's Encrypt"),),),
                "notAfter": fecha_proxima,
                "subjectAltName": (
                    ("DNS", "api.objetivo.com"),
                    ("DNS", "staging.objetivo.com"),
                    ("DNS", "portal-interno.objetivo.com"),
                    ("DNS", "cdn-compartido.proveedor.net"),
                ),
            },
        }

    with TemporaryDirectory() as temporal:
        db_lab = Path(temporal) / "tls_lab.db"

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
                (1, "Programa Bug Bounty TLS", "*.objetivo.com"),
            )
            con.execute(
                "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                (1, '["*.objetivo.com"]', '[443]', '["https"]'),
            )
            con.commit()

        res = ejecutar_inspeccion_tls(
            proyecto_id=1,
            host="api.objetivo.com",
            puerto=443,
            intervalo_segundos=0.2,
            db_ruta=db_lab,
            resolvedor=dns_simulado,
            inspector_tls=tls_simulado,
        )

        cert_info = res["resumen_certificado"]
        print(f"Analisis ID: #{res['analisis_id']} | SHA256: {res['huella_sha256'][:16]}...")
        print(f"Protocolo:   {cert_info['version_tls']} | Emisor: {cert_info['emisor']}")
        print(f"SANs en alcance: {cert_info['sans_en_alcance']} (omitidos fuera de alcance: {cert_info['sans_fuera_alcance_total']})")
        print(f"\nHallazgos detectados ({res['total_observaciones']}):")
        for obs in res["observaciones"]:
            print(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")