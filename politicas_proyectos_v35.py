# =====================================
# MOONDETEX - CLASE 35
# POLITICAS DE SEGURIDAD POR PROYECTO
# =====================================

from politica_objetivos_v35 import aplicar_politica_local


def verificar_objetivo_proyecto(
    proyecto_id,
    url,
    politicas,
    resolver
):

    # Comprobar que existan politicas
    if not isinstance(politicas, dict):
        raise ValueError(
            "El registro de politicas no es valido."
        )

    # Comprobar que el proyecto exista
    if proyecto_id not in politicas:
        raise ValueError(
            "El proyecto no tiene una politica registrada."
        )

    # Obtener la politica de ese proyecto
    politica = politicas[proyecto_id]

    # Aplicar sus reglas de seguridad
    return aplicar_politica_local(
        url,
        politica,
        resolver
    )


# =====================================
# LABORATORIO LOCAL SIN INTERNET
# =====================================

if __name__ == "__main__":

    politicas = {
        "web_demo": {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"https"}
        },

        "api_demo": {
            "dominios": {"example.net"},
            "puertos": {8443},
            "protocolos": {"https"}
        }
    }

    def resolver_simulado(dominio):
        respuestas = {
            "example.org": ["8.8.8.8"],
            "example.net": ["1.1.1.1"]
        }
        return respuestas.get(dominio, [])

    casos = [
        (
            "Web permitido",
            "web_demo",
            "https://example.org/inicio"
        ),
        (
            "Dominio de otro proyecto",
            "web_demo",
            "https://example.net"
        ),
        (
            "API permitida",
            "api_demo",
            "https://example.net:8443/docs"
        ),
        (
            "Puerto incorrecto",
            "api_demo",
            "https://example.net/docs"
        ),
        (
            "Proyecto inexistente",
            "desconocido",
            "https://example.org"
        )
    ]

    print("\nMOONDETEX - CLASE 35")
    print("POLITICAS POR PROYECTO")
    print("==============================")

    for nombre, proyecto, url in casos:

        try:
            resultado = verificar_objetivo_proyecto(
                proyecto,
                url,
                politicas,
                resolver_simulado
            )

            print("\nPERMITIDO:", nombre)
            print("Puerto:", resultado["puerto"])

        except ValueError as error:
            print("\nRECHAZADO:", nombre)
            print("Motivo:", error)
