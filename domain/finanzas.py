import pandas as pd

def resumen_financiero(turnos, pagos):
    df_turnos = pd.DataFrame(turnos)
    df_pagos = pd.DataFrame(pagos)

    pagos_sum = (
        df_pagos.groupby("id_turno")["monto"]
        .sum()
        .reset_index()
    )

    df = df_turnos.merge(pagos_sum, on="id_turno", how="left")
    df["monto"].fillna(0, inplace=True)

    df["deuda"] = df["precio"] - df["monto"]

    return df

from datetime import datetime

def es_pago_duplicado(pagos, paciente, mes, monto, fecha):
    for p in pagos:
        if (
            p.get("paciente") == paciente and
            p.get("mes") == mes and
            str(p.get("monto")) == str(monto) and
            p.get("fecha") == fecha
        ):
            return True
    return False

def calcular_participacion_turno(
    turno,
    paciente,
    es_primera_evaluacion,
):
    precio = float(turno.get("precio", 0))
    tipo = paciente.get("tipo_cliente")

    # Bonificaciones
    if es_primera_evaluacion:
        if tipo == "SOCIO":
            return {
                "precio": precio,
                "participacion_pct": 0,
                "participacion_monto": 0,
                "neto_profesional": precio,
                "detalle": "Primera evaluación bonificada 100%"
            }
        else:
            bonificado = precio * 0.5
            return {
                "precio": precio,
                "participacion_pct": 0.2,
                "participacion_monto": bonificado * 0.2,
                "neto_profesional": precio - bonificado * 0.2,
                "detalle": "Primera evaluación bonificada 50%"
            }

    # Turno normal
    pct = 0.30 if tipo == "SOCIO" else 0.20
    monto = precio * pct

    return {
        "precio": precio,
        "participacion_pct": pct,
        "participacion_monto": monto,
        "neto_profesional": precio - monto,
        "detalle": "Turno normal"
    }

def ya_tuvo_evaluacion(turnos, id_paciente, id_servicio):
    evaluaciones = [
        t for t in turnos
        if t.get("id_paciente") == id_paciente
        and t.get("id_servicio") == id_servicio
        and t.get("estado") == "ASISTIÓ"
    ]
    return len(evaluaciones) > 0


# =========================
# UTILIDADES
# =========================
def mes_de_fecha(fecha_str):
    """
    Convierte 'YYYY-MM-DD' → 'YYYY-MM'
    """
    return fecha_str[:7]


# =========================
# DEUDA
# =========================
def detectar_deuda(turnos, pagos=None, mes=None):
    """
    Detecta turnos NO pagados.
    Si se pasa mes, filtra por mes.
    """
    deuda = []

    for t in turnos:
        if mes and mes_de_fecha(t["fecha"]) != mes:
            continue

        if t.get("pagado", "NO") != "SI":
            deuda.append({
                "paciente": t.get("paciente", ""),
                "fecha": t.get("fecha", ""),
                "monto": t.get("monto", 0)
            })

    return deuda


# =========================
# FACTURACIÓN
# =========================
def calcular_facturado(turnos, mes):
    total = 0

    for t in turnos:
        if mes_de_fecha(t["fecha"]) == mes:
            total += int(t.get("monto", 0))

    return total


def calcular_cobrado(pagos, mes):
    total = 0

    for p in pagos:
        if mes_de_fecha(p["fecha"]) == mes:
            total += int(p.get("monto", 0))

    return total


# =========================
# CIERRES
# =========================
def mes_cerrado(ws_cierres, mes):
    cierres = ws_cierres.get_all_records()

    return any(
        c["mes"] == mes and c["cerrado"] == "SI"
        for c in cierres
    )


def obtener_cierre(ws_cierres, mes):
    cierres = ws_cierres.get_all_records()

    for c in cierres:
        if c["mes"] == mes:
            return {
                "total_facturado": int(c.get("total_facturado", 0)),
                "total_cobrado": int(c.get("total_cobrado", 0)),
                "diferencia": int(c.get("diferencia", 0))
            }

    return None
