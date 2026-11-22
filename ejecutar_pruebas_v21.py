import sys
import unittest

# =====================================
# MOONDETEX V0.21
# CENTRO DE PRUEBAS AUTOMATICAS
# =====================================

# Archivos de pruebas que vamos a ejecutar






MODULOS = [
    "pruebas_v07",
    "pruebas_v08",
    "pruebas_v09",
    "pruebas_v10",
    "pruebas_guardado_v19",
    "pruebas_proyectos_v20",
    "pruebas_hallazgos_v21",
    "pruebas_diagnostico_v25",
    "pruebas_respaldos_v26",
    "pruebas_recuperacion_v27",
    "pruebas_restauracion_v27",
    "pruebas_validador_v29",
    "pruebas_filtros_v30",
    "pruebas_alcance_v32",
    "pruebas_redirecciones_v32",
    "pruebas_dns_v33",
    "pruebas_verificar_informes_v33",
    "pruebas_resolver_dns_v34",
    "pruebas_adaptador_dns_v34",
    "pruebas_control_puertos_v34",
    "pruebas_preconexion_v35",
    "pruebas_comparador_dns_v35",
    "pruebas_dns_estable_v35",
    "pruebas_politica_objetivos_v35",
    "pruebas_politicas_proyectos_v35",
    "pruebas_vincular_politicas_v35",
    "pruebas_cargar_proyectos_v35",
    "pruebas_puente_politicas_v35",
    "pruebas_politicas_sqlite_v35",
    "pruebas_guardado_seguro_v35",
    "pruebas_migracion_politicas_v35",
    "pruebas_integridad_politicas_v35",
    "pruebas_lector_politicas_v35",
    "pruebas_politica_guardada_v35",
    "pruebas_auditoria_politicas_v35",
    "pruebas_migracion_segura_v35",
    "pruebas_comparacion_migracion_v35"

]



def ejecutar_pruebas():

    print("\n================================")
    print("      MOONDETEX V0.21")
    print("   CENTRO DE PRUEBAS")
    print("================================\n")

    # Preparar el sistema de pruebas
    cargador = unittest.TestLoader()

    conjunto = cargador.loadTestsFromNames(
        MODULOS
    )

    total = conjunto.countTestCases()

    print(f"Pruebas encontradas: {total}")
    print("\nIniciando comprobaciones...\n")

    # Ejecutar todas las pruebas
    ejecutor = unittest.TextTestRunner(
        verbosity=2
    )

    resultado = ejecutor.run(conjunto)

    # Mostrar resumen final
    print("\n================================")
    print("     RESULTADOS MOONDETEX")
    print("================================")

    ejecutadas = resultado.testsRun

    errores = len(resultado.errors)
    fallos = len(resultado.failures)

    omitidas = len(resultado.skipped)

    aprobadas = (
        ejecutadas - errores - fallos - omitidas
    )

    print(f"Ejecutadas: {ejecutadas}")
    print(f"Aprobadas: {aprobadas}")
    print(f"Fallos: {fallos}")
    print(f"Errores: {errores}")
    print(f"Omitidas: {omitidas}")

    if resultado.wasSuccessful():

        print("\nRESULTADO: PRUEBAS APROBADAS")

    else:

        print("\nRESULTADO: REVISAR ERRORES")

    return resultado.wasSuccessful()


# =====================================
# INICIAR EL CENTRO DE PRUEBAS
# =====================================

if __name__ == "__main__":

    correcto = ejecutar_pruebas()

    if correcto:
        sys.exit(0)
    else:
        sys.exit(1)
