from urllib.parse import urlsplit

from validador_alcance_v32 import validar_objetivo


# =====================================
# MOONDETEX - CLASE 34
# CONTROL DE PUERTOS AUTORIZADOS
# =====================================

def validar_puerto_objetivo(
    url,
    dominios_permitidos,
    puertos_permitidos
):

    # Comprobar primero el dominio
    validar_objetivo(
        url,
        dominios_permitidos
    )

    # Comprobar la lista de puertos autorizados
    if (
        not isinstance(puertos_permitidos, (set, list, tuple))
        or not puertos_permitidos
    ):
        raise ValueError(
            "No hay puertos autorizados validos."
        )

    for puerto_permitido in puertos_permitidos:

        if (
            type(puerto_permitido) is not int
            or not 1 <= puerto_permitido <= 65535
        ):
            raise ValueError(
                "La lista contiene un puerto invalido."
            )

    # Obtener el puerto de la URL
    partes = urlsplit(url.strip())

    puerto = partes.port

    # Usar el puerto predeterminado
    if puerto is None:

        if partes.scheme == "https":
            puerto = 443

        else:
            puerto = 80

    # Comprobar autorización
    if puerto not in puertos_permitidos:
        raise ValueError(
            f"Puerto no autorizado: {puerto}"
        )

    return puerto


# =====================================
# LABORATORIO LOCAL
# =====================================

if __name__ == "__main__":

    dominios = {"example.org"}
    puertos = {443}

    objetivos = [
        "https://example.org",
        "https://example.org:443",
        "http://example.org",
        "https://example.org:8080",
        "https://otro-dominio.org"
    ]

    print("\nMOONDETEX - CLASE 34")
    print("CONTROL DE PUERTOS")
    print("==============================")

    for url in objetivos:

        try:
            puerto = validar_puerto_objetivo(
                url,
                dominios,
                puertos
            )

            print("PERMITIDO:", url)
            print("Puerto:", puerto)

        except ValueError as error:

            print("RECHAZADO:", url)
            print("Motivo:", error)
