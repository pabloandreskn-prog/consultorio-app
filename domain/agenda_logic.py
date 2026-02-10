import streamlit as st
from datetime import datetime
from domain.finanzas import calcular_precio_teorico, es_primera_evaluacion

def contar_sesiones_realizadas(turnos, id_paciente, id_servicio):
    """Cuenta asistencias filtrando por paciente y servicio (IDs como texto)."""
    if not turnos: return 0
    return sum(
        1 for t in turnos
        if (str(t.get("id_paciente")) == str(id_paciente) and 
            str(t.get("id_servicio")) == str(id_servicio) and 
            str(t.get("estado")).upper() == "ASISTIÓ")
    )

def marcar_turno_asistio(ws_turnos, fila, turno, todos_los_turnos):
    """Actualiza el turno en la hoja de turnos."""
    id_servicio = turno.get("id_servicio")
    nombre_servicio = str(turno.get("nombre_servicio", ""))
    condicion = str(turno.get("condicion_turno", "GENERAL")).upper()

    p_teorico = calcular_precio_teorico(id_servicio, nombre_servicio)
    v_facturado = p_teorico

    if "evaluacion" in nombre_servicio.lower():
        if es_primera_evaluacion(turno, todos_los_turnos):
            v_facturado = 0 if condicion == "SOCIO_GYM" else (p_teorico // 2)

    ws_turnos.update_cell(fila, 9, "ASISTIÓ")
    ws_turnos.update_cell(fila, 10, p_teorico)
    ws_turnos.update_cell(fila, 11, v_facturado)
    return True

def actualizar_contador_plan(sheet, id_paciente, id_servicio):
    """Suma +1 en la columna E de la hoja 'planes_pacientes'."""
    try:
        ws_planes = sheet.worksheet("planes_pacientes")
        planes = ws_planes.get_all_records()
        for i, plan in enumerate(planes):
            if (str(plan["id_paciente"]) == str(id_paciente) and 
                str(plan["id_servicio"]) == str(id_servicio) and 
                str(plan["estado"]).upper() == "ACTIVO"):
                
                nueva_asistencia = int(plan.get("sesiones_usadas", 0)) + 1
                # Fila = i + 2 (1 por encabezado + 1 por índice 0)
                ws_planes.update_cell(i + 2, 5, nueva_asistencia)
                return True
    except Exception as e:
        st.error(f"Error actualizando plan: {e}")
    return False

def marcar_turno_cancelado(ws_turnos, fila):
    ws_turnos.update_cell(fila, 9, "CANCELADO")
    ws_turnos.update_cell(fila, 10, 0)
    ws_turnos.update_cell(fila, 11, 0)

def obtener_alerta_renovacion(sesiones_usadas, sesiones_totales, nombre_servicio):
    if sesiones_totales == 0: return "⚠️ Sin plan activo detectado"
    if sesiones_totales <= 1: return "⚠️ Última sesión disponible."
    if sesiones_usadas >= (sesiones_totales - 1):
        return f"📢 Sesión {sesiones_usadas}/{sesiones_totales}. ¡Renovar plan!"
    return None

def crear_entrada_plan(sheet, paciente, servicio, sesiones, fecha_inicio):
    ws_planes = sheet.worksheet("planes_pacientes")
    planes = ws_planes.get_all_records()
    ids = [int(p["id_plan_paciente"]) for p in planes if str(p.get("id_plan_paciente")).isdigit()]
    nuevo_id = max(ids) + 1 if ids else 1
    ws_planes.append_row([nuevo_id, paciente["id_paciente"], servicio["id_servicio"], sesiones, 0, "ACTIVO", str(fecha_inicio), "", ""])