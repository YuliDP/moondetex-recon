import hashlib
import json
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
from orquestador_bounty_v39 import (
    _abrir_conexion_escritura,
    _comparar_con_anterior,
)
from sensor_http_v38 import ControladorVelocidad, _crear_contexto_ssl


# =====================================
# MOONDETEX - CLASE 45
# AUDITORIA PASIVA DE SEGURIDAD DNS
# (SPF, DMARC Y CAA VIA DOH)
# =====================================

def _consultar_doh_json(nombre_dns, tipo_registro, timeout=12):
    """Consulta registros DNS publicos via DNS-over-HTTPS (Cloudflare JSON)."""
    nombre_q = urllib.parse.quote(nombre_dns)
    tipo_q = urllib.parse.quote(tipo_registro.upper())
    url = f"https://cloudflare-dns.com/dns-query?name={nombre_q}&type={tipo_q}"

    peticion = urllib.request.Request(
        url,
        headers={
            "Accept": "application/dns-json",
            "User-Agent": "MoonDetex-PassiveDNS/0.45",
        },
    )

    contexto_ssl = _crear_contexto_ssl()
    with urllib.request.urlopen(
        peticion, timeout=timeout, context=contexto_ssl
    ) as respuesta:
        cuerpo = respuesta.read().decode("utf-8", errors="replace")

    datos = json.loads(cuerpo)
    if not isinstance(datos, dict):
        raise ValueError("Respuesta DoH invalida.")

    respuestas = datos.get("Answer") or []
    valores = []
    for item in respuestas:
        if isinstance(item, dict) and isinstance(item.get("data"), str):
            valores.append(item["data"].strip())
    return valores


def _limpiar_txt(registro_crudo):
    """Une segmentos entre comillas tipicos de respuestas TXT DNS."""
    texto = registro_crudo.strip()
    if texto.startswith('"') and texto.endswith('"'):
        partes = [p.strip() for p in texto.split('"') if p.strip()]
        return "".join(partes)
    return texto


def evaluar_registros_dns(host, txt_raiz, txt_dmarc, registros_caa):
    """Evalua postura defensiva SPF, DMARC y CAA a partir de registros DNS."""
    observaciones = []

    # 1. Analisis SPF (v=spf1)
    limpios_raiz = [_limpiar_txt(r) for r in txt_raiz]
    spf_lista = [r for r in limpios_raiz if r.lower().startswith("v=spf1")]

    if not spf_lista:
        observaciones.append({
            "clave": f"{host}:dns_missing_spf",
            "titulo": "Ausencia de registro SPF (riesgo de Email Spoofing)",
            "detalle": (
                f"El dominio '{host}' no publica un registro TXT 'v=spf1' "
                "para restringir servidores autorizados a enviar correo."
            ),
        })
    elif len(spf_lista) > 1:
        observaciones.append({
            "clave": f"{host}:dns_multiple_spf",
            "titulo": "Multiples registros SPF detectados (PermError RFC 7208)",
            "detalle": f"Se encontraron {len(spf_lista)} registros v=spf1 simultaneos.",
        })
    else:
        spf = spf_lista[0]
        spf_lower = spf.lower()
        if "+all" in spf_lower:
            observaciones.append({
                "clave": f"{host}:dns_spf_permisivo_plus_all",
                "titulo": "Politica SPF insegura (+all)",
                "detalle": f"El registro SPF permite cualquier remitente (+all): {spf}",
            })
        elif "?all" in spf_lower:
            observaciones.append({
                "clave": f"{host}:dns_spf_neutral",
                "titulo": "Politica SPF neutral (?all)",
                "detalle": f"El registro SPF usa calificador neutral (?all): {spf}",
            })

    # 2. Analisis DMARC (_dmarc.<host>)
    limpios_dmarc = [_limpiar_txt(r) for r in txt_dmarc]
    dmarc_lista = [r for r in limpios_dmarc if r.lower().startswith("v=dmarc1")]

    if not dmarc_lista:
        observaciones.append({
            "clave": f"{host}:dns_missing_dmarc",
            "titulo": "Ausencia de registro DMARC",
            "detalle": (
                f"No existe registro TXT en '_dmarc.{host}' para aplicar "
                "politicas de rechazo o cuarentena ante suplantacion."
            ),
        })
    else:
        dmarc = dmarc_lista[0]
        dmarc_lower = dmarc.replace(" ", "").lower()
        if "p=none" in dmarc_lower:
            observaciones.append({
                "clave": f"{host}:dns_dmarc_policy_none",
                "titulo": "Politica DMARC en modo monitoreo (p=none)",
                "detalle": (
                    f"DMARC esta configurado con 'p=none', por lo que no bloquea "
                    f"correos falsificados: {dmarc}"
                ),
            })

    # 3. Analisis CAA (Certification Authority Authorization)
    if not registros_caa:
        observaciones.append({
            "clave": f"{host}:dns_missing_caa",
            "titulo": "Ausencia de registros DNS CAA",
            "detalle": (
                f"El dominio '{host}' no restringe que autoridades certificadoras (CA) "
                "pueden emitir certificados TLS para su nombre."
            ),
        })

    resumen_dns = {
        "spf": spf_lista[0] if spf_lista else None,
        "dmarc": dmarc_lista[0] if dmarc_lista else None,
        "caa": list(registros_caa),
    }

    return observaciones, resumen_dns


