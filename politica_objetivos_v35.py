
# =====================================
# MOONDETEX - CLASE 35
# POLITICA DE OBJETIVOS
# =====================================
from urllib.parse import urlsplit
from verificador_preconexion_v35 import verificar_destino


def aplicar_politica_local(url, politica, resolver):

    # Comprobar que exista una politica
    if not isinstance(politica, dict):
        raise ValueError(
            "La politica debe ser un diccionario."
        )

    dominios = politica.get("dominios")
    puertos = politica.get("puertos")
    protocolos = politica.get("protocolos")

    # Comprobar que existan dominios
    if (
        not isinstance(dominios, (set, list, tuple))
        or not dominios
    ):
        raise ValueError(
            "La politica no contiene dominios validos."
        )

    # Comprobar que existan puertos
    if (
        not isinstance(puertos, (set, list, tuple))
        or not puertos
    ):
        raise ValueError(
            "La politica no contiene puertos validos."
        )

    # =====================================
    # VALIDAR PROTOCOLOS AUTORIZADOS
    # =====================================

    if (
        not isinstance(protocolos, (set, list, tuple))
        or not protocolos
        or any(
            protocolo not in ("http", "https")
            for protocolo in protocolos
        )
    ):
        raise ValueError(
            "La politica no contiene protocolos validos."
        )

    if not isinstance(url, str):
        raise ValueError(
            "La URL debe ser texto."
        )

    protocolo_url = urlsplit(url.strip()).scheme

    if protocolo_url not in protocolos:
        raise ValueError(
            f"Protocolo no autorizado: {protocolo_url}"
        )


    # Aplicar las comprobaciones existentes
    return verificar_destino(
        url,
        dominios,
        puertos,
        resolver
    )

# =====================================
# LABORATORIO LOCAL
# =====================================

if __name__ == "__main__":

   
    politica = {
        "dominios": {"example.org"},
        "puertos": {443},
        "protocolos": {"https"}
    }


    def resolver_simulado(dominio):
        respuestas = {
            "example.org": ["8.8.8.8"]
        }
        return respuestas.get(dominio, [])

    objetivos = [
        "https://example.org/inicio",
        "http://example.org:443",
        "http://example.org",
        "https://example.org:8080",
        "https://otro-dominio.org"
    ]

    print("\nMOONDETEX - CLASE 35")
    print("POLITICA DE OBJETIVOS")
    print("==============================")

    for url in objetivos:

        try:
            resultado = aplicar_politica_local(
                url,
                politica,
                resolver_simulado
            )

            print("\nPERMITIDO:", url)
            print("Puerto:", resultado["puerto"])
            print("IP:", resultado["ips"])

        except ValueError as error:

            print("\nRECHAZADO:", url)
            print("Motivo:", error)

