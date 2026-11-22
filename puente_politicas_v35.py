# =====================================
# MOONDETEX - CLASE 35
# PUENTE ENTRE PROYECTOS Y POLITICAS
# =====================================

from cargar_proyectos_reales_v35 import cargar_proyectos_reales

from vincular_politicas_v35 import verificar_proyecto_registrado


def verificar_proyecto_real(
    proyecto_id,
    url,
    politicas,
    resolver
):
    # Leer proyectos reales desde SQLite
    proyectos = cargar_proyectos_reales()

    # Aplicar las reglas del proyecto seleccionado
    return verificar_proyecto_registrado(
        proyecto_id,
        url,
        proyectos,
        politicas,
        resolver
    )


# =====================================
# LABORATORIO SIN CONEXIONES DE RED
# =====================================

if __name__ == "__main__":

    # Aun no hay politicas configuradas
    politicas = {}

    def resolver_bloqueado(dominio):
        raise RuntimeError(
            "No debe consultarse el DNS."
        )

    print("\nMOONDETEX - CLASE 35")
    print("VINCULACION DE PROYECTOS REALES")
    print("==============================")

    try:
        verificar_proyecto_real(
            1,
            "https://example.org",
            politicas,
            resolver_bloqueado
        )

        print("OBJETIVO VALIDADO")

    except ValueError as error:
        print("OBJETIVO RECHAZADO")
        print("Motivo:", error)