def ejecutar_auditoria_dns(
    proyecto_id,
    host,
    intervalo_segundos=0.8,
    db_ruta=DB,
    consultor_dns=None,
):
    if type(proyecto_id) is not int or proyecto_id <= 0:
        raise ValueError("ID de proyecto invalido.")

    if type(host) is not str or not host.strip():
        raise ValueError("Debes indicar un dominio objetivo valido.")

    dominio = host.strip().lower().rstrip(".")
    validar_dominio_alcance(dominio)

    if not db_ruta.is_file():
        raise FileNotFoundError("No se encontro la base de datos.")

    with closing(
        sqlite3.connect(db_ruta.as_uri() + "?mode=ro", uri=True)
    ) as con_ro:
        con_ro.execute("PRAGMA query_only = ON")
        politica = cargar_politica(con_ro, proyecto_id)

    if politica is None:
        raise ValueError(
            "El proyecto no tiene politica configurada. Auditoria DNS bloqueada."
        )

    if not host_en_alcance(dominio, politica["dominios"]):
        raise ValueError(
            f"El dominio '{dominio}' esta fuera del alcance autorizado."
        )

    controlador = ControladorVelocidad(intervalo_segundos=intervalo_segundos)
    consultar = consultor_dns if consultor_dns is not None else _consultar_doh_json

    controlador.esperar()
    txt_raiz = consultar(dominio, "TXT")

    controlador.esperar()
    txt_dmarc = consultar(f"_dmarc.{dominio}", "TXT")

    controlador.esperar()
    registros_caa = consultar(dominio, "CAA")

    observaciones, resumen_dns = evaluar_registros_dns(
        dominio, txt_raiz, txt_dmarc, registros_caa
    )

    # Evidencia forense SHA-256
    evidencia_obj = {
        "tipo": "auditoria_dns_v45",
        "proyecto_id": proyecto_id,
        "host": dominio,
        "registros_dns": resumen_dns,
        "observaciones": sorted(observaciones, key=lambda x: x["clave"]),
    }
    contenido_evidencia = json.dumps(
        evidencia_obj, ensure_ascii=False, sort_keys=True, indent=2
    )
    huella_sha256 = hashlib.sha256(
        contenido_evidencia.encode("utf-8")
    ).hexdigest()

    # Persistencia en SQLite
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
        "host": dominio,
        "registros_dns": resumen_dns,
        "huella_sha256": huella_sha256,
        "total_observaciones": len(observaciones),
        "observaciones": observaciones,
        "diferencias": diferencias,
    }


# =====================================
# LABORATORIO OFFLINE (SIN INTERNET)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 45")
    print("AUDITORIA PASIVA DE SEGURIDAD DNS (LABORATORIO)")
    print("===============================================")

    def dns_doh_simulado(nombre, tipo):
        if nombre == "objetivo.com" and tipo == "TXT":
            return ['"v=spf1 include:_spf.google.com ?all"']
        if nombre == "_dmarc.objetivo.com" and tipo == "TXT":
            return ['"v=DMARC1; p=none; rua=mailto:dmarc@objetivo.com"']
        if nombre == "objetivo.com" and tipo == "CAA":
            return []
        return []

    with TemporaryDirectory() as temporal:
        db_lab = Path(temporal) / "dns_lab.db"

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
                (1, "Programa Bug Bounty DNS", "objetivo.com, *.objetivo.com"),
            )
            con.execute(
                "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                (1, '["objetivo.com", "*.objetivo.com"]', '[443]', '["https"]'),
            )
            con.commit()

        res = ejecutar_auditoria_dns(
            proyecto_id=1,
            host="objetivo.com",
            intervalo_segundos=0.2,
            db_ruta=db_lab,
            consultor_dns=dns_doh_simulado,
        )

        print(f"Analisis ID: #{res['analisis_id']} | SHA256: {res['huella_sha256'][:16]}...")
        print("Registros leidos:", res["registros_dns"])
        print(f"\nHallazgos detectados ({res['total_observaciones']}):")
        for obs in res["observaciones"]:
            print(f"  - [{obs['clave']}] {obs['titulo']} -> {obs['detalle']}")