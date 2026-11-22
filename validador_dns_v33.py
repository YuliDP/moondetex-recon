from ipaddress import ip_address


# =====================================
# MOONDETEX - CLASE 33 (BLINDADO)
# VALIDADOR DE DIRECCIONES DNS
# =====================================

def validar_ips_resueltas(direcciones):

    # Comprobar que recibimos una coleccion valida y no vacia
    if not isinstance(direcciones, (list, tuple, set)):
        raise ValueError(
            "Las direcciones deben estar en una lista."
        )

    if not direcciones:
        raise ValueError(
            "No se recibieron direcciones IP."
        )

    for texto in direcciones:

        if not isinstance(texto, str) or not texto:
            raise ValueError(
                "Se encontro una direccion IP vacia o no textual."
            )

        # Rechazar espacios o saltos de linea ocultos
        if texto != texto.strip():
            raise ValueError(
                f"Direccion IP con espacios no permitidos: {texto!r}"
            )

        # Comprobar que la IP sea sintacticamente valida
        try:
            ip = ip_address(texto)
        except ValueError:
            raise ValueError(
                f"Direccion IP invalida: {texto}"
            ) from None

        # Bloquear vectores especificos de IPv6 (zonas locales y tuneles)
        if ip.version == 6:
            if ip.scope_id is not None:
                raise ValueError(
                    f"Direccion IPv6 con zona de interfaz no permitida: {ip}"
                )

            if (
                ip.ipv4_mapped is not None
                or ip.sixtofour is not None
                or ip.teredo is not None
            ):
                raise ValueError(
                    f"Direccion IPv6 mapeada o tunelizada no permitida: {ip}"
                )

        # Rechazar IP privadas, locales, metadatos cloud, multicast o reservadas
        if (
            not ip.is_global
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_reserved
        ):
            raise ValueError(
                f"Direccion IP no permitida: {ip}"
            )

    return True


# =====================================
# LABORATORIO LOCAL
# =====================================

if __name__ == "__main__":

    casos = [
        ("IP publica", ["8.8.8.8"]),
        ("IPv6 publica nativa", ["2606:4700:4700::1111"]),
        ("IP privada", ["192.168.1.10"]),
        ("IP local", ["127.0.0.1"]),
        ("Metadatos cloud", ["169.254.169.254"]),
        ("CGNAT", ["100.64.0.1"]),
        ("IPv6 local", ["::1"]),
        ("IPv6 mapeada a IPv4", ["::ffff:8.8.8.8"]),
        ("IPv6 con zona local", ["2001:4860:4860::8888%lo"]),
        ("IP con salto de linea", ["8.8.8.8\n"]),
        ("DNS mixto", ["8.8.8.8", "10.0.0.5"])
    ]

    print("\nMOONDETEX - CLASE 33 (BLINDADO)")
    print("VALIDACION DE DIRECCIONES DNS")
    print("==============================")

    for nombre, direcciones in casos:

        try:
            validar_ips_resueltas(direcciones)
            print(f"PERMITIDO: {nombre}")

        except ValueError as error:
            print(f"RECHAZADO: {nombre}")
            print(f"Motivo: {error}")