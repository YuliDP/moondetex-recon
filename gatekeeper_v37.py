import json
import socket
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from adaptador_dns_v34 import extraer_ips_dns
from base_datos import DB
from comparador_dns_v35 import comparar_respuestas_dns
from guardado_seguro_politicas_v35 import validar_dominio_alcance
from lector_politicas_v35 import cargar_politica


# =====================================
# MOONDETEX - CLASE 37
# GATEKEEPER DE ALCANCE Y RED (BUG BOUNTY)
# =====================================

def _resolver_dns_sistema(host, puerto):
    return socket.getaddrinfo(
        host,
        puerto,
        socket.AF_UNSPEC,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
    )


def host_en_alcance(host, dominios_permitidos):
    # El objetivo a analizar debe ser un host concreto, nunca un comodin
    if type(host) is not str or host.startswith("*."):
        raise ValueError("El host objetivo debe ser un dominio concreto.")

    validar_dominio_alcance(host)

    # 1. Coincidencia exacta (ej. 'example.org')
    if host in dominios_permitidos:
        return True

    # 2. Coincidencia con comodin Bug Bounty (ej. '*.example.org')
    for regla in dominios_permitidos:
        if regla.startswith("*."):
            dominio_raiz = regla[2:]
            if host.endswith("." + dominio_raiz):
                return True

    return False


def autorizar_objetivo(
    proyecto_id,
    protocolo,
    host,
    puerto,
    db_ruta=DB,
    resolvedor=None,
):
    if type(proyecto_id) is not int or proyecto_id <= 0:
        raise ValueError("ID de proyecto invalido.")

    if protocolo not in ("http", "https"):
        raise ValueError("Protocolo solicitado no permitido.")

    if type(puerto) is not int or not 1 <= puerto <= 65535:
        raise ValueError("Puerto solicitado invalido.")

    if not db_ruta.is_file():
        raise FileNotFoundError("No se encontro la base de datos.")

    # Abrir la base de datos en modo estrictamente solo lectura
    with closing(
        sqlite3.connect(db_ruta.as_uri() + "?mode=ro", uri=True)
    ) as conexion:
        conexion.execute("PRAGMA query_only = ON")
        politica = cargar_politica(conexion, proyecto_id)

    if politica is None:
        raise ValueError(
            "El proyecto no tiene una politica configurada. Analisis bloqueado."
        )

    # Validar protocolo, puerto y alcance del dominio
    if protocolo not in politica["protocolos"]:
        raise ValueError(
            f"Protocolo '{protocolo}' fuera de la politica del proyecto."
        )

    if puerto not in politica["puertos"]:
        raise ValueError(
            f"Puerto {puerto} fuera de la politica del proyecto."
        )

    if not host_en_alcance(host, politica["dominios"]):
        raise ValueError(
            f"El dominio '{host}' esta fuera del alcance autorizado."
        )

    # Doble resolucion DNS para bloquear IPs privadas y DNS Rebinding
    consultar_dns = resolvedor if resolvedor is not None else _resolver_dns_sistema

    try:
        registros_iniciales = consultar_dns(host, puerto)
        ips_iniciales = extraer_ips_dns(registros_iniciales)

        registros_confirmacion = consultar_dns(host, puerto)
        ips_confirmacion = extraer_ips_dns(registros_confirmacion)
    except socket.gaierror as error:
        raise ValueError(
            f"No se pudo resolver el dominio '{host}'."
        ) from error

    comparar_respuestas_dns(ips_iniciales, ips_confirmacion)

    return {
        "autorizado": True,
        "proyecto_id": proyecto_id,
        "protocolo": protocolo,
        "host": host,
        "puerto": puerto,
        "ips_aprobadas": ips_iniciales,
        "ip_fijada": ips_iniciales[0],
    }


# =====================================
# LABORATORIO OFFLINE (SIN INTERNET)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 37")
    print("GATEKEEPER DE ALCANCE BUG BOUNTY")
    print("==================================")

    # Simulador DNS local para probar sin salida a internet
    respuestas_simuladas = {
        "api.objetivo.com": [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ],
        "dev.api.objetivo.com": [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ],
        "objetivo.com": [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ],
        "objetivo.com.atacante.com": [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ],
        "interno.objetivo.com": [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))
        ],
    }

    def resolvedor_laboratorio(host, puerto):
        if host not in respuestas_simuladas:
            raise socket.gaierror("Dominio no encontrado en laboratorio")
        return respuestas_simuladas[host]

    with TemporaryDirectory() as temporal:
        db_prueba = Path(temporal) / "gatekeeper_lab.db"

        with closing(sqlite3.connect(db_prueba)) as conexion:
            conexion.execute("PRAGMA foreign_keys = ON")
            conexion.execute("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL
                )
            """)
            conexion.execute("""
                CREATE TABLE politicas_proyecto (
                    proyecto_id INTEGER PRIMARY KEY,
                    dominios TEXT NOT NULL,
                    puertos TEXT NOT NULL,
                    protocolos TEXT NOT NULL,
                    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
                )
            """)
            conexion.execute(
                "INSERT INTO proyectos VALUES (?, ?)",
                (1, "Programa Bug Bounty Wildcard"),
            )
            # Solo autorizamos subdominios (*.objetivo.com), NO el dominio raiz
            conexion.execute(
                "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                (
                    1,
                    json.dumps(["*.objetivo.com"]),
                    json.dumps([443]),
                    json.dumps(["https"]),
                ),
            )
            conexion.commit()

        pruebas = [
            ("Subdominio valido", ("https", "api.objetivo.com", 443)),
            ("Subdominio multinivel", ("https", "dev.api.objetivo.com", 443)),
            ("Dominio raiz no listado", ("https", "objetivo.com", 443)),
            ("Dominio trampa externo", ("https", "objetivo.com.atacante.com", 443)),
            ("Puerto no autorizado", ("https", "api.objetivo.com", 8443)),
            ("Subdominio apuntando a localhost", ("https", "interno.objetivo.com", 443)),
        ]

        for etiqueta, (proto, host, puerto) in pruebas:
            try:
                ticket = autorizar_objetivo(
                    1,
                    proto,
                    host,
                    puerto,
                    db_ruta=db_prueba,
                    resolvedor=resolvedor_laboratorio,
                )
                print(f"AUTORIZADO ({etiqueta}): {host} -> IP fijada {ticket['ip_fijada']}")
            except ValueError as error:
                print(f"BLOQUEADO  ({etiqueta}): {error}")

    print("\nLABORATORIO FINALIZADO (SIN SALIDA A INTERNET)")