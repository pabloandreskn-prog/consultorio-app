import streamlit as st
from datetime import date, timedelta
from domain.cierres import mes_esta_cerrado
from domain.agenda_logic import (
    marcar_turno_asistio, 
    marcar_turno_cancelado,
    contar_sesiones_realizadas,
    obtener_alerta_renovacion,
    crear_entrada_plan,
    actualizar_contador_plan
)

# =========================
# HELPERS ORIGINALES Y DEUDA
# =========================
def generar_horarios():
    return [f"{h:02d}:00" for h in range(8, 21)]

def siguiente_id_turno(turnos):
    ids = [int(t["id_turno"]) for t in turnos if str(t.get("id_turno")).isdigit()]
    return max(ids) + 1 if ids else 1

def extraer_sesiones(nombre_servicio):
    numeros = "".join(filter(str.isdigit, nombre_servicio))
    return int(numeros) if numeros else 1

def generar_fechas_plan(fecha_inicio, d_semana, sesiones):
    fechas = []
    fecha = fecha_inicio
    while len(fechas) < sesiones:
        if fecha.weekday() in d_semana:
            fechas.append(fecha)
        fecha += timedelta(days=1)
    return fechas

def sesiones_acumuladas(id_paciente, id_servicio, planes_pacientes):
    for plan in planes_pacientes:
        p_id_match = str(plan.get("id_paciente")) == str(id_paciente)
        s_id_match = str(plan.get("id_servicio")) == str(id_servicio)
        es_activo = str(plan.get("estado", "")).upper() == "ACTIVO"
        if p_id_match and s_id_match and es_activo:
            return (int(plan.get("sesiones_usadas", 0)), int(plan.get("sesiones_totales", 0)))
    return 0, 0

def obtener_deuda_paciente(id_paciente, sheet):
    from ui.recepcion_ui import limpiar_monto
    try:
        ventas = sheet.worksheet("ventas").get_all_records()
        pagos = sheet.worksheet("pagos").get_all_records()
        total_venta = sum(limpiar_monto(v.get("monto_total", 0)) for v in ventas if str(v.get("id_paciente")) == str(id_paciente))
        total_pago = sum(limpiar_monto(p.get("monto", 0)) for p in pagos if str(p.get("id_paciente")) == str(id_paciente))
        return total_venta - total_pago
    except:
        return 0.0

