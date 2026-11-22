# =====================================
# MOONDETEX - CLASE 35
# VERIFICACION DNS EN DOS ETAPAS
# =====================================

from verificador_preconexion_v35 import verificar_destino

from comparador_dns_v35 import comparar_respuestas_dns


def verificar_dns_estable(
    url,
    dominios_permitidos,
    puertos_permitidos,
    resolver
):

    # PRIMERA COMPROBACION
    primera = verificar_destino(
        url,
        dominios_permitidos,
        puertos_permitidos,
        resolver
    )

    # SEGUNDA COMPROBACION
    segunda = verificar_destino(
        url,
        dominios_permitidos,
        puertos_permitidos,
        resolver
    )

    # COMPARAR LAS RESPUESTAS DNS
    comparar_respuestas_dns(
        primera["ips"],
        segunda["ips"]
    )

    return primera


# =====================================
# LABORATORIO LOCAL SIN INTERNET
# =====================================

if __name__ == "__main__":

    dominios = {"example.org"}
    puertos = {443}
    url = "https://example.org/inicio"

    casos = [
        (
            "DNS estable",
            ["8.8.8.8"],
            ["8.8.8.8"]
        ),
        (
            "Cambio de IP publica",
            ["8.8.8.8"],
            ["1.1.1.1"]
        ),
        (
            "Cambio a IP privada",
            ["8.8.8.8"],
            ["192.168.1.10"]
        ),
        (
            "Cambio de orden",
            ["8.8.8.8", "1.1.1.1"],
            ["1.1.1.1", "8.8.8.8"]
        )
    ]

    print("\nMOONDETEX - CLASE 35")
    print("VERIFICACION DNS EN DOS ETAPAS")
    print("==============================")

    for nombre, iniciales, actuales in casos:

        # Simular dos respuestas consecutivas
        respuestas = iter((iniciales, actuales))

        def resolver_simulado(dominio):
            return next(respuestas)

        try:
            resultado = verificar_dns_estable(
                url,
                dominios,
                puertos,
                resolver_simulado
            )

            print("\nPERMITIDO:", nombre)
            print("IP verificadas:", resultado["ips"])

        except ValueError as error:

            print("\nRECHAZADO:", nombre)
            print("Motivo:", error)

