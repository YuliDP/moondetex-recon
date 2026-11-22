import hashlib
import json
import socket
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from base_datos import DB
from gatekeeper_v37 import autorizar_objetivo
from sensor_http_v38 import analizar_cabeceras_http, consultar_http_seguro


# =====================================
# MOONDETEX - CLASE 39
# ORQUESTADOR DE RECONOCIMIENTO Y PERSISTENCIA
# =====================================

def _abrir_conexion_escritura(db_ruta):
    if not db_ruta.is_file():
        raise FileNotFoundError(f"No se encontro la base de datos: {db_ruta}")

    conexion = sqlite3.connect(db_ruta)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _construir_evidencia_forense(ticket, resultado_http):
    registro = {
        "proyecto_id": ticket["proyecto_id"],
        "protocolo": ticket["protocolo"],
        "host": resultado_http["host"],
        "ip_conectada": resultado_http["ip_conectada"],
        "puerto": resultado_http["puerto"],
        "ruta": resultado_http["ruta"],
        "estado_http": resultado_http["estado_http"],
        "bytes_leidos": resultado_http["bytes_leidos"],
        "observaciones": sorted(
            resultado_http["observaciones"],
            key=lambda item: item["clave"],
        ),
    }
    contenido = json.dumps(registro, ensure_ascii=False, sort_keys=True, indent=2)
    huella_sha256 = hashlib.sha256(contenido.encode("utf-8")).hexdigest()
    return contenido, huella_sha256


