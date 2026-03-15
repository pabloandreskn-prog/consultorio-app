from datetime import datetime

# =====================================================
# CONFIGURACIÓN Y UTILIDADES
# =====================================================

def obtener_info_servicio(id_servicio):
    """Base de datos maestra de precios y sesiones por servicio."""
    servicios = {
        1: {"precio": 36000, "sesiones": 1, "nombre": "Evaluación"},
        2: {"precio": 36000, "sesiones": 1, "nombre": "Sesión Especializada"},
        3: {"precio": 24000, "sesiones": 1, "nombre": "Sesión Individual"},
        4: {"precio": 110000, "sesiones": 5, "nombre": "PLAN x5"},
        5: {"precio": 200000, "sesiones": 10, "nombre": "PLAN x10"},
    }
    return servicios.get(int(id_servicio or 0), {"precio": 0, "sesiones": 1, "nombre": ""})

def calcular_precio_teorico_sesion(id_servicio):
    """Calcula cuánto vale una sola sesión (prorrateado)."""
    info = obtener_info_servicio(id_servicio)
    return int(info["precio"] / info["sesiones"]) if info["sesiones"] > 0 else 0

# =====================================================
# LÓGICA DE NEGOCIO (DASHBOARD)
# =====================================================

def es_primera_evaluacion(turno, turnos_paciente):
    """Verifica si es la primera vez que el paciente asiste a una evaluación."""
    nombre_serv = str(turno.get("nombre_servicio", "")).lower()
    if "evaluacion" not in nombre_serv:
        return False
    
    fecha_actual = turno.get("fecha")
    asistencias_eval = [
        t for t in turnos_paciente 
        if t.get("estado") == "ASISTIÓ" and "evaluacion" in str(t.get("nombre_servicio", "")).lower()
    ]
    
    if not asistencias_eval:
        return True
    
    # Ordenar por fecha y ver si la actual es la más antigua
    asistencias_eval.sort(key=lambda x: x["fecha"])
    return asistencias_eval[0]["fecha"] == fecha_actual

def calcular_participacion_dashboard(turno, turnos_paciente):
    """Calcula el desglose financiero de una sesión específica."""
    id_serv = turno.get("id_servicio", 0)
    condicion = str(turno.get("condicion_turno", "GENERAL")).upper()
    es_socio = "SOCIO" in condicion
    
    v_sesion = calcular_precio_teorico_sesion(id_serv)
    
    # Lógica de Bonificación
    monto_bonificado = 0
    if es_primera_evaluacion(turno, turnos_paciente):
        # 100% bonificado si es socio, 50% si es general
        monto_bonificado = v_sesion if es_socio else v_sesion * 0.5
            
    bruto = max(0, v_sesion - monto_bonificado)
    porcentaje_gym = 30 if es_socio else 20
    participacion_gym = bruto * (porcentaje_gym / 100)
    neto_profesional = bruto - participacion_gym

    return {
        "bruto": int(bruto),
        "bonificacion": int(monto_bonificado),
        "porcentaje": porcentaje_gym,
        "participacion": int(participacion_gym),
        "neto": int(neto_profesional)
    }

def mes_esta_cerrado(cierres, mes):
    return any(c.get("mes") == mes and str(c.get("estado")).upper() == "CERRADO" for c in cierres)

# Compatibilidad con otras partes de la app
def calcular_precio_teorico(id_servicio, nombre_servicio=""):
    return obtener_info_servicio(id_servicio)["precio"]