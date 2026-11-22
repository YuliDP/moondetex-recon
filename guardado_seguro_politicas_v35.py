import re
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing


# =====================================
# MOONDETEX - CLASE 35 (BLINDADO)
# VALIDACION ANTES DEL GUARDADO
# =====================================

TLDS_BLOQUEADOS = {
    "localhost",
    "local",
    "internal",
    "intranet",
    "lan",
    "home",
    "corp",
    "arpa",
    "onion",
}

PATRON_ETIQUETA = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)


def validar_dominio_alcance(dominio):

    if type(dominio) is not str or not dominio:
        raise ValueError("Dominio invalido.")

    if (
        dominio != dominio.strip()
        or dominio != dominio.lower()
        or len(dominio) > 253
    ):
        raise ValueError("Dominio invalido.")

    # Admitir comodines Bug Bounty unicamente en formato *.dominio.tld
    if dominio.startswith("*."):
        dominio_base = dominio[2:]
    else:
        dominio_base = dominio

    # Rechazar comodines globales (*), parciales (a*.com) o multinivel (*.*.com)
    if "*" in dominio_base:
        raise ValueError("Formato de comodin DNS no permitido.")

    partes = dominio_base.split(".")

    # Exigir al menos dominio + TLD (bloquea 'localhost' y '*.com')
    if len(partes) < 2:
        raise ValueError("Dominio invalido.")

    if not all(PATRON_ETIQUETA.fullmatch(parte) for parte in partes):
        raise ValueError("Dominio invalido.")

    tld = partes[-1]

    # Bloquear direcciones IPv4 disfrazadas de dominio y TLDs internos
    if len(tld) < 2 or tld.isdigit() or tld in TLDS_BLOQUEADOS:
        raise ValueError("TLD no permitido en politica de alcance.")


def validar_politica(proyecto_id, politica):

    if type(proyecto_id) is not int or proyecto_id <= 0:
        raise ValueError("ID de proyecto invalido.")

    if not isinstance(politica, dict):
        raise ValueError("Politica invalida.")

    claves = {"dominios", "puertos", "protocolos"}

    if set(politica) != claves:
        raise ValueError("La politica esta incompleta.")

    for clave in claves:
        valores = politica[clave]

        if (
            not isinstance(valores, (set, list, tuple))
            or not valores
        ):
            raise ValueError(
                f"Configuracion invalida: {clave}"
            )

    # Validar nombres de dominio y comodines autorizados
    for dominio in politica["dominios"]:
        validar_dominio_alcance(dominio)

    # Validar puertos
    for puerto in politica["puertos"]:

        if type(puerto) is not int or not 1 <= puerto <= 65535:
            raise ValueError("Puerto invalido.")

    # Validar protocolos
    for protocolo in politica["protocolos"]:

        if protocolo not in ("http", "https"):
            raise ValueError("Protocolo invalido.")


def guardar_politica_validada(
    conexion, proyecto_id, politica
):
    from laboratorio_politicas_sqlite_v35 import guardar_politica

    validar_politica(proyecto_id, politica)

    # Guardar solo despues de validar todo
    guardar_politica(conexion, proyecto_id, politica)

    return True


# =====================================
# LABORATORIO CON SQLITE TEMPORAL
# =====================================

if __name__ == "__main__":

    from laboratorio_politicas_sqlite_v35 import (
        crear_tablas,
        consultar_politica
    )

    print("\nMOONDETEX - CLASE 35 (BLINDADO)")
    print("GUARDADO VALIDADO DE POLITICAS")
    print("==============================")

    carpeta = Path(__file__).resolve().parent

    with TemporaryDirectory(dir=carpeta) as temporal:

        db = Path(temporal) / "politicas_prueba.db"

        with closing(sqlite3.connect(db)) as conexion:

            conexion.execute("PRAGMA foreign_keys = ON")

            crear_tablas(conexion)

            conexion.execute(
                "INSERT INTO proyectos (id, nombre) VALUES (?, ?)",
                (1, "Laboratorio de prueba")
            )
            conexion.commit()

            correcta = {
                "dominios": {"example.org", "*.example.org"},
                "puertos": {443},
                "protocolos": {"https"}
            }

            casos_invalidos = [
                ("Puerto fuera de rango", {"dominios": {"example.org"}, "puertos": {70000}, "protocolos": {"https"}}),
                ("IPv4 como dominio", {"dominios": {"127.0.0.1"}, "puertos": {443}, "protocolos": {"https"}}),
                ("Comodin de TLD", {"dominios": {"*.com"}, "puertos": {443}, "protocolos": {"https"}}),
                ("Dominio interno", {"dominios": {"panel.local"}, "puertos": {443}, "protocolos": {"https"}}),
            ]

            guardar_politica_validada(
                conexion, 1, correcta
            )

            print("POLITICA CORRECTA: GUARDADA")

            for etiqueta, politica_mala in casos_invalidos:
                try:
                    guardar_politica_validada(
                        conexion, 1, politica_mala
                    )
                except ValueError as error:
                    print(f"RECHAZADA ({etiqueta}): {error}")

            recuperada = consultar_politica(
                conexion, 1
            )

            print("POLITICA CONSERVADA:", recuperada == correcta)

    print("BASE TEMPORAL ELIMINADA")