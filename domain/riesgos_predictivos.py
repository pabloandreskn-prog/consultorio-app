from collections import defaultdict


def tendencia_facturacion(cierres, meses=3):
    """
    Detecta caída sostenida de facturación en los últimos N meses
    """
    if len(cierres) < meses:
        return None

    ultimos = sorted(cierres, key=lambda x: x["mes"])[-meses:]
    valores = [c["total_facturado"] for c in ultimos]

    if all(valores[i] > valores[i + 1] for i in range(len(valores) - 1)):
        return {
            "nivel": "rojo",
            "mensaje": "La facturación viene cayendo de forma sostenida",
            "detalle": valores
        }

    return None


def brecha_cobranza(cierres, umbral_pct=15):
    """
    Detecta aumento peligroso en la diferencia entre facturado y cobrado
    """
    alertas = []

    for c in cierres:
        facturado = c["total_facturado"]
        diferencia = c["diferencia"]

        if facturado > 0:
            pct = (diferencia / facturado) * 100
            if pct >= umbral_pct:
                alertas.append(
                    f"En {c['mes']} la diferencia fue del {pct:.1f}%"
                )

    if alertas:
        return {
            "nivel": "amarillo",
            "mensaje": "Brecha elevada entre facturación y cobranza",
            "detalle": alertas
        }

    return None


def dependencia_servicios(filas_detalle, umbral_pct=60):
    """
    Riesgo si un solo servicio concentra demasiado ingreso
    """
    totales = defaultdict(float)
    total_general = 0

    for f in filas_detalle:
        totales[f["servicio"]] += f["precio"]
        total_general += f["precio"]

    for servicio, monto in totales.items():
        pct = (monto / total_general) * 100 if total_general else 0
        if pct >= umbral_pct:
            return {
                "nivel": "amarillo",
                "mensaje": f"Alta dependencia del servicio '{servicio}'",
                "detalle": f"{pct:.1f}% del ingreso total"
            }

    return None


def meses_en_rojo(historial_salud, consecutivos=2):
    """
    Detecta meses consecutivos con salud financiera mala
    """
    contador = 0

    for estado in historial_salud:
        if estado == "rojo":
            contador += 1
            if contador >= consecutivos:
                return {
                    "nivel": "rojo",
                    "mensaje": f"{contador} meses consecutivos en rojo",
                    "detalle": "Riesgo financiero estructural"
                }
        else:
            contador = 0

    return None
