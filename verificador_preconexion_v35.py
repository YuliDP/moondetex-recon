# =====================================
# MOONDETEX - CLASE 35
# VERIFICADOR PREVIO A LA CONEXION
# =====================================

from validador_alcance_v32 import validar_objetivo
from control_puertos_v34 import validar_puerto_objetivo
from resolver_dns_v34 import comprobar_resolucion
from control_redirecciones_v32 import validar_redireccion


def verificar_destino(
    url,
    dominios_permitidos,
    puertos_permitidos,
    resolver
):

    # 1. Validar el dominio
    validar_objetivo(
        url,
        dominios_permitidos
    )

    # 2. Validar el puerto
    puerto = validar_puerto_objetivo(
        url,
        dominios_permitidos,
        puertos_permitidos
    )

    # 3. Validar las respuestas DNS
    direcciones = comprobar_resolucion(
        url,
        dominios_permitidos,
        resolver
    )

    return {
        "url": url,
        "puerto": puerto,
        "ips": direcciones
    }


def verificar_cadena_local(
    url,
    dominios_permitidos,
    puertos_permitidos,
    resolver,
    redireccion=None
):

    # Verificar el objetivo inicial
    resultados = [
        verificar_destino(
            url,
            dominios_permitidos,
            puertos_permitidos,
            resolver
        )
    ]

    # Si existe una redireccion, verificarla
    if redireccion is not None:

        nueva_url = validar_redireccion(
            url,
            redireccion,
            dominios_permitidos
        )

        resultados.append(
            verificar_destino(
                nueva_url,
                dominios_permitidos,
                puertos_permitidos,
                resolver
            )
        )

    return resultados


# =====================================
# LABORATORIO LOCAL SIN INTERNET
# =====================================

if __name__ == "__main__":

    dominios = {"example.org"}
    puertos = {443}

    def resolver_simulado(dominio):
        respuestas = {
            "example.org": ["8.8.8.8"]
        }
        return respuestas.get(dominio, [])

    casos = [
        ("Objetivo permitido", None),
        ("Redireccion permitida", "/ayuda"),
        ("Dominio externo", "https://otro-dominio.org"),
        ("Puerto no autorizado", "https://example.org:8080")
    ]

    print("\nMOONDETEX - CLASE 35")
    print("VERIFICADOR PREVIO A LA CONEXION")
    print("==============================")

    for nombre, redireccion in casos:

        try:
            resultados = verificar_cadena_local(
                "https://example.org/inicio",
                dominios,
                puertos,
                resolver_simulado,
                redireccion
            )

            print("\nPERMITIDO:", nombre)

            for resultado in resultados:
                print("URL:", resultado["url"])
                print("Puerto:", resultado["puerto"])
                print("IP:", resultado["ips"])

        except ValueError as error:
            print("\nRECHAZADO:", nombre)
            print("Motivo:", error)
