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
    """Devuelve el precio base del servicio desde la tabla servicios."""
    # Precios fijos según tu tabla de servicios
    precios = {
        1: 36000,   # Evaluacion
        2: 36000,   # Sesión Especializada
        3: 24000,   # Sesión individual
        4: 110000,  # PLAN x5
        5: 200000,  # PLAN x10
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

def obtener_deuda_paciente(id_paciente, planes, pagos, servicios):
    """
    Lógica Liliana: Suma (Precio Servicio - Pagos Realizados) 
    solo para planes que el paciente tenga activos.
    """
    deuda_total = 0
    # 1. Filtrar planes activos del paciente
    planes_activos = [p for p in planes if str(p['id_paciente']) == str(id_paciente) and str(p['estado']).upper() == 'ACTIVO']
    
    for plan in planes_activos:
        id_serv = str(plan['id_servicio'])
        # Buscamos precio en servicios
        serv_info = next((s for s in servicios if str(s['id_servicio']) == id_serv), None)
        if not serv_info: continue
        
        precio_servicio = float(serv_info.get('precio', 0))
        
        # Sumamos pagos del paciente para ESTE servicio específico
        pagado = sum(float(p['monto']) for p in pagos 
                     if str(p.get('id_paciente')) == str(id_paciente) 
                     and str(p.get('id_servicio')) == id_serv)
        
        deuda_total += (precio_servicio - pagado)
    
    return max(0, deuda_total)


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