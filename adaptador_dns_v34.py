import socket
from ipaddress import ip_address

from validador_dns_v33 import validar_ips_resueltas


# =====================================
# MOONDETEX - CLASE 34
# ADAPTADOR DE RESPUESTAS DNS
# =====================================

def extraer_ips_dns(registros):

    if not isinstance(registros, (list, tuple)) or not registros:
        raise ValueError(
            "No se recibieron registros DNS validos."
        )

    direcciones = []

    for registro in registros:

        if not isinstance(registro, tuple) or len(registro) != 5:
            raise ValueError(
                "Formato de registro DNS incorrecto."
            )

        familia, tipo, protocolo, nombre, destino = registro

        if familia not in (socket.AF_INET, socket.AF_INET6):
            raise ValueError(
                "Familia de direccion no admitida."
            )

       
        # Comprobar la estructura del destino DNS
        if not isinstance(destino, tuple):
            raise ValueError(
                "Destino DNS incorrecto."
            )

        # IPv4 debe contener exactamente 2 elementos
        if familia == socket.AF_INET and len(destino) != 2:
            raise ValueError(
                "Formato IPv4 incorrecto."
            )

        # IPv6 debe contener exactamente 4 elementos
        if familia == socket.AF_INET6 and len(destino) != 4:
            raise ValueError(
                "Formato IPv6 incorrecto."
            )
        
        # =====================================
        # VALIDAR TIPO DE CONEXION Y PROTOCOLO
        # =====================================

        if tipo != socket.SOCK_STREAM:
            raise ValueError(
                "Tipo de conexion no permitido."
            )

        if protocolo != socket.IPPROTO_TCP:
            raise ValueError(
                "Protocolo de conexion no permitido."
            )

        # =====================================
        # VALIDAR PUERTO
        # =====================================

        puerto = destino[1]

        if type(puerto) is not int:
            raise ValueError(
                "El puerto debe ser un numero entero."
            )

        if not 1 <= puerto <= 65535:
            raise ValueError(
                "Puerto fuera del rango permitido."
            )



        try:
            ip = ip_address(destino[0])
        except (ValueError, TypeError):
            raise ValueError(
                "El registro contiene una IP invalida."
            ) from None

        # Comprobar que IPv4 e IPv6 coincidan
        if familia == socket.AF_INET and ip.version != 4:
            raise ValueError(
                "La familia IPv4 no coincide con la IP."
            )

        if familia == socket.AF_INET6 and ip.version != 6:
            raise ValueError(
                "La familia IPv6 no coincide con la IP."
            )

        direcciones.append(str(ip))

    # Aplicar nuestro validador de seguridad
    validar_ips_resueltas(direcciones)

    # Eliminar duplicados sin alterar el orden
    return list(dict.fromkeys(direcciones))


# =====================================
# LABORATORIO SIN INTERNET
# =====================================

if __name__ == "__main__":

    casos = [
        (
            "IP global",
            [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("8.8.8.8", 443)
                )
            ]
        ),
        (
            "IP local",
            [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("127.0.0.1", 443)
                )
            ]
        )
    ]

    print("\nMOONDETEX - CLASE 34")
    print("ADAPTADOR DNS")
    print("==============================")

    for nombre, registros in casos:

        try:
            ips = extraer_ips_dns(registros)
            print("PERMITIDO:", nombre, ips)

        except ValueError as error:
            print("RECHAZADO:", nombre)
            print("Motivo:", error)
