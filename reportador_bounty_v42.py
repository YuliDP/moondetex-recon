import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from base_datos import CARPETA, DB, conectar
from lector_politicas_v35 import cargar_politica


# =====================================
# MOONDETEX - CLASE 42
# TRIAJE Y REPORTES FORENSES (MARKDOWN)
# =====================================

ESTADOS_HALLAZGO_VALIDOS = {
    "Pendiente",
    "Revisado",
    "Falso Positivo",
    "Reportable",
}


def cambiar_estado_hallazgo(proyecto_id, hallazgo_id, nuevo_estado, db_ruta=DB):
    if type(proyecto_id) is not int or proyecto_id <= 0:
        raise ValueError("ID de proyecto invalido.")

    if type(hallazgo_id) is not int or hallazgo_id <= 0:
        raise ValueError("ID de hallazgo invalido.")

    if nuevo_estado not in ESTADOS_HALLAZGO_VALIDOS:
        permitidos = ", ".join(sorted(ESTADOS_HALLAZGO_VALIDOS))
        raise ValueError(f"Estado no valido. Usa uno de: {permitidos}")

    if not db_ruta.is_file():
        raise FileNotFoundError("No se encontro la base de datos.")

    conexion = conectar() if db_ruta == DB else sqlite3.connect(db_ruta)
    conexion.execute("PRAGMA foreign_keys = ON")

    with closing(conexion):
        with conexion:
            cursor = conexion.execute(
                """
                UPDATE hallazgos
                SET estado = ?
                WHERE id = ? AND proyecto_id = ?
                """,
                (nuevo_estado, hallazgo_id, proyecto_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    f"No existe el hallazgo #{hallazgo_id} en el proyecto #{proyecto_id}."
                )

    return True


def exportar_reporte_markdown(
    proyecto_id,
    incluir_pendientes=True,
    db_ruta=DB,
    carpeta_salida=None,
):
    if type(proyecto_id) is not int or proyecto_id <= 0:
        raise ValueError("ID de proyecto invalido.")

    if not db_ruta.is_file():
        raise FileNotFoundError("No se encontro la base de datos.")

    with closing(
        sqlite3.connect(db_ruta.as_uri() + "?mode=ro", uri=True)
    ) as conexion:
        conexion.execute("PRAGMA query_only = ON")

        proyecto = conexion.execute(
            """
            SELECT nombre, alcance, notas, fecha
            FROM proyectos
            WHERE id = ?
            """,
            (proyecto_id,),
        ).fetchone()

        if proyecto is None:
            raise ValueError("El proyecto no existe.")

        nombre, alcance, notas, fecha_creacion = proyecto
        politica = cargar_politica(conexion, proyecto_id)

        estados_filtrados = ["Reportable", "Revisado"]
        if incluir_pendientes:
            estados_filtrados.append("Pendiente")

        marcadores = ", ".join("?" for _ in estados_filtrados)
        hallazgos = conexion.execute(
            f"""
            SELECT id, clave, titulo, detalle, estado, fecha
            FROM hallazgos
            WHERE proyecto_id = ? AND estado IN ({marcadores})
            ORDER BY
                CASE estado
                    WHEN 'Reportable' THEN 1
                    WHEN 'Revisado' THEN 2
                    ELSE 3
                END,
                id ASC
            """,
            [proyecto_id, *estados_filtrados],
        ).fetchall()

        evidencias = conexion.execute(
            """
            SELECT ha.id, ha.fecha, eh.huella_sha256, ha.total_observaciones
            FROM historial_analisis ha
            JOIN historial_evidencias he ON he.analisis_id = ha.id
            JOIN evidencias_http eh ON eh.id = he.evidencia_id
            WHERE ha.proyecto_id = ?
            ORDER BY ha.id DESC
            LIMIT 10
            """,
            (proyecto_id,),
        ).fetchall()

    destino_dir = (
        Path(carpeta_salida)
        if carpeta_salida is not None
        else (CARPETA / "reportes")
    )
    destino_dir.mkdir(parents=True, exist_ok=True)

    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"reporte_moondetex_p{proyecto_id}_{marca_tiempo}.md"
    ruta_reporte = destino_dir / nombre_archivo

    lineas = [
        f"# Informe Tecnico de Reconocimiento - {nombre}",
        "",
        f"- **Herramienta:** MoonDetex Bug Bounty Recon",
        f"- **Proyecto ID:** `{proyecto_id}`",
        f"- **Fecha de emision:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Alcance declarado:** {alcance}",
    ]

    if notas:
        lineas.append(f"- **Notas:** {notas}")

    lineas.extend(["", "## 1. Politica de Alcance Autorizada", ""])
    if politica is None:
        lineas.append("_Sin politica activa configurada._")
    else:
        doms = ", ".join(f"`{d}`" for d in sorted(politica["dominios"]))
        puertos = ", ".join(f"`{p}`" for p in sorted(politica["puertos"]))
        protos = ", ".join(f"`{pr}`" for pr in sorted(politica["protocolos"]))
        lineas.extend([
            f"- **Dominios:** {doms}",
            f"- **Puertos:** {puertos}",
            f"- **Protocolos:** {protos}",
        ])

    lineas.extend(["", "## 2. Hallazgos Seleccionados", ""])
    if not hallazgos:
        lineas.append("_No hay hallazgos bajo los criterios de triaje seleccionados._")
    else:
        for hid, clave, titulo, detalle, estado, fecha_h in hallazgos:
            lineas.extend([
                f"### [#{hid}] {titulo}",
                f"- **Estado de triaje:** `{estado}`",
                f"- **Identificador:** `{clave}`",
                f"- **Ultima deteccion:** {fecha_h}",
                f"- **Detalle tecnico:** {detalle}",
                "",
            ])

    lineas.extend(["## 3. Cadena de Custodia (Evidencias SHA-256)", ""])
    if not evidencias:
        lineas.append("_Aun no se han registrado evidencias HTTP con huella SHA-256._")
    else:
        lineas.extend([
            "| Analisis ID | Fecha | Observaciones | Huella SHA-256 |",
            "| :--- | :--- | :---: | :--- |",
        ])
        for aid, fecha_a, sha256, total_obs in evidencias:
            lineas.append(
                f"| #{aid} | {fecha_a} | {total_obs} | `{sha256}` |"
            )

    ruta_reporte.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta_reporte


# =====================================
# LABORATORIO OFFLINE (SIN TOCAR DB REAL)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 42")
    print("TRIAJE Y REPORTES FORENSES (LABORATORIO)")
    print("========================================")

    with TemporaryDirectory() as temporal:
        base_temp = Path(temporal)
        db_lab = base_temp / "reportes_lab.db"

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
                "INSERT INTO proyectos (id, nombre, alcance, notas) VALUES (?, ?, ?, ?)",
                (1, "Programa Bug Bounty Demo", "*.objetivo.com", "Pruebas pasivas autorizadas"),
            )
            con.execute(
                "INSERT INTO politicas_proyecto VALUES (?, ?, ?, ?)",
                (1, '["*.objetivo.com"]', '[443]', '["https"]'),
            )
            con.executemany(
                "INSERT INTO hallazgos (id, proyecto_id, clave, titulo, detalle) VALUES (?, ?, ?, ?, ?)",
                [
                    (1, 1, "api.objetivo.com:banner_x-powered-by", "Cabecera tecnologica expuesta", "Valor reportado: PHP/8.1.2"),
                    (2, 1, "api.objetivo.com:missing_csp", "Falta CSP", "Sin cabecera CSP"),
                ],
            )
            con.execute(
                "INSERT INTO historial_analisis (id, proyecto_id, total_observaciones) VALUES (1, 1, 2)"
            )
            con.execute(
                "INSERT INTO evidencias_http (id, proyecto_id, contenido, huella_sha256) VALUES (1, 1, '{}', ?)",
                ("a" * 64,),
            )
            con.execute(
                "INSERT INTO historial_evidencias (analisis_id, evidencia_id) VALUES (1, 1)"
            )
            con.commit()

        # Clasificar hallazgos: uno reportable y otro falso positivo
        cambiar_estado_hallazgo(1, 1, "Reportable", db_ruta=db_lab)
        cambiar_estado_hallazgo(1, 2, "Falso Positivo", db_ruta=db_lab)

        ruta_md = exportar_reporte_markdown(
            proyecto_id=1,
            incluir_pendientes=False,
            db_ruta=db_lab,
            carpeta_salida=base_temp,
        )

        print("REPORTE GENERADO:", ruta_md.name)
        print("\n--- CONTENIDO DEL REPORTE ---")
        print(ruta_md.read_text(encoding="utf-8"))