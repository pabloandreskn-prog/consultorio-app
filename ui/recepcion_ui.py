import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
from data.sheets_client import get_sheet
from domain.finanzas import mes_esta_cerrado
from domain.agenda_logic import marcar_turno_asistio, actualizar_contador_plan

def obtener_deuda_paciente(id_paciente, planes, pagos, servicios):
    """Calcula si un paciente tiene saldos pendientes en sus planes activos."""
    deuda_total = 0
    planes_activos = [p for p in planes if str(p['id_paciente']) == str(id_paciente) and str(p['estado']).upper() == 'ACTIVO']
    
    for plan in planes_activos:
        serv = next((s for s in servicios if str(s['id_servicio']) == str(plan['id_servicio'])), None)
        if serv:
            try:
                precio_plan = float(serv.get('precio', 0))
                # Filtramos pagos por paciente Y servicio para exactitud
                pagado = sum(float(p['monto']) for p in pagos 
                             if str(p.get('id_paciente')) == str(id_paciente) 
                             and str(p.get('id_servicio')) == str(plan['id_servicio']))
                deuda_total += (precio_plan - pagado)
            except:
                continue
    return max(0, deuda_total)

def obtener_siguiente_id(ws):
    try:
        ids = ws.col_values(1)[1:]
        ids_numericos = [int(i) for i in ids if str(i).isdigit()]
        return max(ids_numericos) + 1 if ids_numericos else 1
    except:
        return 1

def verificar_limite_24hs(fecha, hora):
    try:
        cita = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        return (cita - datetime.now()) < timedelta(hours=24)
    except: 
        return False

