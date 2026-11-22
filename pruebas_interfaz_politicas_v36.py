"""Pruebas sin ventanas, red, main.py ni bases reales."""

import sqlite3
import unittest
from unittest.mock import MagicMock, Mock, patch

import interfaz_politicas_v36 as interfaz


class PruebasInterfazPoliticas(unittest.TestCase):
    def setUp(self):
        laboratorio = interfaz.laboratorio_temporal()
        self.conexion = self.enterContext(laboratorio)

    def estado(self, proyecto_id=1):
        return interfaz.consultar_estado(self.conexion, proyecto_id)

    def guardar(self, proyecto_id=1, dominios="example.net", puertos="8443",
                protocolos=("https",), **opciones):
        return interfaz.guardar_desde_campos(
            self.conexion, proyecto_id, dominios, puertos, protocolos, **opciones
        )

    def formulario(self, proyecto_id=1, **opciones):
        self.ctk = MagicMock()
        self.mensajes = Mock()
        self.ctk.BooleanVar.side_effect = lambda **kwargs: Mock(get=Mock(return_value=False))
        return interfaz.crear_formulario(
            Mock(), self.conexion, proyecto_id, "Proyecto ficticio",
            ctk_modulo=self.ctk, mensajes=self.mensajes, **opciones
        )

    def test_tabla_ausente_sin_crearla(self):
        with interfaz.laboratorio_temporal("sin-tabla") as conexion:
            self.assertEqual(interfaz.consultar_estado(conexion, 1)["estado"], interfaz.TABLA_AUSENTE)
            with self.assertRaises(ValueError):
                interfaz.guardar_desde_campos(
                    conexion, 1, "example.net", "443", ["https"], permitir_guardado=True
                )
            self.assertIsNone(conexion.execute(
                "SELECT name FROM sqlite_master WHERE name = 'politicas_proyecto'"
            ).fetchone())

    def test_estados_pendiente_configurada_invalida(self):
        for proyecto_id, esperado in (
            (1, interfaz.PENDIENTE), (2, interfaz.CONFIGURADA), (3, interfaz.INVALIDA),
        ):
            with self.subTest(id=proyecto_id):
                self.assertEqual(self.estado(proyecto_id)["estado"], esperado)

    def test_politica_configurada_contiene_valores(self):
        self.assertEqual(self.estado(2)["politica"], {
            "dominios": {"example.org"}, "puertos": {443}, "protocolos": {"https"},
        })

    def test_esquema_incompatible_es_error_de_almacenamiento(self):
        with interfaz.laboratorio_temporal("esquema-invalido") as conexion:
            self.assertEqual(
                interfaz.consultar_estado(conexion, 1)["estado"], interfaz.ERROR_ALMACENAMIENTO
            )

    def test_conexion_cerrada_es_error_de_almacenamiento(self):
        conexion = sqlite3.connect(":memory:")
        conexion.close()
        self.assertEqual(
            interfaz.consultar_estado(conexion, 1)["estado"], interfaz.ERROR_ALMACENAMIENTO
        )

    def test_proyecto_inexistente_no_es_politica_invalida(self):
        self.assertEqual(self.estado(99)["estado"], interfaz.ERROR_ALMACENAMIENTO)
        with self.assertRaises(ValueError):
            self.guardar(99, permitir_guardado=True)

    def test_id_invalido(self):
        for identificador in (True, "1", 0, None):
            with self.subTest(id=identificador):
                self.assertEqual(self.estado(identificador)["estado"], interfaz.ERROR_ALMACENAMIENTO)

    def test_consulta_no_escribe_ni_inicia_transaccion(self):
        cambios = self.conexion.total_changes
        for identificador in (1, 2, 3):
            self.estado(identificador)
        self.assertEqual(self.conexion.total_changes, cambios)
        self.assertFalse(self.conexion.in_transaction)

    def test_guardado_bloqueado_por_defecto_antes_de_consultar(self):
        with patch.object(interfaz, "consultar_estado") as consultar:
            with self.assertRaises(PermissionError):
                self.guardar()
            consultar.assert_not_called()
        self.assertEqual(self.estado()["estado"], interfaz.PENDIENTE)

    def test_permiso_no_se_deduce_de_valores_verdaderos(self):
        for permiso in (1, "True", object(), None, False):
            with self.subTest(permiso=permiso):
                with self.assertRaises(PermissionError):
                    self.guardar(permitir_guardado=permiso)

    def test_convertir_campos_sin_inventar_valores(self):
        politica = interfaz.convertir_campos(
            1, " example.net\n\nexample.org ", "443, 8443", ["http", "https"]
        )
        self.assertEqual(politica, {
            "dominios": {"example.net", "example.org"},
            "puertos": {443, 8443}, "protocolos": {"http", "https"},
        })

    def test_campos_vacios_no_generan_autorizaciones(self):
        for dominios, puertos, protocolos in (
            ("", "443", ["https"]), ("example.net", "", ["https"]),
            ("example.net", "443", []),
        ):
            with self.subTest(campos=(dominios, puertos, protocolos)):
                with self.assertRaises(ValueError):
                    interfaz.convertir_campos(1, dominios, puertos, protocolos)

    def test_entradas_invalidas_se_rechazan(self):
        for dominios, puertos, protocolos in (
            ("https://example.net", "443", ["https"]),
            ("example.net", "443,", ["https"]),
            ("example.net", "443.0", ["https"]),
            ("example.net", "0", ["https"]),
            ("example.net", "65536", ["https"]),
            ("example.net", "443", ["ftp"]),
            ("example.net", "443", "https"),
        ):
            with self.subTest(campos=(dominios, puertos, protocolos)):
                with self.assertRaises(ValueError):
                    interfaz.convertir_campos(1, dominios, puertos, protocolos)

    def test_guardar_y_actualizar_con_permiso_explicito(self):
        resultado = self.guardar(permitir_guardado=True)
        self.assertEqual(resultado["estado"], interfaz.CONFIGURADA)
        resultado = self.guardar(puertos="443", permitir_guardado=True)
        self.assertEqual(resultado["politica"]["puertos"], {443})

    def test_actualizacion_invalida_conserva_original_y_otro_proyecto(self):
        original = self.estado(2)
        with self.assertRaises(ValueError):
            self.guardar(2, puertos="70000", permitir_guardado=True)
        self.assertEqual(self.estado(2), original)
        self.assertEqual(self.estado(1)["estado"], interfaz.PENDIENTE)

    def test_reparar_politica_invalida_requiere_valores_explicitos(self):
        self.assertIsNone(self.estado(3)["politica"])
        resultado = self.guardar(3, permitir_guardado=True)
        self.assertEqual(resultado["estado"], interfaz.CONFIGURADA)
        self.assertEqual(resultado["politica"]["dominios"], {"example.net"})

    def test_formulario_vacio_y_guardado_deshabilitado(self):
        formulario = self.formulario()
        formulario["dominios"].insert.assert_not_called()
        formulario["puertos"].insert.assert_not_called()
        for llamada in self.ctk.BooleanVar.call_args_list:
            self.assertIs(llamada.kwargs["value"], False)
        self.assertEqual(self.ctk.CTkButton.call_args_list[0].kwargs["state"], "disabled")

    def test_callback_directo_bloqueado_sin_leer_widgets(self):
        formulario = self.formulario()
        callback = self.ctk.CTkButton.call_args_list[0].kwargs["command"]
        with patch.object(interfaz, "guardar_desde_campos") as guardar:
            self.assertFalse(callback())
            guardar.assert_not_called()
        formulario["dominios"].get.assert_not_called()
        formulario["puertos"].get.assert_not_called()
        self.mensajes.showwarning.assert_called_once()

    def test_sin_tabla_boton_y_callback_bloqueados_aun_con_permiso(self):
        self.conexion.execute("DROP TABLE politicas_proyecto")
        formulario = self.formulario(permitir_guardado=True)
        self.assertEqual(self.ctk.CTkButton.call_args_list[0].kwargs["state"], "disabled")
        formulario["dominios"].get.return_value = "example.net"
        formulario["puertos"].get.return_value = "443"
        formulario["protocolos"]["https"].get.return_value = True
        self.assertFalse(formulario["guardar"]())
        self.assertEqual(self.estado()["estado"], interfaz.TABLA_AUSENTE)
        self.mensajes.showerror.assert_called_once()

    def test_precargar_solo_politica_validada(self):
        formulario = self.formulario(2)
        formulario["dominios"].insert.assert_called_once_with("1.0", "example.org")
        formulario["puertos"].insert.assert_called_once_with(0, "443")
        formulario["protocolos"]["http"].set.assert_called_once_with(False)
        formulario["protocolos"]["https"].set.assert_called_once_with(True)

    def test_politica_invalida_no_precarga_datos(self):
        formulario = self.formulario(3)
        formulario["dominios"].insert.assert_not_called()
        formulario["puertos"].insert.assert_not_called()

    def test_callback_guarda_y_refresca_estado(self):
        refrescar = Mock()
        formulario = self.formulario(permitir_guardado=True, al_guardar=refrescar)
        formulario["dominios"].get.return_value = "example.net"
        formulario["puertos"].get.return_value = "8443"
        formulario["protocolos"]["https"].get.return_value = True
        self.assertTrue(formulario["guardar"]())
        self.assertEqual(self.estado()["estado"], interfaz.CONFIGURADA)
        formulario["estado"].configure.assert_called_once()
        self.mensajes.showinfo.assert_called_once()
        refrescar.assert_called_once()

    def test_callback_invalido_conserva_campos_y_ventana(self):
        formulario = self.formulario(2, permitir_guardado=True)
        original = self.estado(2)
        formulario["dominios"].get.return_value = "example.org"
        formulario["puertos"].get.return_value = "70000"
        formulario["protocolos"]["https"].get.return_value = True
        self.assertFalse(formulario["guardar"]())
        self.assertEqual(self.estado(2), original)
        formulario["ventana"].destroy.assert_not_called()
        formulario["dominios"].delete.assert_not_called()
        formulario["puertos"].delete.assert_not_called()
        self.mensajes.showerror.assert_called_once()

    def test_callback_recomprueba_tabla_al_guardar(self):
        formulario = self.formulario(permitir_guardado=True)
        formulario["dominios"].get.return_value = "example.net"
        formulario["puertos"].get.return_value = "443"
        formulario["protocolos"]["https"].get.return_value = True
        self.conexion.execute("DROP TABLE politicas_proyecto")
        self.assertFalse(formulario["guardar"]())
        self.mensajes.showerror.assert_called_once()

    def test_cancelar_no_escribe(self):
        formulario = self.formulario(permitir_guardado=True)
        cancelar = self.ctk.CTkButton.call_args_list[1].kwargs["command"]
        cambios = self.conexion.total_changes
        cancelar()
        self.assertEqual(self.conexion.total_changes, cambios)
        formulario["ventana"].destroy.assert_called_once()

    def test_callback_error_de_almacenamiento_no_cierra_formulario(self):
        formulario = self.formulario(permitir_guardado=True)
        formulario["dominios"].get.return_value = "example.net"
        formulario["puertos"].get.return_value = "443"
        self.conexion.execute("PRAGMA query_only = ON")
        formulario["protocolos"]["https"].get.return_value = True
        try:
            self.assertFalse(formulario["guardar"]())
            self.assertEqual(self.estado()["estado"], interfaz.PENDIENTE)
            formulario["ventana"].destroy.assert_not_called()
            self.mensajes.showerror.assert_called_once()
        finally:
            self.conexion.execute("PRAGMA query_only = OFF")

    def test_no_confirma_transaccion_externa(self):
        self.conexion.execute("BEGIN")
        self.guardar(permitir_guardado=True)
        self.assertTrue(self.conexion.in_transaction)
        self.conexion.rollback()
        self.assertEqual(self.estado()["estado"], interfaz.PENDIENTE)


if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=True)
