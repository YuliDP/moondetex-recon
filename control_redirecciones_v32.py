from urllib.parse import urljoin

from validador_alcance_v32 import validar_objetivo


# =====================================
# MOONDETEX - CLASE 32
# CONTROL DE REDIRECCIONES
# =====================================

def validar_redireccion(
    url_actual,
    destino,
    dominios_permitidos
):

    # Comprobar la direccion de origen
    validar_objetivo(
        url_actual,
        dominios_permitidos
    )

    if not isinstance(destino, str) or not destino.strip():
        raise ValueError(
            "La redireccion no contiene un destino valido."
        )

    # Rechazar caracteres de control
    if any(
        ord(caracter) < 32 or ord(caracter) == 127
        for caracter in destino
    ):
        raise ValueError(
            "La redireccion contiene caracteres ocultos."
        )

    # Convertir rutas relativas en URL completas
    nueva_url = urljoin(
        url_actual,
        destino.strip()
    )

    # Comprobar el destino antes de continuar
    validar_objetivo(
        nueva_url,
        dominios_permitidos
    )

    return nueva_url


# =====================================
# LABORATORIO LOCAL
# =====================================

if __name__ == "__main__":

    permitidos = {"example.org"}

    origen = "https://example.org/inicio"

    destinos = [
        "/documentacion",
        "https://example.org/ayuda",
        "https://otro-dominio.org",
        "//admin.example.org/panel"
    ]

    print("\nMOONDETEX - CLASE 32")
    print("CONTROL DE REDIRECCIONES")
    print("==============================")

    for destino in destinos:

        try:
            resultado = validar_redireccion(
                origen,
                destino,
                permitidos
            )

            print("\nPERMITIDO:", resultado)

        except ValueError as error:

            print("\nRECHAZADO:", destino)
            print("Motivo:", error)
