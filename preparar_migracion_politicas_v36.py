"""Preparador de ensayos con origen explicito y destinos nuevos.

El modo ficticio exige siete nombres explicitos. --ensayar-origen-real lee
el origen con mode=ro y query_only=ON y descubre sus siete tablas.
Ambos requieren una carpeta NUEVA. El modo real conserva respaldo, copia,
recuperacion e informe. Mantener el origen cerrado a escritores al ensayar.
"""

import argparse
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory

from respaldo_sqlite_v26 import crear_respaldo
from simular_restauracion_v27 import calcular_hash, revisar_base
from migracion_politicas_v36 import (
    migrar_politicas, obtener_manifiesto, verificar_conservacion,
    verificar_integridad, ESQUEMA_POLITICAS,
)


def _ruta_ficticia(archivo):
    ruta = Path(archivo).resolve()
    real = Path(__file__).resolve().parent / "moondetex.db"
    if (ruta.name.lower() == "moondetex.db" or ruta == real
            or (ruta.exists() and real.exists() and ruta.samefile(real))):
        raise ValueError("moondetex.db esta excluida de esta fase.")
    if not ruta.is_file():
        raise FileNotFoundError(ruta)
    return ruta


def _manifestar_archivo(ruta):
    # Reutilizar el verificador de restauracion, reforzado con todos los
    # resultados de integrity_check y las huellas completas del contenido.
    revisar_base(ruta)
    with closing(sqlite3.connect(ruta.as_uri() + "?mode=ro", uri=True)) as con:
        con.execute("PRAGMA query_only = ON")
        con.execute("BEGIN")
        verificar_integridad(con)
        return obtener_manifiesto(con)


def _exigir_rutas_distintas(*rutas):
    resueltas = [Path(ruta).resolve() for ruta in rutas]
    for indice, ruta in enumerate(resueltas):
        for otra in resueltas[:indice]:
            if ruta == otra or (ruta.exists() and otra.exists() and ruta.samefile(otra)):
                raise ValueError("El origen, respaldo y copias deben ser distintos.")


