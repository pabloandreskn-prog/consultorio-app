from collections import defaultdict


def ingreso_por_dia(filas_detalle):
    ingresos = defaultdict(float)

    for f in filas_detalle:
        fecha = f["fecha"]
        ingresos[fecha] += f["neto"]

    if not ingresos:
        return None

    promedio = sum(ingresos.values()) / len(ingresos)

    dias_bajos = [
        d for d, v in ingresos.items()
        if v < promedio * 0.6
    ]

    return {
        "promedio_diario": round(promedio, 2),
        "dias_bajos": dias_bajos
    }


def servicios_subutilizados(filas_detalle, umbral_turnos=3):
    conteo = defaultdict(int)

    for f in filas_detalle:
        conteo[f["servicio"]] += 1

    return [
        s for s, c in conteo.items()
        if c <= umbral_turnos
    ]


def eficiencia_turnos(filas_detalle):
    total = len(filas_detalle)
    evaluaciones = sum(
        1 for f in filas_detalle
        if "Evaluación" in f["detalle"]
    )

    return {
        "total_turnos": total,
        "evaluaciones_pct": round((evaluaciones / total) * 100, 1) if total else 0
    }
