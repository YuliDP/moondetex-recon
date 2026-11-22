from urllib.parse import urlsplit

from validador_alcance_v32 import validar_objetivo
from validador_dns_v33 import validar_ips_resueltas


# =====================================
# MOONDETEX - CLASE 34
# RESOLUCION DNS CONTROLADA
# =====================================

def comprobar_resolucion(url, permitidos, resolver):

    # Verificar primero el dominio autorizado
    validar_objetivo(url, permitidos)

    # Obtener el dominio de la URL
    dominio = urlsplit(url.strip()).hostname
    dominio = dominio.lower().rstrip(".")

   
    # Obtener las IP del resolutor
    try:
        direcciones = resolver(dominio)

    except OSError as error:
        raise ValueError(
            f"No se pudo resolver el dominio: {dominio}"
        ) from error

    # Comprobar todas las IP recibidas
    validar_ips_resueltas(direcciones)

    return direcciones


# =====================================
# SIMULADOR DNS LOCAL
# =====================================

def resolver_simulado(dominio):

    respuestas = {
        "example.org": ["8.8.8.8"],
        "example.net": [
            "8.8.8.8",
            "192.168.1.10"
        ]
    }

    return respuestas.get(dominio, [])


# =====================================
# LABORATORIO
# =====================================

if __name__ == "__main__":


    # SIMULAR UN ERROR DE RESOLUCION DNS

    print("\nSIMULACION DE ERROR DNS")
    print("==============================")

    def resolver_con_error(dominio):
        raise OSError("Servicio DNS no disponible")

    
    try:
        comprobar_resolucion(
            "https://example.org/inicio",
            {"example.org"},
            resolver_con_error
        )



    except ValueError as error:
        print("ERROR DNS CONTROLADO")
        print("Motivo:", error)




    permitidos = {
        "example.org",
        "example.net"
    }

    objetivos = [
        "https://example.org/inicio",
        "https://example.net/inicio"
    ]

    print("\nMOONDETEX - CLASE 34")
    print("RESOLUCION DNS CONTROLADA")
    print("==============================")

    for url in objetivos:

        try:
            ips = comprobar_resolucion(
                url,
                permitidos,
                resolver_simulado
            )

            print("PERMITIDO:", url)
            print("IP verificadas:", ips)

        except ValueError as error:
            print("RECHAZADO:", url)
            print("Motivo:", error)
