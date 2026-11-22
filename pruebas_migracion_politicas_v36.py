"""Pruebas aisladas. Ejecutar: python -B -m unittest -v pruebas_migracion_politicas_v36

No importa main.py, no usa red ni abre bases reales. Los siete nombres de
este laboratorio son ficticios; no afirman describir el esquema de produccion.
"""

from contextlib import closing
import importlib
import io
import json
from pathlib import Path
import runpy
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import migracion_politicas_v36 as migracion
import preparar_migracion_politicas_v36 as preparador


TABLAS = ("proyectos", "hallazgos", "historial_analisis",
          "ejemplo_a", "ejemplo_b", "ejemplo_c", "ejemplo_d")


def crear_laboratorio(con):
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
        CREATE TABLE proyectos (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                nombre TEXT NOT NULL);
        CREATE TABLE hallazgos (id INTEGER PRIMARY KEY, proyecto_id INTEGER,
            detalle TEXT, FOREIGN KEY (proyecto_id) REFERENCES proyectos(id));
        CREATE TABLE historial_analisis (id INTEGER PRIMARY KEY, detalle TEXT);
        CREATE INDEX indice_nombre_ficticio ON proyectos(nombre);
        CREATE VIEW vista_ficticia AS SELECT nombre FROM proyectos;
        CREATE TRIGGER trigger_ficticio AFTER UPDATE ON proyectos
            BEGIN INSERT INTO historial_analisis(detalle) VALUES ('cambio'); END;
        INSERT INTO proyectos(nombre) VALUES ('Proyecto ficticio');
        INSERT INTO proyectos(nombre) VALUES ('Proyecto independiente');
        INSERT INTO hallazgos VALUES (1, 1, 'Hallazgo ficticio');
        INSERT INTO historial_analisis VALUES (1, 'Analisis ficticio');
    """)
    for tabla in TABLAS[3:]:
        con.execute(f'CREATE TABLE "{tabla}" (id INTEGER PRIMARY KEY, dato BLOB)')
        con.executemany(f'INSERT INTO "{tabla}" VALUES (?, ?)',
                        [(1, b"contenido"), (2, None)])
    con.commit()


class PruebasMigracionPoliticasV36(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        crear_laboratorio(self.con)
        self.antes = migracion.obtener_manifiesto(self.con)

    def migrar(self):
        return migracion.migrar_politicas(self.con, tablas_originales=TABLAS)

    def comprobar_intacta(self):
        self.assertEqual(migracion.obtener_manifiesto(self.con), self.antes)
        self.assertFalse(self.con.in_transaction)

    def test_migracion_correcta_y_tabla_vacia(self):
        self.assertEqual(self.migrar(), self.antes)
        self.assertFalse(self.con.in_transaction)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM politicas_proyecto").fetchone()[0], 0)
        columnas = self.con.execute("PRAGMA table_info(politicas_proyecto)").fetchall()
        self.assertEqual([fila[1] for fila in columnas],
                         ["proyecto_id", "dominios", "puertos", "protocolos", "fecha"])
        self.assertEqual(columnas[4][4], "CURRENT_TIMESTAMP")
        migracion.verificar_integridad(self.con)

    def test_conserva_siete_tablas_esquema_y_secuencias(self):
        self.migrar()
        migracion.verificar_conservacion(self.con, self.antes)
        self.assertEqual(len(self.antes["tablas"]), 7)
        self.assertIsNotNone(self.antes["secuencias"])

    def test_detecta_cambio_datos_con_igual_cantidad(self):
        self.migrar()
        self.con.execute("UPDATE ejemplo_a SET dato = 'alterado' WHERE id = 1")
        with self.assertRaisesRegex(RuntimeError, "Cambio inesperado"):
            migracion.verificar_conservacion(self.con, self.antes)

    def test_detecta_cambio_esquema(self):
        self.migrar()
        self.con.execute("DROP INDEX indice_nombre_ficticio")
        with self.assertRaisesRegex(RuntimeError, "Cambio inesperado"):
            migracion.verificar_conservacion(self.con, self.antes)

    def test_rechaza_tabla_existente_sin_cambios(self):
        self.con.execute("CREATE TABLE politicas_proyecto (incompatible TEXT)")
        self.con.commit()
        antes = migracion.obtener_manifiesto(self.con)
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            self.migrar()
        self.assertEqual(migracion.obtener_manifiesto(self.con), antes)

    def test_rechaza_vista_existente(self):
        self.con.execute("CREATE VIEW POLITICAS_PROYECTO AS SELECT id FROM proyectos")
        self.con.commit()
        antes = migracion.obtener_manifiesto(self.con)
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            self.migrar()
        self.assertEqual(migracion.obtener_manifiesto(self.con), antes)

    def test_rollback_completo_ante_error_despues_del_ddl(self):
        with patch.object(migracion, "verificar_conservacion",
                          side_effect=RuntimeError("fallo inducido")):
            with self.assertRaisesRegex(RuntimeError, "fallo inducido"):
                self.migrar()
        self.comprobar_intacta()

    def test_rollback_por_datos_o_esquema_alterados(self):
        verificar = migracion.verificar_conservacion
        for sql in ("UPDATE ejemplo_a SET dato = 'alterado' WHERE id = 1",
                    "DROP INDEX indice_nombre_ficticio"):
            with self.subTest(sql=sql):
                def alterar(con, antes):
                    con.execute(sql)
                    verificar(con, antes)
                with patch.object(migracion, "verificar_conservacion", side_effect=alterar):
                    with self.assertRaisesRegex(RuntimeError, "Cambio inesperado"):
                        self.migrar()
                self.comprobar_intacta()

    def test_rollback_si_falla_commit(self):
        def autorizar(accion, argumento, _b, _c, _d):
            if accion == sqlite3.SQLITE_TRANSACTION and argumento == "COMMIT":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.con.set_authorizer(autorizar)
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.migrar()
        finally:
            self.con.set_authorizer(None)
        self.comprobar_intacta()

    def test_on_delete_restrict_y_json_con_fecha(self):
        self.migrar()
        self.con.execute(
            "INSERT INTO politicas_proyecto (proyecto_id, dominios, puertos, protocolos) "
            "VALUES (2, ?, ?, ?)", ('["example.org"]', '[443]', '["https"]'))
        self.con.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("DELETE FROM proyectos WHERE id = 2")
        self.con.rollback()
        self.assertIsNotNone(self.con.execute(
            "SELECT fecha FROM politicas_proyecto WHERE proyecto_id = 2").fetchone()[0])
        fk = self.con.execute("PRAGMA foreign_key_list(politicas_proyecto)").fetchone()
        self.assertEqual(fk[6], "RESTRICT")

    def test_rechaza_inventario_inexacto(self):
        with self.assertRaises(ValueError):
            migracion.migrar_politicas(self.con, tablas_originales=TABLAS[:-1] + ("otra",))
        self.comprobar_intacta()

    def test_rechaza_proyectos_con_clave_incompatible(self):
        with closing(sqlite3.connect(":memory:")) as con:
            con.execute("CREATE TABLE proyectos(id TEXT PRIMARY KEY)")
            for tabla in TABLAS[1:]:
                con.execute(f'CREATE TABLE "{tabla}" (id INTEGER PRIMARY KEY)')
            con.commit()
            antes = migracion.obtener_manifiesto(con)
            with self.assertRaisesRegex(ValueError, "Esquema incompatible"):
                migracion.migrar_politicas(con, tablas_originales=TABLAS)
            self.assertEqual(migracion.obtener_manifiesto(con), antes)

    def test_no_confirma_ni_revierte_transaccion_del_llamador(self):
        self.con.execute("UPDATE ejemplo_a SET dato = 'pendiente' WHERE id = 1")
        with self.assertRaisesRegex(ValueError, "transaccion activa"):
            self.migrar()
        self.assertTrue(self.con.in_transaction)
        self.con.rollback()
        self.comprobar_intacta()

    def test_rechaza_relaciones_invalidas(self):
        self.con.execute("PRAGMA foreign_keys = OFF")
        self.con.execute("INSERT INTO hallazgos VALUES (2, 999, 'huerfano')")
        self.con.commit()
        antes = migracion.obtener_manifiesto(self.con)
        with self.assertRaisesRegex(RuntimeError, "Relaciones inconsistentes"):
            self.migrar()
        self.assertEqual(migracion.obtener_manifiesto(self.con), antes)
        self.assertEqual(self.con.execute("PRAGMA foreign_keys").fetchone()[0], 0)


class PruebasPreparadorV36(unittest.TestCase):
    def setUp(self):
        self.temporal = self.enterContext(TemporaryDirectory(prefix="ficticio_v36_"))
        self.carpeta = Path(self.temporal)
        self.origen = self.carpeta / "ficticia.db"
        with closing(sqlite3.connect(self.origen)) as con:
            crear_laboratorio(con)

    def preparar(self):
        return preparador.preparar_ensayo(
            self.origen, self.carpeta / "trabajo", tablas_originales=TABLAS)

    def test_respaldo_ensayo_y_recuperacion_ficticios(self):
        original = self.origen.read_bytes()
        informe = self.preparar()
        self.assertEqual(informe["resultado"], "ENSAYO_APROBADO")
        self.assertEqual(self.origen.read_bytes(), original)
        respaldo = Path(informe["respaldo"])
        contenido = respaldo.read_bytes()
        destino = preparador.recuperar_respaldo_ficticio(
            respaldo, self.carpeta / "restaurada.db",
            manifiesto=informe["manifiesto_original"], sha256=informe["sha256_respaldo"])
        self.assertEqual(destino.read_bytes(), contenido)
        self.assertEqual(respaldo.read_bytes(), contenido)
        self.assertTrue((self.carpeta / "trabajo" / "manifiesto.json").is_file())
        self.assertEqual(list((self.carpeta / "trabajo").glob("ensayo_v36_*")), [])
        # El manifiesto persistido tambien permite recuperar en otra sesion.
        guardado = json.loads((self.carpeta / "trabajo" / "manifiesto.json").read_text(
            encoding="utf-8"))
        preparador.recuperar_respaldo_ficticio(
            guardado["respaldo"], self.carpeta / "desde_manifiesto.db",
            manifiesto=guardado["manifiesto_original"], sha256=guardado["sha256_respaldo"])

    def test_no_toca_respaldos_existentes(self):
        carpeta = self.carpeta / "respaldos_existentes"
        carpeta.mkdir()
        previo = carpeta / "respaldo_previo.db"
        previo.write_bytes(b"respaldo centinela ficticio")
        with self.assertRaises(FileExistsError):
            preparador.preparar_ensayo(self.origen, carpeta, tablas_originales=TABLAS)
        self.assertEqual(previo.read_bytes(), b"respaldo centinela ficticio")
        self.assertEqual(list(carpeta.iterdir()), [previo])

    def test_recuperacion_rechaza_hash_incorrecto_y_destino_existente(self):
        informe = self.preparar()
        destino = self.carpeta / "no_sobrescribir.db"
        destino.write_bytes(b"centinela")
        for huella, error in (("incorrecto", RuntimeError),
                              (informe["sha256_respaldo"], FileExistsError)):
            with self.subTest(huella=huella), self.assertRaises(error):
                preparador.recuperar_respaldo_ficticio(
                    informe["respaldo"], destino,
                    manifiesto=informe["manifiesto_original"], sha256=huella)
        self.assertEqual(destino.read_bytes(), b"centinela")

    def test_rechaza_nombre_real_antes_de_abrir_sqlite(self):
        # Es solo una ruta ficticia: no se crea ni se abre ese archivo.
        with patch.object(sqlite3, "connect", side_effect=AssertionError("No abrir")):
            with self.assertRaises(ValueError):
                preparador.preparar_ensayo(
                    self.carpeta / "moondetex.db", self.carpeta / "trabajo",
                    tablas_originales=TABLAS)

    def test_origen_inexistente_no_se_crea(self):
        ruta = self.carpeta / "ausente.db"
        with self.assertRaises(FileNotFoundError):
            preparador.preparar_ensayo(ruta, self.carpeta / "trabajo",
                                      tablas_originales=TABLAS)
        self.assertFalse(ruta.exists())
        self.assertFalse((self.carpeta / "trabajo").exists())

    def test_importar_y_ejecutar_sin_parametros_no_hace_io_de_bases(self):
        # Fallar ante cualquier intento de conectar, respaldar o crear carpetas.
        self.addCleanup(importlib.reload, preparador)
        with patch.object(sqlite3, "connect", side_effect=AssertionError("No conectar")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("No crear")), \
             patch("respaldo_sqlite_v26.crear_respaldo",
                   side_effect=AssertionError("No respaldar")), \
             patch("sys.stdout", new_callable=io.StringIO), \
             patch("sys.stderr", new_callable=io.StringIO):
            importlib.reload(migracion)
            importlib.reload(preparador)
            runpy.run_path(str(Path(migracion.__file__)), run_name="__main__")
            with patch("sys.argv", ["preparar_migracion_politicas_v36.py"]):
                with self.assertRaises(SystemExit) as resultado:
                    runpy.run_path(str(Path(preparador.__file__)), run_name="__main__")
            self.assertEqual(resultado.exception.code, 2)


class PruebasOrigenLecturaV36(unittest.TestCase):
    # Reutilizar la fabrica de siete tablas ficticias, sin heredar sus tests.
    setUp = PruebasPreparadorV36.setUp

    def ensayar_temporal(self):
        return preparador.preparar_ensayo_origen_real(
            self.origen, self.carpeta / "trabajo_lectura")

    def leer_informe(self):
        return json.loads((self.carpeta / "trabajo_lectura" / "informe_ensayo.json").read_text(
            encoding="utf-8"))

    def test_ensayo_completo_sobre_origen_temporal(self):
        original = self.origen.read_bytes()
        informe = self.ensayar_temporal()
        self.assertEqual(informe["resultado"], "ENSAYO_APROBADO")
        self.assertTrue(informe["seguro_continuar"])
        self.assertTrue(all(valor == "APROBADA" for valor in informe["comprobaciones"].values()))
        self.assertEqual(self.origen.read_bytes(), original)
        self.assertEqual(informe["politicas_proyecto"]["cantidad"], 0)
        self.assertEqual(self.leer_informe()["resultado"], "ENSAYO_APROBADO")
        self.assertEqual(Path(informe["respaldo"]).read_bytes(),
                         Path(informe["recuperacion"]).read_bytes())
        with closing(sqlite3.connect(Path(informe["copia_trabajo"]))) as con:
            migracion.verificar_conservacion(con, informe["manifiesto_original"])

    def test_conexion_origen_ro_query_only_y_snapshot(self):
        conectar = sqlite3.connect
        consultas = []
        aperturas = []

        def registrar(ruta, *args, **kwargs):
            con = conectar(ruta, *args, **kwargs)
            if str(ruta).startswith(self.origen.as_uri()):
                aperturas.append((str(ruta), kwargs.get("uri")))
                con.set_trace_callback(consultas.append)
            return con

        with patch.object(sqlite3, "connect", side_effect=registrar):
            self.ensayar_temporal()
        self.assertEqual(aperturas, [(self.origen.as_uri() + "?mode=ro", True)])
        self.assertIn("PRAGMA query_only = ON", consultas)
        self.assertIn("BEGIN", consultas)
        self.assertFalse(any(sql.startswith(("CREATE", "INSERT", "UPDATE", "DELETE"))
                             for sql in consultas))

    def test_query_only_rechaza_escritura(self):
        with closing(preparador._abrir_lectura(self.origen)) as con:
            self.assertEqual(con.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("DELETE FROM ejemplo_a")

    def test_fallo_migracion_conserva_respaldo_e_informe(self):
        with patch.object(preparador, "migrar_politicas", side_effect=RuntimeError("inducido")):
            with self.assertRaisesRegex(RuntimeError, "inducido"):
                self.ensayar_temporal()
        informe = self.leer_informe()
        self.assertFalse(informe["seguro_continuar"])
        self.assertEqual(informe["comprobaciones"]["migracion"], "FALLIDA")
        self.assertEqual(informe["errores"][0]["detalle"], "inducido")
        self.assertEqual(preparador.calcular_hash(Path(informe["respaldo"])),
                         informe["sha256_respaldo"])

    def test_backup_incluye_datos_confirmados_en_wal(self):
        # Mantener una conexion abierta para conservar el WAL del laboratorio.
        with closing(sqlite3.connect(self.origen)) as escritor:
            modo = escritor.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            self.assertEqual(modo.lower(), "wal")
            escritor.execute("UPDATE ejemplo_a SET dato = 'confirmado en WAL' WHERE id = 1")
            escritor.commit()
            informe = self.ensayar_temporal()
            with closing(preparador._abrir_lectura(Path(informe["respaldo"]))) as con:
                self.assertEqual(con.execute("SELECT dato FROM ejemplo_a WHERE id = 1").fetchone()[0],
                                 "confirmado en WAL")

    def test_fallo_recuperacion_conserva_respaldo_e_informe(self):
        recuperar = preparador.recuperar_respaldo_ficticio

        def fallar_solo_recuperacion(respaldo, destino, **kwargs):
            if Path(destino).name == "recuperacion_prueba.db":
                raise RuntimeError("recuperacion inducida")
            return recuperar(respaldo, destino, **kwargs)

        with patch.object(preparador, "recuperar_respaldo_ficticio", side_effect=fallar_solo_recuperacion):
            with self.assertRaisesRegex(RuntimeError, "recuperacion inducida"):
                self.ensayar_temporal()
        informe = self.leer_informe()
        self.assertEqual(informe["comprobaciones"]["recuperacion"], "FALLIDA")
        self.assertTrue(Path(informe["respaldo"]).is_file())
        self.assertFalse(informe["seguro_continuar"])

    def test_detecta_commit_concurrente_incluso_si_datos_se_restauran(self):
        migrar = preparador.migrar_politicas

        def escribir_y_migrar(con, **kwargs):
            with closing(sqlite3.connect(self.origen)) as escritor:
                escritor.execute("UPDATE ejemplo_a SET dato = 'concurrente' WHERE id = 1")
                escritor.commit()
                escritor.execute("UPDATE ejemplo_a SET dato = ? WHERE id = 1", (b"contenido",))
                escritor.commit()
            return migrar(con, **kwargs)

        with patch.object(preparador, "migrar_politicas", side_effect=escribir_y_migrar):
            with self.assertRaisesRegex(RuntimeError, "Cambios concurrentes"):
                self.ensayar_temporal()
        self.assertEqual(self.leer_informe()["comprobaciones"]["origen_estable"], "FALLIDA")

    def test_rechaza_respaldo_de_otro_estado(self):
        manifestar = preparador._manifestar_archivo

        def alterar_manifiesto(ruta):
            resultado = manifestar(ruta)
            resultado["tablas"]["proyectos"]["huella"] = "incompatible"
            return resultado

        with patch.object(preparador, "_manifestar_archivo", side_effect=alterar_manifiesto):
            with self.assertRaisesRegex(RuntimeError, "manifiesto difieren"):
                self.ensayar_temporal()
        informe = self.leer_informe()
        self.assertTrue(Path(informe["respaldo"]).is_file())
        self.assertEqual(informe["comprobaciones"]["comparacion_respaldo"], "FALLIDA")

    def test_rechaza_origen_ausente_y_carpeta_como_origen(self):
        for ruta in (self.carpeta / "ausente.db", self.carpeta):
            with self.subTest(ruta=ruta), self.assertRaises(FileNotFoundError):
                preparador.preparar_ensayo_origen_real(ruta, self.carpeta / "nuevo")
        self.assertFalse((self.carpeta / "nuevo").exists())

    def test_rechaza_carpeta_existente_y_ruta_coincidente(self):
        for destino in (self.origen, self.origen.parent / "." / self.origen.name,
                        self.carpeta):
            with self.subTest(destino=destino), self.assertRaises((ValueError, FileExistsError)):
                preparador.preparar_ensayo_origen_real(self.origen, destino)

    def test_rechaza_enlace_duro_al_origen(self):
        enlace = self.carpeta / "enlace.db"
        try:
            enlace.hardlink_to(self.origen)
        except OSError as error:
            self.skipTest(f"El sistema no permite crear enlaces duros: {error}")
        with self.assertRaisesRegex(ValueError, "deben ser distintos"):
            preparador._exigir_rutas_distintas(self.origen, enlace)
        with self.assertRaises(ValueError):
            preparador.preparar_ensayo_origen_real(self.origen, enlace)

    def test_recuperacion_rechaza_destino_igual_al_respaldo(self):
        informe = self.ensayar_temporal()
        respaldo = Path(informe["respaldo"])
        with self.assertRaises(ValueError):
            preparador.recuperar_respaldo_ficticio(
                respaldo, respaldo.parent / "." / respaldo.name,
                manifiesto=informe["manifiesto_original"], sha256=informe["sha256_respaldo"])

    def test_rechaza_inventario_con_ocho_tablas_y_emite_informe(self):
        with closing(sqlite3.connect(self.origen)) as con:
            con.execute("CREATE TABLE adicional(id INTEGER PRIMARY KEY)")
            con.commit()
        with self.assertRaisesRegex(ValueError, "siete tablas"):
            self.ensayar_temporal()
        self.assertEqual(self.leer_informe()["comprobaciones"]["origen"], "FALLIDA")

    def test_cli_rechaza_sin_argumentos_y_modos_simultaneos(self):
        with patch.object(preparador, "preparar_ensayo_origen_real") as ejecutar:
            for argumentos in ([], ["--origen-ficticio", "a.db", "--ensayar-origen-real", "b.db",
                                   "--carpeta-trabajo-nueva", "nueva"]):
                with self.subTest(argumentos=argumentos), patch("sys.stderr", new_callable=io.StringIO):
                    with self.assertRaises(SystemExit) as salida:
                        preparador.main(argumentos)
                    self.assertEqual(salida.exception.code, 2)
            ejecutar.assert_not_called()

    def test_cli_ruta_incorrecta_devuelve_error(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            codigo = preparador.main([
                "--ensayar-origen-real", str(self.carpeta / "ausente.db"),
                "--carpeta-trabajo-nueva", str(self.carpeta / "nuevo"),
            ])
        self.assertEqual(codigo, 1)
        self.assertFalse((self.carpeta / "nuevo").exists())

    def test_cli_selecciona_entrada_explicita_sin_ejecutar_ensayo(self):
        resultado = {"resultado": "ENSAYO_APROBADO", "respaldo": "ficticio", "sha256_respaldo": "hash"}
        with patch.object(preparador, "preparar_ensayo_origen_real", return_value=resultado) as ejecutar, \
             patch("sys.stdout", new_callable=io.StringIO):
            codigo = preparador.main(["--ensayar-origen-real", str(self.origen),
                                      "--carpeta-trabajo-nueva", str(self.carpeta / "nuevo")])
        self.assertEqual(codigo, 0)
        ejecutar.assert_called_once_with(self.origen, self.carpeta / "nuevo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
