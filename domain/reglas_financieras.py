# domain/reglas_financieras.py

def evaluar_precios(ingreso_promedio, umbral_bajo=8000):
    """
    Detecta si el ingreso promedio por turno es bajo.
    """
    if ingreso_promedio < umbral_bajo:
        return {
            "nivel": "alerta",
            "mensaje": (
                f"⚠️ Ingreso promedio por turno bajo (${ingreso_promedio}). "
                "Evaluá ajustar precios o reducir descuentos."
            )
        }

    return {
        "nivel": "ok",
        "mensaje": "✅ Ingreso promedio por turno dentro de valores esperados."
    }


def evaluar_retencion_espacio(participacion_pct, umbral_alto=45):
    """
    Detecta si el espacio se queda con demasiado porcentaje.
    """
    if participacion_pct > umbral_alto:
        return {
            "nivel": "alerta",
            "mensaje": (
                f"⚠️ El espacio retiene {participacion_pct}% del ingreso. "
                "Podría estar afectando la rentabilidad profesional."
            )
        }

    return {
        "nivel": "ok",
        "mensaje": "✅ Participación del espacio equilibrada."
    }


def evaluar_cobranza(total_facturado, total_cobrado):
    """
    Analiza eficiencia de cobranza.
    """
    if total_facturado == 0:
        return {
            "nivel": "info",
            "mensaje": "ℹ️ Sin facturación registrada este mes."
        }

    ratio = total_cobrado / total_facturado

    if ratio < 0.85:
        return {
            "nivel": "critico",
            "mensaje": (
                f"🚨 Solo se cobró el {int(ratio * 100)}% de lo facturado. "
                "Revisar seguimiento de pagos y políticas de cobranza."
            )
        }

    return {
        "nivel": "ok",
        "mensaje": "✅ Cobranza saludable."
    }


def generar_recomendaciones_financieras(
    ingreso_promedio,
    participacion_pct,
    total_facturado,
    total_cobrado
):
    """
    Consolida todas las reglas y devuelve recomendaciones accionables.
    """
    recomendaciones = []

    r1 = evaluar_precios(ingreso_promedio)
    r2 = evaluar_retencion_espacio(participacion_pct)
    r3 = evaluar_cobranza(total_facturado, total_cobrado)

    for r in (r1, r2, r3):
        if r["nivel"] in ("alerta", "critico"):
            recomendaciones.append(r["mensaje"])

    return recomendaciones
