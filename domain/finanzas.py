from datetime import datetime

# =====================================================
# FECHAS / UTILIDADES
# =====================================================

def mes_de_fecha(fecha_str):
    """YYYY-MM-DD → YYYY-MM"""
    if not fecha_str:
        return ""
    return fecha_str[:7]


# =====================================================
# PRECIOS TEÓRICOS
# =====================================================

def calcular_precio_teorico(id_servicio, nombre_servicio):
    """
    Devuelve el precio teórico base del servicio.
    """
    # PLANES (precio por sesión)
    if "PLAN x5" in nombre_servicio:
        return 110000 // 5

    if "PLAN x10" in nombre_servicio:
        return 200000 // 10

    # SESIONES
    precios = {
        1: 36000,   # Evaluación
        2: 36000,   # Sesión Especializada
        3: 24000,   # Sesión individual
        6: 25000,   # Zona A
        7: 25000,   # Zona B
        8: 38000,   # Completo
    }

    return precios.get(int(id_servicio), 0)


# =====================================================
# EVALUACIONES
# =====================================================

def es_primera_evaluacion(turno, turnos_paciente):
    """
    Determina si este turno es la primera evaluación real del paciente.
    """
    servicio = turno.get("nombre_servicio", "").lower()
    if not servicio.startswith("evaluacion"):
        return False

    fecha_actual_str = turno.get("fecha")
    if not fecha_actual_str:
        return False

    fecha_actual = datetime.fromisoformat(fecha_actual_str)

    for t in turnos_paciente:
        if t.get("estado") != "ASISTIÓ":
            continue

        if not t.get("nombre_servicio", "").lower().startswith("evaluacion"):
            continue

        fecha_t_str = t.get("fecha")
        if not fecha_t_str:
            continue

        fecha_t = datetime.fromisoformat(fecha_t_str)

        if fecha_t < fecha_actual:
            return False

    return True


# =====================================================
# DEUDA
# =====================================================

def detectar_deuda(turnos, mes=None):
    deuda = []
    for t in turnos:
        fecha = t.get("fecha")
        if not fecha:
            continue

        if mes and not fecha.startswith(mes):
            continue

        precio = int(t.get("precio_teorico", 0) or 0)
        facturado = int(t.get("valor_facturado", 0) or 0)

        if precio > facturado:
            deuda.append({
                "paciente": t.get("nombre_paciente"),
                "fecha": fecha,
                "servicio": t.get("nombre_servicio"),
                "deuda": precio - facturado
            })
    return deuda

def calcular_deuda_turno(turno):
    try:
        precio = int(turno.get("precio_teorico", 0) or 0)
        facturado = int(turno.get("valor_facturado", 0) or 0)
        deuda = precio - facturado
        return max(deuda, 0)
    except:
        return 0


# =====================================================
# FACTURACIÓN
# =====================================================

def obtener_monto_turno(turno):
    for clave in ("importe", "monto", "precio", "bruto"):
        if clave in turno and turno[clave]:
            return int(turno[clave])
    return 0


# =====================================================
# CIERRES MENSUALES
# =====================================================

def mes_esta_cerrado(cierres, mes):
    for c in cierres:
        if c.get("mes") == mes and c.get("estado") == "CERRADO":
            return True
    return False

def calcular_cierre_mes(turnos, pagos, mes):
    def to_int(v):
        try:
            return int(v)
        except:
            return 0

    total_facturado = sum(
        to_int(t.get("valor_facturado"))
        for t in turnos
        if t.get("fecha", "").startswith(mes)
        and t.get("estado") == "ASISTIÓ"
    )

    total_cobrado = sum(
        to_int(p.get("monto"))
        for p in pagos
        if p.get("mes") == mes
    )

    return {
        "mes": mes,
        "total_facturado": total_facturado,
        "total_cobrado": total_cobrado,
        "diferencia": total_facturado - total_cobrado
    }


# =====================================================
# PARTICIPACIÓN / COMISIONES (ACTUALIZADA)
# =====================================================

def calcular_participacion_turno(turno, paciente, todos_los_turnos):
    """
    Calcula la comisión basada en la condición del turno:
    SOCIO_GYM = 30% | GENERAL = 20%
    """
    # 1. Monto cobrado real
    bruto_original = int(turno.get("valor_facturado", 0) or 0)
    
    # 2. Regla de porcentajes
    condicion = str(turno.get("condicion_turno", "GENERAL")).upper()
    porcentaje = 30 if condicion == "SOCIO_GYM" else 20

    # 3. Cálculo final
    participacion = bruto_original * (porcentaje / 100)
    neto = bruto_original - participacion

    return {
        "bruto": int(bruto_original),
        "porcentaje": porcentaje,
        "participacion": int(participacion),
        "neto": int(neto)
    }