def recepcion_ui():
    st.markdown("# 🏢 Gestión de Recepción")
    sheet = get_sheet("Consultorio")
    
    if "turnos" not in st.session_state or st.session_state.get("refresh_data"):
        st.session_state.turnos = sheet.worksheet("turnos").get_all_records()
        st.session_state.pacientes = sheet.worksheet("pacientes").get_all_records()
        st.session_state.servicios = sheet.worksheet("servicios").get_all_records()
        st.session_state.planes_pacientes = sheet.worksheet("planes_pacientes").get_all_records()
        st.session_state.pagos = sheet.worksheet("pagos").get_all_records()
        st.session_state.cierres = sheet.worksheet("cierres").get_all_records()
        st.session_state.refresh_data = False

    turnos = st.session_state.turnos
    servicios = st.session_state.servicios
    pacientes = st.session_state.pacientes
    planes = st.session_state.planes_pacientes
    pagos = st.session_state.pagos
    hoy = date.today().isoformat()
    horas_lista = [f"{h:02d}:00" for h in range(8, 21)]

    tabs = st.tabs(["📅 Agenda de Hoy", "🔍 Ver Libres", "➕ Nuevo Turno", "👤 Nuevo Paciente"])
    tab_hoy, tab_disponibilidad, tab_nuevo, tab_paciente = tabs

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
        
                        deuda = obtener_deuda_paciente(t['id_paciente'], planes, pagos, servicios)
        
                        txt_plan = f"📊 {info_plan['sesiones_usadas']}/{info_plan['sesiones_totales']}" if info_plan else "S/P"
                        estado_act = t.get("estado", "RESERVADO")
                        color_map = {"RESERVADO": "#FFA500", "ASISTIÓ": "#28a745", "AUSENTE": "#dc3545"}
                        border_color = color_map.get(estado_act, "#ccc")

                        with st.container(border=True):
                            st.markdown(f"""
                                <div style="background-color: {border_color}1A; border-radius: 8px; padding: 10px; border-left: 5px solid {border_color};">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span style="background-color: {border_color}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;">{t['hora']}</span>
                                        <span style="font-weight: bold; color: #444; font-size: 0.85rem;">{txt_plan}</span>
                                    </div>
                                    <div style="margin-top: 8px; font-weight: bold; font-size: 1rem; color: #1e1e1e;">{t['nombre_paciente']}</div>
                                    <div style="font-size: 0.8rem; color: #666;">{t['nombre_servicio']}</div>
                                    {f'<div style="color: #dc3545; font-weight: bold; font-size: 0.9rem; margin-top: 5px; border-top: 1px dashed #dc3545; padding-top: 5px;">⚠️ DEBE ${deuda:,.0f}</div>' if deuda > 0 else ""}
                                </div>
                            """, unsafe_allow_html=True)

                            st.write("") 
                            est = st.selectbox("Estado", opciones_asistencia, index=opciones_asistencia.index(estado_act) if estado_act in opciones_asistencia else 0, key=f"est_{t['id_turno']}")
                            
                            c1, c2 = st.columns(2)
                            monto = c1.number_input("$ Pago", min_value=0, step=500, key=f"m_{t['id_turno']}")
                            medio = c2.selectbox("Medio", medios_pago, key=f"med_{t['id_turno']}")
            
                            btn_col1, btn_col2 = st.columns([1, 1])
                            if btn_col1.button("💾 REGISTRAR", key=f"btn_{t['id_turno']}", use_container_width=True, type="primary"):
                                if est == "AUSENTE":
                                    es_tarde = verificar_limite_24hs(t['fecha'], t['hora'])
                                    marcar_ausencia(sheet, t, servicios, penalizar=(info_plan and es_tarde))
                                else:
                                    ejecutar_guardado_recepcion(sheet, t, est, monto, medio, turnos)
                
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
        dias_semana_list = [(lunes_semana + timedelta(days=i)) for i in range(5)]
        grid_cols = st.columns(len(dias_semana_list))
        
        for d_idx, fecha_dia in enumerate(dias_semana_list):
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

    # --- TAB 3: NUEVO TURNO ---
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
            dias_recurrencia = st.multiselect("Fijar días recurrentes:", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
            
            if st.form_submit_button("🚀 CONFIRMAR TURNO(S)"):
                if p_nombre and s_nombre:
                    ws_t = sheet.worksheet("turnos")
                    p_data = pacientes_dict[p_nombre]
                    s_data = servicios_dict[s_nombre]
                    condicion_real = p_data.get("tipo_cliente", "PUBLICO")
                    
                    cant_sesiones = 1
                    if "PLAN" in s_nombre.upper():
                        try: cant_sesiones = int(''.join(filter(str.isdigit, s_nombre)))
                        except: cant_sesiones = 1
                    
                    fechas_a_generar = []
                    if dias_recurrencia and "PLAN" in s_nombre.upper():
                        mapa_dias = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4}
                        dias_indices = [mapa_dias[d] for d in dias_recurrencia]
                        curr_date = f_inicio
                        while len(fechas_a_generar) < cant_sesiones:
                            if curr_date.weekday() in dias_indices:
                                fechas_a_generar.append(curr_date.isoformat())
                            curr_date += timedelta(days=1)
                    else:
                        fechas_a_generar = [f_inicio.isoformat()]

                    id_base = obtener_siguiente_id(ws_t)
                    rows = []
                    for i, f_str in enumerate(fechas_a_generar):
                        rows.append([id_base + i, f_str, h_cita, p_data["id_paciente"], 
                                     p_nombre, condicion_real, s_data["id_servicio"], 
                                     s_nombre, "RESERVADO", "", ""])
                    
                    ws_t.append_rows(rows)
                    st.session_state.refresh_data = True
                    for key in ["temp_fecha", "temp_hora"]:
                        if key in st.session_state: del st.session_state[key]
                    st.success(f"Se crearon {len(rows)} turnos.")
                    st.rerun()

    # --- TAB 4: NUEVO PACIENTE ---
    with tab_paciente:
        st.subheader("👤 Registro de Nuevo Paciente")
        with st.form("form_registro_paciente"):
            col1, col2 = st.columns(2)
            n_nom = col1.text_input("Nombre y Apellido completo")
            n_dni = col2.text_input("DNI (sin puntos)")
            n_tel = col1.text_input("Celular")
            n_tipo = col2.selectbox("Tipo de Cliente", ["PUBLICO", "SOCIO_GIM"])
            n_obs = st.text_area("Observaciones")
            
            if st.form_submit_button("💾 GUARDAR"):
                if n_nom and n_dni:
                    ws_pac = sheet.worksheet("pacientes")
                    nuevo_id_p = len(pacientes) + 1
                    ws_pac.append_row([nuevo_id_p, n_nom, n_dni, n_tel, n_tipo, date.today().isoformat(), "TRUE", n_obs])
                    st.session_state.refresh_data = True
                    st.success(f"Paciente {n_nom} registrado.")
                    st.rerun()

