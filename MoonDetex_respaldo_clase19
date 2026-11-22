import sqlite3
import tempfile
import unittest

from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import registro_analisis_v18


# =====================================
# MOONDETEX V0.19
# PRUEBA DE TRANSACCIONES SQLITE
# CORRECCION PARA WINDOWS
# =====================================

ORIGEN = (
    Path(__file__).resolve().parent
    / "moondetex.db"
)


class PruebaTransaccion(unittest.TestCase):

    def test_fallo_no_deja_registros_incompletos(self):

        self.assertTrue(
            ORIGEN.is_file(),
            "No se encontró moondetex.db"
        )

        # Crear carpeta temporal
        with tempfile.TemporaryDirectory() as temporal:

            copia = Path(temporal) / "prueba.db"

            # Copiar la base de datos
            # Cerrar ambas conexiones al terminar
            with closing(sqlite3.connect(ORIGEN)) as original:
                with closing(sqlite3.connect(copia)) as destino:
                    original.backup(destino)

            tablas = (
                "historial_analisis",
                "historial_observaciones",
                "evidencias_http",
                "historial_evidencias"
            )

            # Preparar la prueba
            with closing(sqlite3.connect(copia)) as con:

                proyecto = con.execute(
                    "SELECT id FROM proyectos LIMIT 1"
                ).fetchone()

                self.assertIsNotNone(
                    proyecto,
                    "Necesitas un proyecto guardado"
                )

                pid = proyecto[0]

                # Contar registros originales
                antes = {
                    tabla: con.execute(
                        f"SELECT COUNT(*) FROM {tabla}"
                    ).fetchone()[0]
                    for tabla in tablas
                }

                hallazgos_antes = con.execute(
                    "SELECT clave, titulo, detalle, estado "
                    "FROM hallazgos "
                    "WHERE proyecto_id = ? ORDER BY id",
                    (pid,)
                ).fetchall()

                # Simular error de almacenamiento
                con.executescript("""
                    CREATE TRIGGER fallo_simulado
                    BEFORE INSERT ON historial_evidencias
                    BEGIN
                        SELECT RAISE(
                            ABORT,
                            'Error de laboratorio'
                        );
                    END;
                """)

                con.commit()

            # Ejecutar la función sobre la copia
            with patch.object(
                registro_analisis_v18,
                "DB",
                copia
            ):

                with self.assertRaisesRegex(
                    sqlite3.DatabaseError,
                    "Error de laboratorio"
                ):

                    registro_analisis_v18.guardar_analisis_completo(
                        pid,
                        [
                            (
                                "prueba_v19",
                                "Prueba de fallo",
                                "Temporal"
                            )
                        ],
                        "HTTP/1.1 200 OK\n"
                        "Content-Type: text/html\n"
                    )

            # Comprobar que no cambió nada
            with closing(sqlite3.connect(copia)) as con:

                despues = {
                    tabla: con.execute(
                        f"SELECT COUNT(*) FROM {tabla}"
                    ).fetchone()[0]
                    for tabla in tablas
                }

                hallazgos_despues = con.execute(
                    "SELECT clave, titulo, detalle, estado "
                    "FROM hallazgos "
                    "WHERE proyecto_id = ? ORDER BY id",
                    (pid,)
                ).fetchall()

            self.assertEqual(antes, despues)

            self.assertEqual(
                hallazgos_antes,
                hallazgos_despues
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
