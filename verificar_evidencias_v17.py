import hashlib
import sqlite3
from pathlib import Path

# MOONDETEX V0.17
# VERIFICAR INTEGRIDAD DE EVIDENCIAS

BASE_DATOS = (
    Path(__file__).resolve().parent
    / "moondetex.db"
)

if not BASE_DATOS.is_file():
    raise SystemExit("No se encontro la base de datos.")

with sqlite3.connect(BASE_DATOS) as conexion:

    evidencias = conexion.execute("""
        SELECT
            h.analisis_id,
            a.proyecto_id,
            e.proyecto_id,
            e.contenido,
            e.huella_sha256
        FROM historial_evidencias h
        JOIN historial_analisis a
            ON a.id = h.analisis_id
        LEFT JOIN evidencias_http e
            ON e.id = h.evidencia_id
        ORDER BY h.analisis_id
    """).fetchall()

print("\n=== MOONDETEX V0.17 ===")
print("VERIFICACION DE EVIDENCIAS\n")

correctas = 0
errores = 0

for analisis, proyecto, origen, texto, huella in evidencias:

    if texto is None or huella is None:
        valido = False
    else:
        calculada = hashlib.sha256(
            texto.encode("utf-8")
        ).hexdigest()

        valido = (
            calculada == huella
            and proyecto == origen
        )

    if valido:
        correctas += 1
        print(f"Analisis #{analisis}: OK")
    else:
        errores += 1
        print(f"Analisis #{analisis}: REVISAR")

print("\nRESULTADOS")
print("Evidencias correctas:", correctas)
print("Evidencias con problemas:", errores)

if errores == 0:
    print("Verificacion completada.")
else:
    print("Se encontraron inconsistencias.")
