import re

# MOONDETEX V0.7
# Motor de análisis HTTP sin conexión

REGLAS = [
    ("csp", "Política CSP"),
    ("marcos", "Protección de marcos"),
    ("nosniff", "Control de tipos MIME"),
]


def extraer_cabeceras(texto):
    lineas = texto.replace("\r\n", "\n").split("\n")

    patron = r"^HTTP/(?:1\.[01]|[23])\s+\d{3}(?:\s|$)"

    if not lineas or not re.match(
        patron,
        lineas[0].strip(),
        re.IGNORECASE
    ):
        raise ValueError(
            "El texto debe comenzar con "
            "HTTP/1.1 200 OK o similar."
        )

    cabeceras = {}

    for linea in lineas[1:]:
        if not linea.strip():
            break

        if ":" not in linea:
            raise ValueError(
                "Cabecera incorrecta: " + linea[:70]
            )

        nombre, valor = linea.split(":", 1)
        nombre = nombre.strip().lower()

        if not re.fullmatch(
            r"[a-z0-9!#$%&'*+.^_`|~-]+",
            nombre
        ):
            raise ValueError(
                "Nombre de cabecera no válido."
            )

        cabeceras[nombre] = valor.strip()

    if "content-type" not in cabeceras:
        raise ValueError(
            "Falta la cabecera Content-Type."
        )

    return cabeceras


def evaluar(texto):
    cab = extraer_cabeceras(texto)

    tipo = cab["content-type"].split(";", 1)[0].strip().lower()

    if tipo != "text/html":
        return {
            clave: None
            for clave, _ in REGLAS
        }

    csp = cab.get(
        "content-security-policy", ""
    )

    directivas = [
        x.strip().lower()
        for x in csp.split(";")
    ]

    # Una directiva sin valor no cuenta
    frame_ancestors = any(
        x.startswith("frame-ancestors ")
        and bool(
            x[len("frame-ancestors "):].strip()
        )
        for x in directivas
    )

    xframe = cab.get(
        "x-frame-options", ""
    ).upper()

    marcos = (
        frame_ancestors
        or xframe in ("DENY", "SAMEORIGIN")
    )

    nosniff = cab.get(
        "x-content-type-options", ""
    ).lower() == "nosniff"

    return {
        
        
        "csp": any(
            parte.strip().split()[0] in {
                "default-src",
                "script-src",
                "style-src",
                "img-src",
                "connect-src",
                "font-src",
                "object-src",
                "base-uri",
                "form-action",
                "frame-ancestors",
                "frame-src",
                "child-src",
                "worker-src",
                "media-src",
                "manifest-src",
                "sandbox",
                "upgrade-insecure-requests",
                "script-src-elem",
                "script-src-attr",
                "style-src-elem",
                "style-src-attr",
                "trusted-types",
                "require-trusted-types-for"
            }
            for parte in csp.lower().split(";")
            if parte.strip()
        ),

        "marcos": bool(marcos),
        "nosniff": nosniff
    }


def analizar(texto):
    estados = evaluar(texto)

    detalles = {
        "csp":
            "No se observó Content-Security-Policy.",

        "marcos":
            "No se observó una restricción "
            "de marcos reconocida en las cabeceras.",

        "nosniff":
            "No se observó "
            "X-Content-Type-Options: nosniff."
    }

   
    observaciones = [
        (
            clave,
            titulo + " por revisar",
            detalles[clave]
        )
        for clave, titulo in REGLAS
        if estados[clave] is False
    ]

    # Agregar advertencias sobre CSP permisivas
    avisos_csp = revisar_csp(texto)

    for numero, aviso in enumerate(avisos_csp, start=1):

        # La ausencia de CSP ya fue detectada
        if aviso == "No se observó la cabecera CSP.":
            continue

        observaciones.append((
            f"csp_aviso_{numero}",
            "Configuración CSP por revisar",
            aviso
        ))

    return observaciones



def comparar(antes, despues):
    estado_antes = evaluar(antes)
    estado_despues = evaluar(despues)

    resultados = []

    for clave, titulo in REGLAS:
        a = estado_antes[clave]
        d = estado_despues[clave]

        if a is None or d is None:
            estado = "No comparable"

        elif not a and d:
            estado = "Mejora observada"

        elif a and not d:
            estado = "Posible regresión"

        elif not a and not d:
            estado = "Pendiente de revisión"

        else:
            estado = "Presente en ambas muestras"

        resultados.append({
            "control": titulo,
            "estado": estado
        })

    return resultados


# =====================================
# MOONDETEX V0.10
# REVISION DE POLITICAS CSP
# =====================================

def revisar_csp(texto):

    cabeceras = extraer_cabeceras(texto)

    tipo = cabeceras["content-type"].split(
        ";", 1
    )[0].strip().lower()

    # Solo revisar documentos HTML
    if tipo != "text/html":
        return []

    politica = cabeceras.get(
        "content-security-policy", ""
    ).strip()

    if not politica:
        return ["No se observó la cabecera CSP."]

    avisos = []

    for fragmento in politica.split(";"):

        partes = fragmento.strip().lower().split()

        if not partes:
            continue

        directiva, *fuentes = partes

        if directiva in ("default-src", "script-src"):
            if "*" in fuentes:

                avisos.append(
                    f"Fuente comodín (*) en {directiva}: "
                    "revisar si es necesaria."
                )

    return avisos