# =========================
# AGENDA UI
# =========================
def agenda_ui(sheet, pacientes, servicios, planes_pacientes):
    st.title("📅 Agenda")

    if "ws_turnos" not in st.session_state: st.session_state.ws_turnos = sheet.worksheet("turnos")
    if "ws_planes" not in st.session_state: st.session_state.ws_planes = sheet.worksheet("planes_pacientes")
    if "ws_ventas" not in st.session_state: st.session_state.ws_ventas = sheet.worksheet("ventas")
    
    if "turnos" not in st.session_state:
        st.session_state.turnos = st.session_state.ws_turnos.get_all_records()
    if "planes_pacientes" not in st.session_state:
        st.session_state.planes_pacientes = st.session_state.ws_planes.get_all_records()

    turnos = st.session_state.turnos
    planes_actuales = st.session_state.planes_pacientes

    fecha_vista = st.date_input("📅 Ver agenda del día", value=date.today())
    turnos_dia = [(i + 2, t) for i, t in enumerate(turnos) if t.get("fecha") == str(fecha_vista)]

    # --- VISTA DE BLOQUES ---
    st.subheader("🟩 Turnos del día")
    if turnos_dia:
        cols = st.columns(4)
        for i, (_, t) in enumerate(turnos_dia):
            usadas, totales = sesiones_acumuladas(t["id_paciente"], t["id_servicio"], planes_actuales)
            deuda = obtener_deuda_paciente(t["id_paciente"], sheet)
            
            if deuda > 0:
                bg_color, border_color = "rgba(255, 75, 75, 0.2)", "rgba(255, 75, 75, 0.6)"
            elif t.get("estado") == "ASISTIÓ":
                bg_color, border_color = "rgba(96,176,103,0.2)", "rgba(96,176,103,0.5)"
            else:
                bg_color, border_color = "rgba(255,165,0,0.15)", "rgba(255,165,0,0.5)"

            with cols[i % 4]:
                alerta_deuda = f"<br><b style='color: #FF4B4B;'>⚠️ DEBE ${deuda:,.0f}</b>" if deuda > 0 else ""
                st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 15px; border-radius: 12px; border: 1px solid {border_color}; margin-bottom: 10px; color: inherit;">
                        <b style="font-size: 1.1em;">🕒 {t['hora']}</b><br>
                        <span style="font-weight: 600;">{t['nombre_paciente']}</span>{alerta_deuda}<br>
                        <div style="opacity: 0.8; font-size: 0.85em;">{t['nombre_servicio']}<br>📊 {usadas}/{totales} sesiones</div>
                    </div>""", unsafe_allow_html=True)
    else:
        st.info("No hay turnos para este día")

    # --- OPERACIÓN DEL DÍA ---
    st.markdown("---")
    st.subheader("📋 Operación del día")

    for fila, t in turnos_dia:
        estado_act = t.get("estado", "RESERVADO")
        usadas_r, t_plan = sesiones_acumuladas(t["id_paciente"], t["id_servicio"], planes_actuales)
        deuda_op = obtener_deuda_paciente(t["id_paciente"], sheet)

        col1, col2, col3, col4, col5 = st.columns([2, 3, 1.5, 1.5, 1.5])
        col1.write(f"🕒 {t['hora']}")
        nombre_label = f"**{t['nombre_paciente']}**"
        if deuda_op > 0: nombre_label += f" ⚠️ **(DEBE ${deuda_op:,.0f})**"
        col2.write(nombre_label)
        col3.write(f"📊 {usadas_r}/{t_plan}")

        if estado_act == "ASISTIÓ":
            col4.markdown("✅ *Asistió*")
        elif estado_act == "CANCELADO":
            col4.markdown("❌ *Cancelado*")
        else:
            if col4.button("✔️", key=f"as_btn_{t['id_turno']}"):
                marcar_turno_asistio(st.session_state.ws_turnos, fila, t, turnos)
                if str(t["id_servicio"]) in ["4", "5"]: actualizar_contador_plan(sheet, t["id_paciente"], t["id_servicio"])
                st.session_state.pop("turnos", None)
                st.rerun()
            if col5.button("🚫", key=f"canc_btn_{t['id_turno']}"):
                marcar_turno_cancelado(st.session_state.ws_turnos, fila)
                st.session_state.pop("turnos", None)
                st.rerun()

        if str(t["id_servicio"]) in ["1", "2", "3"] and estado_act != "CANCELADO":
            with st.expander(f"💰 Cobrar {t['nombre_paciente']}"):
                from ui.recepcion_ui import registrar_cobro_recepcion
                metodo = st.selectbox("Método", ["Efectivo", "Transferencia", "MP"], key=f"met_{t['id_turno']}")
                monto_val = st.number_input("Monto", value=24000, key=f"val_{t['id_turno']}")
                if st.button("Confirmar Pago", key=f"pay_{t['id_turno']}"):
                    if registrar_cobro_recepcion({"id_paciente": t["id_paciente"], "nombre_paciente": t["nombre_paciente"], "id_servicio": t["id_servicio"], "monto": monto_val, "metodo": metodo}):
                        st.success("Pago registrado")
                        st.rerun()

    # --- FORMULARIO NUEVO TURNO (LOGICA DE VENTA INTEGRADA) ---
    st.markdown("---")
    st.subheader("➕ Crear turno / plan")
    pacientes_dict = {p["nombre"]: p for p in pacientes}
    servicios_dict = {s["nombre"]: s for s in servicios}
    dias_opciones = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5}

    with st.form("nuevo_turno"):
        fecha_ini = st.date_input("📅 Fecha de inicio", value=fecha_vista)
        c1, c2, c3 = st.columns(3)
        p_nombre = c1.selectbox("Paciente", pacientes_dict.keys())
        s_nombre = c2.selectbox("Servicio", servicios_dict.keys())
        h_turno = c3.selectbox("Hora", generar_horarios())
        
        servicio_obj = servicios_dict[s_nombre]
        cant_sesiones = extraer_sesiones(servicio_obj["nombre"])
        es_plan = cant_sesiones > 1

        dias_seleccionados = []
        if es_plan:
            st.markdown("### 📆 Configuración del PLAN")
            dias_seleccionados = st.multiselect("Días fijos", options=dias_opciones.keys())

        if st.form_submit_button("🟢 Crear turnos"):
            paciente_obj = pacientes_dict[p_nombre]
            from ui.recepcion_ui import encontrar_proxima_fila_libre, limpiar_monto
            
            # 1. Registrar Venta inmediatamente (Genera la DEUDA)
            id_v = encontrar_proxima_fila_libre(st.session_state.ws_ventas)
            monto_total = limpiar_monto(servicio_obj.get("precio", 0))
            fila_v = [id_v, str(fecha_ini), str(fecha_ini)[:7], paciente_obj["id_paciente"], 
                      paciente_obj["nombre"], servicio_obj["id_servicio"], 
                      paciente_obj.get("condicion", "GENERAL"), monto_total, "NO", "", cant_sesiones, 0]
            st.session_state.ws_ventas.insert_row(fila_v, id_v)

            # 2. Si es Plan, registrar en planes_pacientes
            if es_plan:
                crear_entrada_plan(sheet, paciente_obj, servicio_obj, cant_sesiones, fecha_ini)
            
            # 3. Registrar los Turnos
            fechas_lista = generar_fechas_plan(fecha_ini, [dias_opciones[d] for d in dias_seleccionados], cant_sesiones) if (es_plan and dias_seleccionados) else [fecha_ini]
            id_t = siguiente_id_turno(st.session_state.turnos)
            for f in fechas_lista:
                st.session_state.ws_turnos.append_row([
                    id_t, str(f), h_turno, paciente_obj["id_paciente"], paciente_obj["nombre"],
                    paciente_obj.get("condicion", "GENERAL"), servicio_obj["id_servicio"],
                    servicio_obj["nombre"], "RESERVADO", monto_total if not es_plan else monto_total/cant_sesiones, ""
                ])
                id_t += 1
            
            st.session_state.clear() # Limpiar todo para forzar recarga de sheets
            st.rerun()