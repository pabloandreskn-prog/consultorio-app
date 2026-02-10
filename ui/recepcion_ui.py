import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
from data.sheets_client import get_sheet
from domain.finanzas import mes_esta_cerrado
from domain.agenda_logic import marcar_turno_asistio, actualizar_contador_plan

def obtener_siguiente_id(ws):
    """Busca el ID máximo numérico en la columna A y devuelve el siguiente (+1)."""
    try:
        ids = ws.col_values(1)[1:]
        ids_numericos = [int(i) for i in ids if str(i).isdigit()]
        return max(ids_numericos) + 1 if ids_numericos else 1
    except:
        return 1

def verificar_limite_24hs(fecha, hora):
    """Verifica si faltan menos de 24hs para el turno."""
    try:
        cita = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        return (cita - datetime.now()) < timedelta(hours=24)
    except: 
        return False

def recepcion_ui():
    st.markdown("# 🏢 Gestión de Recepción")
    sheet = get_sheet("Consultorio")
    
    # Manejo de Refresh de datos
    if "turnos" not in st.session_state or st.session_state.get("refresh_data"):
        st.session_state.turnos = sheet.worksheet("turnos").get_all_records()
        st.session_state.pacientes = sheet.worksheet("pacientes").get_all_records()
        st.session_state.servicios = sheet.worksheet("servicios").get_all_records()
        st.session_state.planes_pacientes = sheet.worksheet("planes_pacientes").get_all_records()
        st.session_state.cierres = sheet.worksheet("cierres").get_all_records()
        st.session_state.refresh_data = False

    turnos = st.session_state.turnos
    servicios = st.session_state.servicios
    pacientes = st.session_state.pacientes
    planes = st.session_state.planes_pacientes
    hoy = date.today().isoformat()
    horas_lista = [f"{h:02d}:00" for h in range(8, 21)]

    tabs = st.tabs(["📅 Agenda de Hoy", "🔍 Ver Libres", "➕ Nuevo Turno", "👤 Nuevo Paciente"])
    tab_hoy, tab_disponibilidad, tab_nuevo, tab_paciente = tabs

    # --- TAB 1: AGENDA DE HOY ---
    with tab_hoy:
        nombres_pacientes = sorted(list(set([t.get("nombre_paciente") for t in turnos if t.get("nombre_paciente")])))
        paciente_sel = st.selectbox("🔍 Buscar Paciente en Agenda...", [""] + nombres_pacientes)
        turnos_mostrar = [t for t in turnos if str(t.get("fecha")) == hoy]
        
        if paciente_sel:
            turnos_mostrar = [t for t in turnos_mostrar if t.get("nombre_paciente") == paciente_sel]
            
        if not turnos_mostrar:
            st.info("No hay turnos para hoy.")
        else:
            opciones_asistencia = ["RESERVADO", "ASISTIÓ", "AUSENTE"]
            medios_pago = ["", "Efectivo", "Transferencia", "Débito", "MP"]
            
            for i in range(0, len(turnos_mostrar), 3):
                chunk = turnos_mostrar[i : i + 3]
                cols = st.columns(3)
                for idx, t in enumerate(chunk):
                    with cols[idx]:
                        info_plan = next((p for p in planes if str(p['id_paciente']) == str(t['id_paciente']) 
                                         and str(p['id_servicio']) == str(t['id_servicio']) 
                                         and str(p['estado']).upper() == 'ACTIVO'), None)
                        
                        txt_plan = f"📊 {info_plan.get('sesiones_usadas', 0)}/{info_plan.get('sesiones_totales', 0)}" if info_plan else ""
                        estado_act = t.get("estado", "RESERVADO")
                        color_map = {"RESERVADO": "#FFA500", "ASISTIÓ": "#28a745", "AUSENTE": "#dc3545"}
                        border_color = color_map.get(estado_act, "#ccc")
                        
                        with st.container(border=True):
                            st.markdown(f"""
                                <div style="background-color: {border_color}1A; border-radius: 10px; padding: 10px; border: 1px solid {border_color}; margin-bottom: 5px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <span style="background-color: {border_color}; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; font-size: 0.85rem;">{t['hora']}</span>
                                        <span style="font-size: 0.8rem; font-weight: bold; color: #444;">{txt_plan}</span>
                                    </div>
                                    <b style="font-size: 1rem;">{t['nombre_paciente']}</b><br>
                                    <small style="color: #555;">{t['nombre_servicio']}</small>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            est = st.selectbox("Estado", opciones_asistencia, index=opciones_asistencia.index(estado_act) if estado_act in opciones_asistencia else 0, key=f"est_{t['id_turno']}")
                            monto = st.number_input("$ Monto", min_value=0, step=500, key=f"m_{t['id_turno']}")
                            medio = st.selectbox("Medio", medios_pago, key=f"med_{t['id_turno']}")
                            
                            btn_col1, btn_col2 = st.columns([1, 1])
                            
                            if btn_col1.button("💾 REGISTRAR", key=f"btn_{t['id_turno']}", use_container_width=True, type="primary"):
                                if est == "AUSENTE":
                                    es_tarde = verificar_limite_24hs(t['fecha'], t['hora'])
                                    marcar_ausencia(sheet, t, servicios, penalizar=(info_plan and es_tarde))
                                else:
                                    ejecutar_guardado_recepcion(sheet, t, est, monto, medio, st.session_state.cierres, turnos)
                                st.session_state.refresh_data = True
                                st.rerun()

                            with btn_col2.popover("✏️ EDITAR", use_container_width=True):
                                n_fecha = st.date_input("Nueva Fecha", value=date.fromisoformat(str(t['fecha'])), key=f"f_mod_{t['id_turno']}")
                                n_hora = st.selectbox("Nueva Hora", horas_lista, index=horas_lista.index(t['hora']) if t['hora'] in horas_lista else 8, key=f"h_mod_{t['id_turno']}")
                                aplicar_penalidad = st.checkbox("🚩 Cobrar sesión (<24hs)", value=True if info_plan else False, key=f"pen_{t['id_turno']}")
                                if st.button("Confirmar", key=f"c_mod_{t['id_turno']}"):
                                    modificar_o_penalizar_turno(sheet, t, servicios, n_fecha, n_hora, penalizar=aplicar_penalidad)
                                    st.session_state.refresh_data = True
                                    st.rerun()

    # --- TAB 2: DISPONIBILIDAD ---
    with tab_disponibilidad:
        st.subheader("🗓️ Disponibilidad Semanal")
        lunes_semana = date.today() - timedelta(days=date.today().weekday())
        dias_semana = [(lunes_semana + timedelta(days=i)) for i in range(5)]
        grid_cols = st.columns(len(dias_semana))
        
        for d_idx, fecha_dia in enumerate(dias_semana):
            with grid_cols[d_idx]:
                st.markdown(f"**{fecha_dia.strftime('%a %d/%m')}**")
                fecha_str = fecha_dia.isoformat()
                for h in horas_lista:
                    ocupado = any(turno for turno in turnos if str(turno['fecha']) == fecha_str and turno['hora'] == h)
                    if not ocupado:
                        if st.button(f"✅ {h}", key=f"f_{fecha_str}_{h}", use_container_width=True):
                            st.session_state.temp_fecha = fecha_dia
                            st.session_state.temp_hora = h
                            st.toast(f"Seleccionado {h}", icon="📍")
                    else:
                        st.button(f"🚫 {h}", key=f"o_{fecha_str}_{h}", disabled=True, use_container_width=True)

    # --- TAB 3: NUEVO TURNO (Con recurrencia para Planes) ---
    with tab_nuevo:
        pacientes_dict = {p["nombre"]: p for p in pacientes if "nombre" in p}
        servicios_dict = {s["nombre"]: s for s in servicios if "nombre" in s}
        
        val_fecha = st.session_state.get("temp_fecha", date.today())
        val_hora = st.session_state.get("temp_hora", "09:00")

        with st.form("nuevo_turno_recepcion"):
            p_nombre = st.selectbox("Paciente", [""] + sorted(list(pacientes_dict.keys())))
            s_nombre = st.selectbox("Servicio", [""] + sorted(list(servicios_dict.keys())))
            f_inicio = st.date_input("Fecha Inicio / Única", value=val_fecha)
            h_cita = st.selectbox("Hora", horas_lista, index=horas_lista.index(val_hora) if val_hora in horas_lista else 0)
            
            st.markdown("---")
            st.write("📅 **Opciones de Plan (Opcional)**")
            dias_semana = st.multiselect("Fijar días recurrentes:", 
                                         ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
            
            if st.form_submit_button("🚀 CONFIRMAR TURNO(S)"):
                if p_nombre and s_nombre:
                    ws_t = sheet.worksheet("turnos")
                    p_data = pacientes_dict[p_nombre]
                    s_data = servicios_dict[s_nombre]
                    condicion_real = p_data.get("tipo_cliente", "PUBLICO")
                    
                    # Determinar cantidad de sesiones si es plan
                    cant_sesiones = 1
                    if "PLAN" in s_nombre.upper():
                        try: cant_sesiones = int(''.join(filter(str.isdigit, s_nombre)))
                        except: cant_sesiones = 1
                    
                    # Lógica de generación de fechas
                    fechas_a_generar = []
                    if dias_semana and "PLAN" in s_nombre.upper():
                        mapa_dias = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4}
                        dias_indices = [mapa_dias[d] for d in dias_semana]
                        
                        curr_date = f_inicio
                        while len(fechas_a_generar) < cant_sesiones:
                            if curr_date.weekday() in dias_indices:
                                fechas_a_generar.append(curr_date.isoformat())
                            curr_date += timedelta(days=1)
                    else:
                        fechas_a_generar = [f_inicio.isoformat()]

                    # Carga masiva
                    id_base = obtener_siguiente_id(ws_t)
                    rows = []
                    for i, f_str in enumerate(fechas_a_generar):
                        rows.append([id_base + i, f_str, h_cita, p_data["id_paciente"], 
                                     p_nombre, condicion_real, s_data["id_servicio"], 
                                     s_nombre, "RESERVADO", "", ""])
                    
                    ws_t.append_rows(rows)
                    st.session_state.refresh_data = True
                    # Limpiar temporales
                    for key in ["temp_fecha", "temp_hora"]:
                        if key in st.session_state: del st.session_state[key]
                    st.success(f"Se crearon {len(rows)} turnos para {p_nombre}")
                    st.rerun()

    # --- TAB 4: NUEVO PACIENTE ---
    with tab_paciente:
        st.subheader("👤 Registro de Nuevo Paciente")
        with st.form("form_registro_paciente"):
            col1, col2 = st.columns(2)
            n_nom = col1.text_input("Nombre y Apellido completo")
            n_dni = col2.text_input("DNI (sin puntos)")
            n_tel = col1.text_input("Celular (ej: 2920...)")
            n_tipo = col2.selectbox("Tipo de Cliente", ["PUBLICO", "SOCIO_GIM"])
            n_obs = st.text_area("Observaciones o Patología")
            
            if st.form_submit_button("💾 GUARDAR PACIENTE"):
                if n_nom and n_dni:
                    ws_pac = sheet.worksheet("pacientes")
                    nuevo_id_p = len(pacientes) + 1
                    ws_pac.append_row([
                        nuevo_id_p, n_nom, n_dni, n_tel, n_tipo, 
                        date.today().isoformat(), "TRUE", n_obs
                    ])
                    st.session_state.refresh_data = True
                    st.success(f"Paciente {n_nom} registrado con éxito.")
                    st.rerun()
                else:
                    st.error("Nombre y DNI son obligatorios.")

# --- LÓGICA DE APOYO ---

def marcar_ausencia(sheet, turno, servicios, penalizar=False):
    ws_t = sheet.worksheet("turnos")
    all_t = ws_t.get_all_records()
    f_idx = next((i+2 for i, x in enumerate(all_t) if str(x.get('id_turno')) == str(turno.get('id_turno'))), None)
    
    if f_idx:
        ws_t.update_cell(f_idx, 9, "AUSENTE")
        if penalizar:
            serv = next((s for s in servicios if str(s['id_servicio']) == str(turno['id_servicio'])), {})
            precio_total = serv.get('precio', 0)
            precio_sesion = precio_total
            if "PLAN" in str(serv.get('nombre', '')).upper():
                try: 
                    num_sesiones = int(''.join(filter(str.isdigit, serv.get('nombre', '1'))))
                    precio_sesion = precio_total / num_sesiones
                except: pass
            
            ws_t.update_cell(f_idx, 10, precio_sesion)
            ws_t.update_cell(f_idx, 11, precio_sesion)
            actualizar_contador_plan(sheet, turno['id_paciente'], turno['id_servicio'])
        else:
            ws_t.update_cell(f_idx, 10, 0)
            ws_t.update_cell(f_idx, 11, 0)

def modificar_o_penalizar_turno(sheet, turno, servicios, n_fecha, n_hora, penalizar=False):
    ws_t = sheet.worksheet("turnos")
    all_t = ws_t.get_all_records()
    f_idx = next((i+2 for i, x in enumerate(all_t) if str(x.get('id_turno')) == str(turno.get('id_turno'))), None)
    
    if f_idx:
        if penalizar:
            marcar_ausencia(sheet, turno, servicios, penalizar=True)
            nuevo_id = obtener_siguiente_id(ws_t)
            ws_t.append_row([
                nuevo_id, str(n_fecha), n_hora, 
                turno['id_paciente'], turno['nombre_paciente'], 
                turno.get('tipo_cliente', 'PUBLICO'), 
                turno['id_servicio'], turno['nombre_servicio'], "RESERVADO", "", ""
            ])
        else:
            ws_t.update_cell(f_idx, 2, str(n_fecha))
            ws_t.update_cell(f_idx, 3, n_hora)
            ws_t.update_cell(f_idx, 9, "RESERVADO")

def ejecutar_guardado_recepcion(sheet, turno, estado, monto, medio, cierres, todos_turnos):
    ws_t = sheet.worksheet("turnos")
    ws_p = sheet.worksheet("pagos")
    f_idx = next((i+2 for i, x in enumerate(ws_t.get_all_records()) if str(x.get('id_turno')) == str(turno.get('id_turno'))), None)
    
    if f_idx:
        marcar_turno_asistio(ws_t, f_idx, turno, todos_turnos)
        if monto > 0:
            mes = str(turno.get("fecha"))[:7]
            if not mes_esta_cerrado(cierres, mes):
                ws_p.append_row(["", date.today().isoformat(), mes, turno['id_turno'], 
                                 turno['id_paciente'], turno['nombre_paciente'], monto, medio])
        
        if str(turno.get("id_servicio")) in ["4", "5"] and estado == "ASISTIÓ":
            actualizar_contador_plan(sheet, turno['id_paciente'], turno['id_servicio'])