# --- FUNCIONES DE APOYO ---

def marcar_ausencia(sheet, turno, servicios, penalizar=False):
    ws_t = sheet.worksheet("turnos")
    all_t = ws_t.get_all_records()
    f_idx = next((i+2 for i, x in enumerate(all_t) if str(x.get('id_turno')) == str(turno.get('id_turno'))), None)
    if f_idx:
        ws_t.update_cell(f_idx, 9, "AUSENTE")
        if penalizar:
            serv = next((s for s in servicios if str(s['id_servicio']) == str(turno['id_servicio'])), {})
            precio_total = float(serv.get('precio', 0))
            precio_sesion = precio_total
            if "PLAN" in str(serv.get('nombre', '')).upper():
                try: 
                    num = int(''.join(filter(str.isdigit, serv.get('nombre', '1'))))
                    precio_sesion = precio_total / num
                except: pass
            ws_t.update_cell(f_idx, 10, precio_sesion)
            ws_t.update_cell(f_idx, 11, precio_sesion)
            actualizar_contador_plan(sheet, turno['id_paciente'], turno['id_servicio'])

def modificar_o_penalizar_turno(sheet, turno, servicios, n_fecha, n_hora, penalizar=False):
    ws_t = sheet.worksheet("turnos")
    all_t = ws_t.get_all_records()
    f_idx = next((i+2 for i, x in enumerate(all_t) if str(x.get('id_turno')) == str(turno.get('id_turno'))), None)
    if f_idx:
        if penalizar:
            marcar_ausencia(sheet, turno, servicios, penalizar=True)
            nuevo_id = obtener_siguiente_id(ws_t)
            ws_t.append_row([nuevo_id, str(n_fecha), n_hora, turno['id_paciente'], turno['nombre_paciente'], turno.get('tipo_cliente', 'PUBLICO'), turno['id_servicio'], turno['nombre_servicio'], "RESERVADO", "", ""])
        else:
            ws_t.update_cell(f_idx, 2, str(n_fecha))
            ws_t.update_cell(f_idx, 3, n_hora)
            ws_t.update_cell(f_idx, 9, "RESERVADO")

def ejecutar_guardado_recepcion(sheet, turno, estado, monto_pago, medio_pago, todos_los_turnos):
    try:
        ws_turnos = sheet.worksheet("turnos")
        ids_col = ws_turnos.col_values(1)
        try:
            fila = ids_col.index(str(turno['id_turno'])) + 1
        except ValueError:
            st.error("No se encontró el turno en el Excel")
            return

        # 1. Registrar Asistencia
        if estado == "ASISTIÓ":
            marcar_turno_asistio(ws_turnos, fila, turno, todos_los_turnos)
            actualizar_contador_plan(sheet, turno['id_paciente'], turno['id_servicio'])
        else:
             ws_turnos.update_cell(fila, 9, estado)

        # 2. Registrar Pago con IDs para control de Deuda
        if monto_pago > 0:
            ws_pagos = sheet.worksheet("pagos")
            ws_pagos.append_row([
                obtener_siguiente_id(ws_pagos),
                datetime.now().strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m"),
                turno['nombre_paciente'],
                monto_pago,
                medio_pago,
                f"Pago {turno['nombre_servicio']}",
                turno['id_paciente'],  # Columna H
                turno['id_servicio']   # Columna I
            ])
        
        st.success(f"✅ ¡Datos guardados para {turno['nombre_paciente']}!")
    except Exception as e:
        st.error(f"Error al guardar: {e}")