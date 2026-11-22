import sqlite3
import tempfile
import unittest

from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import gestor_hallazgos


# =====================================
# MOONDETEX V0.21
# PRUEBAS AUTOMATICAS DE HALLAZGOS
# =====================================

class PruebasHallazgos(unittest.TestCase):

    def setUp(self):

        # Crear una base de datos temporal
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.bd = (
            Path(self.temporal.name)
            / "hallazgos_prueba.db"
        )

        # Crear datos de laboratorio
        with closing(sqlite3.connect(self.bd)) as con:

            con.executescript("""
                CREATE TABLE proyectos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL
                );

                CREATE TABLE hallazgos (
                    id INTEGER PRIMARY KEY,
                    proyecto_id INTEGER NOT NULL,
                    clave TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    detalle TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'Pendiente',
                    FOREIGN KEY(proyecto_id)
                        REFERENCES proyectos(id)
                );

                INSERT INTO proyectos
                (id, nombre)
                VALUES (1, 'Laboratorio de prueba');

                INSERT INTO hallazgos
                (id, proyecto_id, clave, titulo,
                 detalle, fecha, estado)
                VALUES (
                    1,
                    1,
                    'csp',
                    'CSP por revisar',
                    'Cabecera ausente',
                    '2026-10-24',
                    'Pendiente'
                );
            """)

            con.commit()

        # Utilizar la base temporal
        parche = patch.object(
            gestor_hallazgos,
            "conectar",
            self.conectar_prueba
        )

        parche.start()
        self.addCleanup(parche.stop)


    def conectar_prueba(self):

        con = sqlite3.connect(self.bd)
        con.execute("PRAGMA foreign_keys = ON")

        return con


    # =====================================
    # PRUEBA 1: CONSULTAR HALLAZGOS
    # =====================================

    def test_consultar_hallazgos(self):

        filas = (
            gestor_hallazgos.obtener_hallazgos_con_estado()
        )

        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][5], "Pendiente")


    # =====================================
    # PRUEBA 2: GUARDAR ESTADO
    # =====================================

    def test_guardar_estado(self):

        resultado = (
            gestor_hallazgos.actualizar_estado_hallazgo(
                1,
                "Revisado"
            )
        )

        self.assertTrue(resultado)

        # Comprobar en una conexion nueva
        with closing(self.conectar_prueba()) as con:

            estado = con.execute(
                "SELECT estado FROM hallazgos "
                "WHERE id = 1"
            ).fetchone()[0]

        self.assertEqual(estado, "Revisado")


    # =====================================
    # PRUEBA 3: RECHAZAR ESTADO INVALIDO
    # =====================================

    def test_estado_invalido(self):

        with self.assertRaises(ValueError):

            gestor_hallazgos.actualizar_estado_hallazgo(
                1,
                "Estado desconocido"
            )

        filas = (
            gestor_hallazgos.obtener_hallazgos_con_estado()
        )

        self.assertEqual(filas[0][5], "Pendiente")


    # =====================================
    # PRUEBA 4: HALLAZGO INEXISTENTE
    # =====================================

    def test_hallazgo_inexistente(self):

        resultado = (
            gestor_hallazgos.actualizar_estado_hallazgo(
                999,
                "Revisado"
            )
        )

        self.assertFalse(resultado)


# =====================================
# EJECUTAR PRUEBAS
# =====================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
