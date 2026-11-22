# =====================================
# MOONDETEX - CLASE 35
# VINCULACION DE POLITICAS A PROYECTOS
# =====================================

from politicas_proyectos_v35 import verificar_objetivo_proyecto


def verificar_proyecto_registrado(
    proyecto_id,
    url,
    proyectos,
    politicas,
    resolver
):

    # Comprobar el listado de proyectos
    if not isinstance(proyectos, (list, tuple)):
        raise ValueError(
            "El listado de proyectos no es valido."
        )

    ids = []

    for proyecto in proyectos:

        if (
            not isinstance(proyecto, dict)
            or type(proyecto.get("id")) is not int
        ):
            raise ValueError(
                "Se encontro un proyecto invalido."
            )

        ids.append(proyecto["id"])

    # Impedir identificadores duplicados
    if len(ids) != len(set(ids)):
        raise ValueError(
            "Existen proyectos con ID duplicado."
        )

    # Comprobar que el proyecto exista
    if type(proyecto_id) is not int or proyecto_id not in ids:
        raise ValueError(
            "El proyecto no esta registrado."
        )

    # Aplicar exclusivamente su politica
    return verificar_objetivo_proyecto(
        proyecto_id,
        url,
        politicas,
        resolver
    )


# =====================================
# LABORATORIO LOCAL SIN INTERNET
# =====================================

if __name__ == "__main__":

    proyectos = [
        {"id": 1, "nombre": "Laboratorio Web"},
        {"id": 2, "nombre": "Laboratorio API"}
    ]

    politicas = {
        1: {
            "dominios": {"example.org"},
            "puertos": {443},
            "protocolos": {"https"}
        },
        2: {
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
        (1, "https://example.org"),
        (1, "https://example.net:8443"),
        (2, "https://example.net:8443"),
        (2, "https://example.net"),
        (99, "https://example.org")
    ]

    print("\nMOONDETEX - CLASE 35")
    print("VINCULACION DE POLITICAS")
    print("==============================")

    for proyecto_id, url in casos:

        try:
            resultado = verificar_proyecto_registrado(
                proyecto_id,
                url,
                proyectos,
                politicas,
                resolver_simulado
            )

            print("\nPERMITIDO: Proyecto", proyecto_id)
            print("URL:", resultado["url"])

        except ValueError as error:
            print("\nRECHAZADO: Proyecto", proyecto_id)
            print("Motivo:", error)