def _abrir_lectura(ruta):
    conexion = sqlite3.connect(Path(ruta).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        conexion.execute("PRAGMA query_only = ON")
        return conexion
    except BaseException:
        conexion.close()
        raise


def preparar_ensayo_origen_real(origen, carpeta_trabajo):
    """Leer un origen explicito y migrar exclusivamente copia_trabajo.db.

    Mantener la aplicacion cerrada durante el ensayo. La conexion observadora
    usa data_version para detectar commits concurrentes, incluso cambios luego
    deshechos por otro escritor. El respaldo y manifiesto nacen de una misma
    transaccion de lectura. No existe una opcion de migracion del origen.
    """
    origen = Path(origen).resolve()
    if not origen.is_file():
        raise FileNotFoundError(origen)
    trabajo = Path(carpeta_trabajo).resolve()
    respaldo = trabajo / "respaldo_previo.db"
    copia = trabajo / "copia_trabajo.db"
    recuperada = trabajo / "recuperacion_prueba.db"
    _exigir_rutas_distintas(origen, trabajo, respaldo, copia, recuperada)
    trabajo.mkdir(parents=True, exist_ok=False)
    informe = {
        "resultado": "ENSAYO_EN_CURSO", "seguro_continuar": False,
        "origen": str(origen), "respaldo": str(respaldo),
        "copia_trabajo": str(copia), "recuperacion": str(recuperada),
        "comprobaciones": {}, "errores": [],
    }
    etapas = ("rutas", "origen", "respaldo_consistente", "comparacion_respaldo",
              "copia_trabajo", "migracion", "esquema_y_conservacion",
              "recuperacion", "origen_estable", "respaldo_intacto")
    informe["comprobaciones"] = {nombre: "PENDIENTE" for nombre in etapas}
    etapa = "rutas"

    def guardar_informe():
        with (trabajo / "informe_ensayo.json").open("w", encoding="utf-8") as archivo:
            json.dump(informe, archivo, ensure_ascii=False, indent=2)

    def aprobar(nombre):
        informe["comprobaciones"][nombre] = "APROBADA"
        guardar_informe()

    try:
        aprobar("rutas")
        etapa = "origen"
        with closing(_abrir_lectura(origen)) as fuente:
            version = fuente.execute("PRAGMA data_version").fetchone()[0]
            fuente.execute("BEGIN")
            verificar_integridad(fuente)
            antes = obtener_manifiesto(fuente)
            nombres = tuple(antes["tablas"])
            if (len(nombres) != 7 or "politicas_proyecto" in nombres
                    or not {"proyectos", "hallazgos", "historial_analisis"}.issubset(nombres)):
                raise ValueError("Se requieren las siete tablas originales sin politicas.")
            informe["tablas_originales"] = nombres
            informe["manifiesto_original"] = antes
            aprobar("origen")
            etapa = "respaldo_consistente"
            _exigir_rutas_distintas(origen, respaldo, copia, recuperada)
            # Reservar exclusivamente un archivo nuevo. backup usa la misma
            # conexion y snapshot que produjo el manifiesto del origen.
            with respaldo.open("xb"):
                pass
            with closing(sqlite3.connect(respaldo.as_uri() + "?mode=rw", uri=True)) as destino:
                fuente.backup(destino)
            fuente.execute("ROLLBACK")
            sha256 = calcular_hash(respaldo)
            informe["sha256_respaldo"] = sha256
            aprobar("respaldo_consistente")
            etapa = "comparacion_respaldo"
            if _manifestar_archivo(respaldo) != antes:
                raise RuntimeError("El respaldo y el manifiesto difieren.")
            if fuente.execute("PRAGMA data_version").fetchone()[0] != version:
                raise RuntimeError("Cambios concurrentes en el origen.")
            aprobar("comparacion_respaldo")
            etapa = "copia_trabajo"
            recuperar_respaldo_ficticio(respaldo, copia, manifiesto=antes, sha256=sha256)
            _exigir_rutas_distintas(origen, respaldo, copia, recuperada)
            aprobar("copia_trabajo")
            etapa = "migracion"
            with closing(sqlite3.connect(copia.as_uri() + "?mode=rw", uri=True)) as con:
                migrar_politicas(con, tablas_originales=nombres)
            aprobar("migracion")
            etapa = "esquema_y_conservacion"
            with closing(_abrir_lectura(copia)) as con:
                con.execute("BEGIN")
                verificar_conservacion(con, antes)
                verificar_integridad(con)
                columnas = con.execute("PRAGMA table_info(politicas_proyecto)").fetchall()
                relaciones = con.execute("PRAGMA foreign_key_list(politicas_proyecto)").fetchall()
                if (len(relaciones) != 1 or relaciones[0][2:5] != ("proyectos", "proyecto_id", "id")
                        or relaciones[0][6] != "RESTRICT"):
                    raise RuntimeError("Restricciones de politicas incompatibles.")
                informe["politicas_proyecto"] = {
                    "cantidad": con.execute("SELECT COUNT(*) FROM politicas_proyecto").fetchone()[0],
                    "columnas": columnas, "claves_foraneas": relaciones,
                    "esquema_esperado": ESQUEMA_POLITICAS,
                }
            aprobar("esquema_y_conservacion")
            etapa = "recuperacion"
            recuperar_respaldo_ficticio(respaldo, recuperada, manifiesto=antes, sha256=sha256)
            _exigir_rutas_distintas(origen, respaldo, copia, recuperada)
            aprobar("recuperacion")
            etapa = "origen_estable"
            fuente.execute("BEGIN")
            verificar_integridad(fuente)
            actual = obtener_manifiesto(fuente)
            fuente.execute("ROLLBACK")
            if (actual != antes
                    or fuente.execute("PRAGMA data_version").fetchone()[0] != version):
                raise RuntimeError("Cambios concurrentes en el origen durante el ensayo.")
            aprobar("origen_estable")
            etapa = "respaldo_intacto"
            if calcular_hash(respaldo) != sha256:
                raise RuntimeError("El respaldo fue alterado.")
            aprobar("respaldo_intacto")
        informe["resultado"] = "ENSAYO_APROBADO"
        informe["seguro_continuar"] = True
        guardar_informe()
        return informe
    except BaseException as error:
        informe["resultado"] = "ENSAYO_RECHAZADO"
        informe["seguro_continuar"] = False
        informe["comprobaciones"][etapa] = "FALLIDA"
        informe["errores"].append({"etapa": etapa, "tipo": type(error).__name__, "detalle": str(error)})
        try:
            guardar_informe()
        except OSError as error_informe:
            raise RuntimeError(f"Fallo del ensayo: {error}. No se pudo guardar el informe: {error_informe}") from error
        raise


def recuperar_respaldo_ficticio(respaldo, destino, *, manifiesto, sha256):
    """Recuperar a un archivo NUEVO; jamas sobrescribir ni restaurar en vivo."""
    respaldo = _ruta_ficticia(respaldo)
    destino = Path(destino).resolve()
    _exigir_rutas_distintas(respaldo, destino)
    if destino.name.lower() == "moondetex.db":
        raise ValueError("No se permite restaurar la base real.")
    if calcular_hash(respaldo) != sha256:
        raise RuntimeError("El respaldo no coincide con el SHA-256 registrado.")
    if _manifestar_archivo(respaldo) != manifiesto:
        raise RuntimeError("El contenido del respaldo no coincide.")
    # xb impide sobreescrituras incluso si el destino aparece entre pasos.
    with respaldo.open("rb") as fuente, destino.open("xb") as copia:
        shutil.copyfileobj(fuente, copia)
    if calcular_hash(destino) != sha256:
        raise RuntimeError("La copia recuperada no coincide.")
    if _manifestar_archivo(destino) != manifiesto:
        raise RuntimeError("La recuperacion no conserva el manifiesto.")
    if calcular_hash(respaldo) != sha256:
        raise RuntimeError("El respaldo cambio durante la recuperacion.")
    return destino


def preparar_ensayo(origen, carpeta_trabajo, *, tablas_originales):
    """Respaldar y ensayar SOLO una base ficticia explicitamente indicada.

El origen debe permanecer cerrado y sin escritores durante toda la operacion.
Una carpeta existente se rechaza, incluso si esta vacia. Ante fallo se conservan
los artefactos para diagnostico; no se anuncia aprobacion ni se toca el origen.
"""
    origen = _ruta_ficticia(origen)
    nombres = tuple(tablas_originales)
    huella_origen = calcular_hash(origen)
    antes = _manifestar_archivo(origen)
    if len(nombres) != 7 or len(set(nombres)) != 7 or set(antes["tablas"]) != set(nombres):
        raise ValueError("Indica las siete tablas originales exactas.")
    trabajo = Path(carpeta_trabajo).resolve()
    trabajo.mkdir(parents=True, exist_ok=False)
    respaldo = crear_respaldo(origen, trabajo / "respaldos")
    sha256 = calcular_hash(respaldo)
    if _manifestar_archivo(respaldo) != antes:
        raise RuntimeError("El respaldo no conserva el origen.")
    with TemporaryDirectory(prefix="ensayo_v36_", dir=trabajo) as temporal:
        carpeta = Path(temporal)
        ensayo = recuperar_respaldo_ficticio(
            respaldo, carpeta / "ensayo.db", manifiesto=antes, sha256=sha256,
        )
        with closing(sqlite3.connect(ensayo.as_uri() + "?mode=rw", uri=True)) as con:
            migrar_politicas(con, tablas_originales=nombres)
        # Comprobar persistencia despues del cierre y COMMIT.
        with closing(sqlite3.connect(ensayo.as_uri() + "?mode=ro", uri=True)) as con:
            verificar_conservacion(con, antes)
            verificar_integridad(con)
        recuperar_respaldo_ficticio(
            respaldo, carpeta / "recuperada.db", manifiesto=antes, sha256=sha256,
        )
    if calcular_hash(respaldo) != sha256 or calcular_hash(origen) != huella_origen:
        raise RuntimeError("El origen o respaldo cambio durante el ensayo.")
    if _manifestar_archivo(origen) != antes:
        raise RuntimeError("El origen cambio durante el ensayo.")
    informe = {"resultado": "ENSAYO_APROBADO", "origen": str(origen),
               "respaldo": str(respaldo), "sha256_respaldo": sha256,
               "manifiesto_original": antes, "tablas_originales": nombres}
    with (trabajo / "manifiesto.json").open("x", encoding="utf-8") as archivo:
        json.dump(informe, archivo, ensure_ascii=False, indent=2)
    return informe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modos = parser.add_mutually_exclusive_group(required=True)
    modos.add_argument("--origen-ficticio", type=Path)
    modos.add_argument("--ensayar-origen-real", type=Path)
    parser.add_argument("--carpeta-trabajo-nueva", required=True, type=Path)
    parser.add_argument("--tablas-originales", nargs=7)
    args = parser.parse_args(argv)
    if args.origen_ficticio is not None and args.tablas_originales is None:
        parser.error("El modo ficticio requiere --tablas-originales.")
    if args.ensayar_origen_real is not None and args.tablas_originales is not None:
        parser.error("El modo real obtiene las siete tablas del origen.")
    try:
        if args.ensayar_origen_real is not None:
            informe = preparar_ensayo_origen_real(
                args.ensayar_origen_real, args.carpeta_trabajo_nueva)
        else:
            informe = preparar_ensayo(
                args.origen_ficticio, args.carpeta_trabajo_nueva,
                tablas_originales=args.tablas_originales,
            )
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as error:
        print("ENSAYO_RECHAZADO:", error)
        return 1
    print(informe["resultado"])
    print("Respaldo:", informe["respaldo"])
    print("SHA-256:", informe["sha256_respaldo"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