def _comparar_con_anterior(conexion, proyecto_id, analisis_actual_id):
    previo = conexion.execute(
        """
        SELECT id FROM historial_analisis
        WHERE proyecto_id = ? AND id < ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (proyecto_id, analisis_actual_id),
    ).fetchone()

    if previo is None:
        return None

    id_anterior = previo[0]

    def cargar_mapa(analisis_id):
        filas = conexion.execute(
            """
            SELECT clave, titulo, detalle
            FROM historial_observaciones
            WHERE analisis_id = ?
            """,
            (analisis_id,),
        ).fetchall()
        return {clave: (titulo, detalle) for clave, titulo, detalle in filas}

    anterior = cargar_mapa(id_anterior)
    actual = cargar_mapa(analisis_actual_id)

    claves_ant = set(anterior)
    claves_act = set(actual)

    nuevas = sorted(claves_act - claves_ant)
    ausentes = sorted(claves_ant - claves_act)
    cambiadas = sorted(
        clave for clave in (claves_act & claves_ant)
        if anterior[clave] != actual[clave]
    )

    return {
        "analisis_anterior_id": id_anterior,
        "nuevas": nuevas,
        "cambiadas": cambiadas,
        "ausentes": ausentes,
    }


def ejecutar_analisis_bounty(
    proyecto_id,
    protocolo,
    host,
    puerto,
    ruta="/",
    metodo="HEAD",
    identificador_bounty="MoonDetex-Research",
    controlador_tasa=None,
    db_ruta=DB,
    resolvedor=None,
    ejecutor_http=None,
):
    # 1. Validacion estricta de alcance y DNS antes de tocar la red
    ticket = autorizar_objetivo(
        proyecto_id=proyecto_id,
        protocolo=protocolo,
        host=host,
        puerto=puerto,
        db_ruta=db_ruta,
        resolvedor=resolvedor,
    )

    # 2. Consulta pasiva controlada mediante IP fijada
    consultar = ejecutor_http if ejecutor_http is not None else consultar_http_seguro
    resultado_http = consultar(
        ticket=ticket,
        ruta=ruta,
        metodo=metodo,
        identificador_bounty=identificador_bounty,
        controlador_tasa=controlador_tasa,
    )

    observaciones = resultado_http["observaciones"]
    contenido_evidencia, huella_sha256 = _construir_evidencia_forense(
        ticket, resultado_http
    )

    # 3. Persistencia atomica en SQLite
    with closing(_abrir_conexion_escritura(db_ruta)) as conexion:
        with conexion:
            # Guardar evidencia HTTP evitando duplicados por SHA-256
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

            # Registrar ejecucion en historial_analisis
            cursor_analisis = conexion.execute(
                """
                INSERT INTO historial_analisis
                    (proyecto_id, total_observaciones)
                VALUES (?, ?)
                """,
                (proyecto_id, len(observaciones)),
            )
            analisis_id = cursor_analisis.lastrowid

            # Vincular analisis con su evidencia forense
            conexion.execute(
                """
                INSERT INTO historial_evidencias
                    (analisis_id, evidencia_id)
                VALUES (?, ?)
                """,
                (analisis_id, evidencia_id),
            )

            # Guardar observaciones del analisis y actualizar tabla maestra hallazgos
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
        "evidencia_id": evidencia_id,
        "huella_sha256": huella_sha256,
        "ip_conectada": resultado_http["ip_conectada"],
        "estado_http": resultado_http["estado_http"],
        "total_observaciones": len(observaciones),
        "diferencias": diferencias,
    }


# =====================================
# LABORATORIO OFFLINE (2 ESCANEOS CONSECUTIVOS)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 39")
    print("ORQUESTADOR END-TO-END (LABORATORIO OFFLINE)")
    print("============================================")

    def dns_simulado(host, puerto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", puerto))
        ]

    # Simulamos dos momentos distintos en el tiempo para ver como detecta cambios
    escaneo_numero = {"turno": 0}

    def sensor_simulado(ticket, ruta="/", metodo="HEAD", **_kwargs):
        escaneo_numero["turno"] += 1
        if escaneo_numero["turno"] == 1:
            cabeceras = {"Server": "nginx/1.24.0"}
        else:
            # En el segundo escaneo aparece una cabecera expuesta nueva (X-Powered-By)
            cabeceras = {
                "Server": "nginx/1.24.0",
                "X-Powered-By": "Express",
                "X-Content-Type-Options": "nosniff",
            }

        obs = analizar_cabeceras_http(
            ticket["host"], ticket["protocolo"], 200, cabeceras
        )
        return {
            "host": ticket["host"],
            "ip_conectada": ticket["ip_fijada"],
            "puerto": ticket["puerto"],
            "ruta": ruta,
            "estado_http": 200,
            "bytes_leidos": 0,
            "observaciones": obs,
        }

    with TemporaryDirectory() as temporal:
        db_lab = Path(temporal) / "orquestador_lab.db"

        # Crear esquema identico a moondetex.db
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
                (1, "Programa Bug Bounty Demo", "*.objetivo.com"),
            )
            con.execute(
                "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                (1, json.dumps(["*.objetivo.com"]), json.dumps([443]), json.dumps(["https"])),
            )
            con.commit()

        # Escaneo 1
        r1 = ejecutar_analisis_bounty(
            1, "https", "api.objetivo.com", 443,
            db_ruta=db_lab, resolvedor=dns_simulado, ejecutor_http=sensor_simulado
        )
        print(f"ESCANEO #1 -> Analisis ID: {r1['analisis_id']} | Hallazgos: {r1['total_observaciones']} | SHA256: {r1['huella_sha256'][:16]}...")

        # Escaneo 2 (detecta cambios respecto al Escaneo 1)
        r2 = ejecutar_analisis_bounty(
            1, "https", "api.objetivo.com", 443,
            db_ruta=db_lab, resolvedor=dns_simulado, ejecutor_http=sensor_simulado
        )
        print(f"ESCANEO #2 -> Analisis ID: {r2['analisis_id']} | Hallazgos: {r2['total_observaciones']} | SHA256: {r2['huella_sha256'][:16]}...")
        print("DIFERENCIAS DETECTADAS:", r2["diferencias"])

        # Intento fuera de alcance
        try:
            ejecutar_analisis_bounty(
                1, "https", "otrodominio.com", 443,
                db_ruta=db_lab, resolvedor=dns_simulado, ejecutor_http=sensor_simulado
            )
        except ValueError as error:
            print("INTENTO FUERA DE ALCANCE:", error)