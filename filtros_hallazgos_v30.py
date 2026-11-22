# =====================================
# MOONDETEX - CLASE 30
# FILTROS DE HALLAZGOS
# =====================================

ESTADOS_VALIDOS = (
    "Todos",
    "Pendiente",
    "Revisado",
    "Descartado"
)


def filtrar_hallazgos(filas, estado="Todos"):

    if estado not in ESTADOS_VALIDOS:
        raise ValueError(
            "El estado seleccionado no es valido."
        )

    if estado == "Todos":
        return list(filas)

    resultados = []

    for hallazgo in filas:

        if hallazgo[5] == estado:
            resultados.append(hallazgo)

    return resultados


# =====================================
# PRUEBA CON DATOS FICTICIOS
# =====================================

if __name__ == "__main__":

    datos_prueba = [
        (
            1, "Laboratorio", "Control MIME",
            "", "2026-10-25", "Pendiente"
        ),
        (
            2, "Laboratorio", "Control CSP",
            "", "2026-10-25", "Revisado"
        ),
        (
            3, "Laboratorio", "Proteccion de marcos",
            "", "2026-10-25", "Descartado"
        )
    ]

    print("\nMOONDETEX - CLASE 30")
    print("==============================")

    for estado in ESTADOS_VALIDOS:

        encontrados = filtrar_hallazgos(
            datos_prueba,
            estado
        )

        print(
            f"{estado}: {len(encontrados)}"
        )
