
from motor_http import evaluar

# =====================================
# MOONDETEX - METRICAS V0.7
# =====================================

# Crear una respuesta HTTP de laboratorio
def respuesta(*cabeceras):
    return (
        "HTTP/1.1 200 OK\n"
        + "\n".join(cabeceras)
        + "\n"
    )


# True = esperamos una alerta
# False = no esperamos una alerta

CASOS = [
    (
        "HTML sin controles",
        respuesta(
            "Content-Type: text/html"
        ),
        {
            "csp": True,
            "marcos": True,
            "nosniff": True
        }
    ),

    (
        "HTML con controles",
        respuesta(
            "Content-Type: text/html",
            "Content-Security-Policy: "
            "default-src 'self'; frame-ancestors 'none'",
            "X-Content-Type-Options: nosniff"
        ),
        {
            "csp": False,
            "marcos": False,
            "nosniff": False
        }
    ),

    (
        "HTML solo con CSP",
        respuesta(
            "Content-Type: text/html",
            "Content-Security-Policy: default-src 'self'"
        ),
        {
            "csp": False,
            "marcos": True,
            "nosniff": True
        }
    ),

    (
        "HTML con X-Frame y nosniff",
        respuesta(
            "Content-Type: text/html",
            "X-Frame-Options: SAMEORIGIN",
            "X-Content-Type-Options: nosniff"
        ),
        {
            "csp": True,
            "marcos": False,
            "nosniff": False
        }
    ),

    (
        "HTML con CSP y nosniff",
        respuesta(
            "Content-Type: text/html",
            "Content-Security-Policy: default-src 'self'",
            "X-Content-Type-Options: nosniff"
        ),
        {
            "csp": False,
            "marcos": True,
            "nosniff": False
        }
    ),

    (
        "Respuesta JSON",
        respuesta(
            "Content-Type: application/json"
        ),
        {
            "csp": False,
            "marcos": False,
            "nosniff": False
        }
    ),

    (
        "JSON con texto engañoso",
        respuesta(
            'Content-Type: application/json; '
            'note="text/html"'
        ),
        {
            "csp": False,
            "marcos": False,
            "nosniff": False
        }
    ),

    (
        "HTML solo con nosniff",
        respuesta(
            "Content-Type: text/html",
            "X-Content-Type-Options: nosniff"
        ),
        {
            "csp": True,
            "marcos": True,
            "nosniff": False
        }
    )
]


# =====================================
# CONTADORES
# =====================================

vp = 0
fp = 0
fn = 0
vn = 0

print("\n===== MOONDETEX V0.7 =====")
print("EVALUACION DEL MOTOR HTTP\n")


# =====================================
# ANALIZAR CASOS DE PRUEBA
# =====================================

for nombre, texto, esperado in CASOS:

    resultado = evaluar(texto)

    print(f"\nCaso: {nombre}")

    for control, valor_esperado in esperado.items():

        valor_detectado = (
            resultado[control] is False
        )

        if valor_detectado and valor_esperado:
            vp += 1

        elif valor_detectado and not valor_esperado:
            fp += 1
            print(f"  FALSO POSITIVO: {control}")

        elif not valor_detectado and valor_esperado:
            fn += 1
            print(f"  FALSO NEGATIVO: {control}")

        else:
            vn += 1


# =====================================
# CALCULAR METRICAS
# =====================================

precision = (
    vp / (vp + fp) * 100
    if vp + fp > 0 else 0
)

sensibilidad = (
    vp / (vp + fn) * 100
    if vp + fn > 0 else 0
)

tasa_fp = (
    fp / (fp + vn) * 100
    if fp + vn > 0 else 0
)


# =====================================
# MOSTRAR RESULTADOS
# =====================================

print("\n===========================")
print("RESULTADOS DE MOONDETEX")
print("===========================")

print(f"Verdaderos positivos: {vp}")
print(f"Falsos positivos: {fp}")
print(f"Falsos negativos: {fn}")
print(f"Verdaderos negativos: {vn}")

print("\nMETRICAS:")

print(f"Precision: {precision:.2f}%")
print(f"Sensibilidad: {sensibilidad:.2f}%")
print(f"Tasa de falsos positivos: {tasa_fp:.2f}%")

print("\nNOTA:")
print("Resultados de muestras sinteticas.")
print("No representan vulnerabilidades reales.")
