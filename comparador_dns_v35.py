from ipaddress import ip_address

from validador_dns_v33 import validar_ips_resueltas


# =====================================
# MOONDETEX - CLASE 35
# COMPARADOR DE RESPUESTAS DNS
# =====================================

def comparar_respuestas_dns(
    ips_iniciales,
    ips_actuales
):

    # Validar ambas respuestas
    validar_ips_resueltas(ips_iniciales)
    validar_ips_resueltas(ips_actuales)

    # Normalizar las direcciones IP
    anteriores = {
        ip_address(ip.strip())
        for ip in ips_iniciales
    }

    actuales = {
        ip_address(ip.strip())
        for ip in ips_actuales
    }

    # Detectar cambios
    if anteriores != actuales:
        raise ValueError(
            "Las respuestas DNS cambiaron."
        )

    return True


# =====================================
# LABORATORIO LOCAL
# =====================================

if __name__ == "__main__":

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
    print("COMPARADOR DNS")
    print("==============================")

    for nombre, iniciales, actuales in casos:

        try:
            comparar_respuestas_dns(
                iniciales,
                actuales
            )

            print("PERMITIDO:", nombre)

        except ValueError as error:

            print("RECHAZADO:", nombre)
            print("Motivo:", error)
