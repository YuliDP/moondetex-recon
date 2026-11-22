from urllib.parse import urlsplit
from ipaddress import ip_address


# =====================================
# MOONDETEX - CLASE 32
# VALIDADOR DE ALCANCE
# =====================================

def validar_objetivo(url, dominios_permitidos):

    if not isinstance(url, str) or not url.strip():
        raise ValueError("La URL no puede estar vacia.")
    
    # Rechazar caracteres de control ocultos
    if any(ord(caracter) < 32 or ord(caracter) == 127
           for caracter in url):
        raise ValueError(
            "La URL contiene caracteres de control."
        )

    url = url.strip()

    # Separar los componentes de la URL
    try:
        partes = urlsplit(url)
        dominio = partes.hostname
        puerto = partes.port

    except ValueError:
        raise ValueError("La URL no es valida.")

    # Admitir solamente HTTP y HTTPS
    if partes.scheme not in ("http", "https"):
        raise ValueError("Protocolo no permitido.")

    if not dominio:
        raise ValueError("La URL no contiene un dominio.")
    
    # BLOQUEAR DIRECCIONES IP DIRECTAS

    try:
        ip_address(dominio)

    except ValueError:
        # No es una direccion IP reconocida
        pass

    else:
        raise ValueError(
            "No se permiten direcciones IP directas."
        )


    # Evitar credenciales dentro de la URL
    if partes.username is not None or partes.password is not None:
        raise ValueError("No se admiten credenciales en la URL.")

    # Normalizar los dominios autorizados
    permitidos = {
        nombre.strip().lower().rstrip(".")
        for nombre in dominios_permitidos
    }

    dominio = dominio.lower().rstrip(".")

    # Comprobar coincidencia exacta
    if dominio not in permitidos:
        raise ValueError(
            "El dominio no esta en el alcance permitido."
        )

    return True


# =====================================
# PRUEBAS DE LABORATORIO
# =====================================

if __name__ == "__main__":

    permitidos = {"example.org"}

    direcciones = [
        "https://example.org/prueba",
        "https://example.org.falso.net",
        "ftp://example.org/archivo",
        "https://otro-dominio.org"
    ]

    print("\nMOONDETEX - CLASE 32")
    print("VALIDADOR DE ALCANCE")
    print("==============================")

    for direccion in direcciones:

        try:
            validar_objetivo(
                direccion,
                permitidos
            )

            print("PERMITIDO:", direccion)

        except ValueError as error:

            print("RECHAZADO:", direccion)
            print("Motivo:", error)