def calcular_cierre_mes(turnos, pagos, mes):
    def to_int(valor):
        try:
            return int(valor)
        except (TypeError, ValueError):
            return 0

    total_facturado = sum(
        to_int(t.get("precio"))
        for t in turnos
        if t.get("fecha", "").startswith(mes)
    )

    total_cobrado = sum(
        to_int(p.get("monto"))
        for p in pagos
        if p.get("mes") == mes
    )

    diferencia = total_facturado - total_cobrado

    return {
        "mes": mes,
        "total_facturado": total_facturado,
        "total_cobrado": total_cobrado,
        "diferencia": diferencia,
        "cerrado": "SI"
    }

def calcular_precio_turno(turno, paciente, servicio):
    precio = int(servicio.get("precio_base", 0))

    if turno.get("evaluacion") == "SI" and turno.get("descuento_aplicado") != "SI":
        if paciente.get("tipo_cliente") == "SOCIO":
            precio = 0
        else:
            precio = precio // 2

    return precio

def porcentaje_paciente(paciente):
    if paciente.get("tipo_cliente") == "SOCIO":
        return 0.30
    return 0.20

def calcular_liquidacion(turnos, pagos, pacientes, servicios, mes):
    pagos_mes = [
        p for p in pagos
        if p.get("mes") == mes
    ]

    total_liquidar = 0

    for p in pagos_mes:
        paciente = next(
            x for x in pacientes
            if x["nombre"] == p["paciente"]
        )

        porcentaje = porcentaje_paciente(paciente)
        total_liquidar += int(p["monto"]) * porcentaje

    return round(total_liquidar, 2)
def porcentaje_por_paciente(paciente):
    if paciente.get("tipo_cliente") == "SOCIO":
        return 0.30
    return 0.20

def calcular_liquidacion_mes(pagos, pacientes, mes):
    pagos_mes = [
        p for p in pagos
        if p.get("mes") == mes
    ]

    total_liquidar = 0

    for pago in pagos_mes:
        paciente = next(
            (p for p in pacientes if p["nombre"] == pago["paciente"]),
            None
        )
        if not paciente:
            continue

        porcentaje = porcentaje_por_paciente(paciente)
        monto = int(pago.get("monto", 0))
        total_liquidar += monto * porcentaje

    return round(total_liquidar, 2)

def obtener_ajustes(ajustes, mes):
    return sum(
        int(a["monto"])
        for a in ajustes
        if a["mes_aplicado"] == mes
    )

# =========================
# PARTICIPACION
# =========================

def calcular_participacion_turno(turno, paciente):
    """
    Retorna:
    - ingreso_bruto
    - participacion_gimnasio
    - ingreso_neto
    """

    precio = float(turno.get("precio", 0) or 0)
    tipo = paciente.get("tipo_cliente", "PARTICULAR")

    if tipo == "SOCIO":
        porcentaje = 0.30
    else:
        porcentaje = 0.20

    participacion = precio * porcentaje
    neto = precio - participacion

    return {
        "bruto": precio,
        "participacion": participacion,
        "neto": neto,
        "porcentaje": int(porcentaje * 100)
    }

def calcular_participacion_turno(turno, paciente):
    """
    Calcula la participación del gimnasio por turno
    """

    try:
        precio = float(turno.get("precio") or 0)
    except ValueError:
        precio = 0

    tipo = paciente.get("tipo_cliente", "PARTICULAR")

    if tipo == "SOCIO":
        porcentaje = 0.30
    else:
        porcentaje = 0.20

    participacion = round(precio * porcentaje, 2)
    neto = round(precio - participacion, 2)

    return {
        "bruto": precio,
        "porcentaje": int(porcentaje * 100),
        "participacion": participacion,
        "neto": neto
    }
