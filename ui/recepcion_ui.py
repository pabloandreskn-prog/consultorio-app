import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
from data.sheets_client import get_sheet
from domain.finanzas import mes_esta_cerrado, obtener_info_servicio
from domain.agenda_logic import marcar_turno_asistio, actualizar_contador_plan

def obtener_deuda_paciente(id_paciente, turnos, pagos, servicios):
    """Calcula la deuda real consultando la hoja de Ventas."""
    try:
        # Optimizamos: intentamos usar datos en sesión para no saturar la API
        if "ventas_data" not in st.session_state:
            sheet = get_sheet("Consultorio")
            st.session_state.ventas_data = sheet.worksheet("ventas").get_all_records()
        
        ventas_data = st.session_state.ventas_data
        
        total_ventas = sum(
            float(v.get('monto_total', 0)) 
            for v in ventas_data 
            if str(v.get('id_paciente')) == str(id_paciente)
        )
        
        total_pagado = sum(
            float(p.get('monto', 0)) 
            for p in pagos 
            if str(p.get('id_paciente')) == str(id_paciente)
        )
        
        deuda = total_ventas - total_pagado
        return max(0, deuda)
    except Exception:
        return 0

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
    
    # Manejo de caché para evitar Error 429 (Quota Exceeded)
    if "turnos" not in st.session_state or st.session_state.get("refresh_data"):
        try:
            st.session_state.turnos = sheet.worksheet("turnos").get_all_records()
            st.session_state.pacientes = sheet.worksheet("pacientes").get_all_records()
            st.session_state.servicios = sheet.worksheet("servicios").get_all_records()
            st.session_state.pagos = sheet.worksheet("pagos").get_all_records()
            if "ventas_data" in st.session_state: del st.session_state["ventas_data"]
            st.session_state.refresh_data = False
        except Exception as e:
            st.error("Error de conexión con Google Sheets. Reintentando en unos segundos...")
            return

    turnos = st.session_state.turnos
    servicios = st.session_state.servicios
    pacientes = st.session_state.pacientes
    pagos = st.session_state.pagos
    horas_lista = [f"{h:02d}:00" for h in range(8, 21)]

    tabs = st.tabs(["📅 Agenda", "🔍 Libres", "➕ Turno", "👤 Paciente"])
    tab_hoy, tab_disponibilidad, tab_nuevo, tab_paciente = tabs

    with tab_hoy:
        # --- NAVEGADOR DE FECHAS EN ESPAÑOL ---
        col_f1, col_f2, col_f3 = st.columns([1, 2, 1])
        with col_f2:
            # Nota: Streamlit usa la configuración regional del navegador, 
            # forzamos formato visual y texto de ayuda.
            fecha_consulta = st.date_input(
                "📅 Seleccione una fecha para ver la agenda:", 
                value=date.today(),
                format="DD/MM/YYYY"
            )
        
        fecha_str_consulta = fecha_consulta.isoformat()
        
        nombres_pacientes = sorted(list(set([t.get("nombre_paciente") for t in turnos if t.get("nombre_paciente")])))
        paciente_sel = st.selectbox("🔍 Buscar Paciente...", [""] + nombres_pacientes)
        
        turnos_mostrar = [t for t in turnos if str(t.get("fecha")) == fecha_str_consulta]
        
        if paciente_sel:
            turnos_mostrar = [t for t in turnos_mostrar if t.get("nombre_paciente") == paciente_sel]
            
        if not turnos_mostrar:
            st.info(f"No hay turnos para el día {fecha_consulta.strftime('%d/%m/%Y')}.")
        else:
            turnos_mostrar = sorted(turnos_mostrar, key=lambda x: x['hora'])
            opciones_asistencia = ["RESERVADO", "ASISTIÓ", "AUSENTE"]
            medios_pago = ["", "Efectivo", "Transferencia", "Débito", "MP"]
            
            for i in range(0, len(turnos_mostrar), 3):
                chunk = turnos_mostrar[i : i + 3]
                cols = st.columns(3)

                for idx, t in enumerate(chunk):
                    with cols[idx]:
                        es_plan = "PLAN" in str(t['nombre_servicio']).upper()
                        if es_plan:
                            asistencias_plan = [a for a in turnos if str(a['id_paciente']) == str(t['id_paciente']) 
                                               and str(a['id_servicio']) == str(t['id_servicio']) 
                                               and a['estado'] == 'ASISTIÓ']
                            try: total_sesiones = int(''.join(filter(str.isdigit, t['nombre_servicio'])))
                            except: total_sesiones = 10
                            txt_plan = f"📊 {len(asistencias_plan)}/{total_sesiones}"
                        else:
                            asistio_hoy = 1 if t['estado'] == 'ASISTIÓ' else 0
                            txt_plan = f"📊 {asistio_hoy}/1"
                        
                        deuda = obtener_deuda_paciente(t['id_paciente'], turnos, pagos, servicios)
                        estado_act = t.get("estado", "RESERVADO")
                        color_map = {"RESERVADO": "#FFA500", "ASISTIÓ": "#28a745", "AUSENTE": "#dc3545"}
                        border_color = color_map.get(estado_act, "#ccc")

                        with st.container(border=True):
                            st.markdown(f"""
                                <div style="background-color: {border_color}1A; border-radius: 8px; padding: 10px; border-left: 5px solid {border_color}; margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span style="background-color: {border_color}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem;">{t['hora']}</span>
                                        <span style="font-weight: bold; color: #444; font-size: 0.8rem;">{txt_plan}</span>
                                    </div>
                                    <div style="margin-top: 5px; font-weight: bold; font-size: 1.1rem; color: #1e1e1e;">{t['nombre_paciente']}</div>
                                    <div style="font-size: 0.85rem; color: #666;">{t['nombre_servicio']}</div>
                                    {f'<div style="color: #dc3545; font-weight: bold; font-size: 0.9rem; margin-top: 8px; border-top: 1px solid #dc354533; padding-top: 5px;">⚠️ DEUDA: ${deuda:,.0f}</div>' if deuda > 0 else ""}
                                </div>
                            """, unsafe_allow_html=True)

                            est = st.selectbox("Estado", opciones_asistencia, index=opciones_asistencia.index(estado_act) if estado_act in opciones_asistencia else 0, key=f"est_{t['id_turno']}")
                            
                            with st.expander("💰 Cobrar / Editar"):
                                c1, c2 = st.columns(2)
                                monto = c1.number_input("$ Pago", min_value=0, step=500, key=f"m_{t['id_turno']}")
                                medio = c2.selectbox("Medio", medios_pago, key=f"med_{t['id_turno']}")
                                
                                if st.button("💾 REGISTRAR", key=f"btn_{t['id_turno']}", use_container_width=True, type="primary"):
                                    if est == "AUSENTE":
                                        es_tarde = verificar_limite_24hs(t['fecha'], t['hora'])
                                        marcar_ausencia(sheet, t, servicios, penalizar=es_tarde)
                                    else:
                                        ejecutar_guardado_recepcion(sheet, t, est, monto, medio, turnos)
                                    st.session_state.refresh_data = True
                                    st.rerun()

                                st.markdown("---")
                                n_fecha = st.date_input("Nueva Fecha", value=date.fromisoformat(str(t['fecha'])), key=f"f_mod_{t['id_turno']}", format="DD/MM/YYYY")
                                n_hora = st.selectbox("Nueva Hora", horas_lista, index=horas_lista.index(t['hora']) if t['hora'] in horas_lista else 8, key=f"h_mod_{t['id_turno']}")
                                if st.button("🔄 Reprogramar", key=f"c_mod_{t['id_turno']}", use_container_width=True):
                                    modificar_o_penalizar_turno(sheet, t, servicios, n_fecha, n_hora, penalizar=False)
                                    st.session_state.refresh_data = True
                                    st.rerun()

    with tab_disponibilidad:
        st.subheader("🗓️ Disponibilidad Semanal")
        dias_es = {"Mon": "Lun", "Tue": "Mar", "Wed": "Mie", "Thu": "Jue", "Fri": "Vie"}
        bloque_manana = [f"{h:02d}:00" for h in range(8, 13)]
        bloque_tarde = [f"{h:02d}:00" for h in range(16, 21)]
        horas_filtradas = bloque_manana + bloque_tarde
        lunes_semana = date.today() - timedelta(days=date.today().weekday())
        dias_semana_list = [(lunes_semana + timedelta(days=i)) for i in range(5)]
        
        grid_cols = st.columns(len(dias_semana_list))
        for d_idx, fecha_dia in enumerate(dias_semana_list):
            with grid_cols[d_idx]:
                dia_txt = dias_es.get(fecha_dia.strftime('%a'), fecha_dia.strftime('%a'))
                st.markdown(f"<div style='text-align: center; font-weight: bold; font-size: 0.8rem;'>{dia_txt}<br>{fecha_dia.strftime('%d/%m')}</div>", unsafe_allow_html=True)
                fecha_str = fecha_dia.isoformat()
                for h in horas_filtradas:
                    ocupado = any(turno for turno in turnos if str(turno['fecha']) == fecha_str and turno['hora'] == h)
                    if not ocupado:
                        if st.button(f"{h}", key=f"f_{fecha_str}_{h}", use_container_width=True):
                            st.session_state.temp_fecha, st.session_state.temp_hora = fecha_dia, h
                            st.toast(f"Seleccionado {h}", icon="📍")
                    else:
                        st.button(f"{h}", key=f"o_{fecha_str}_{h}", disabled=True, use_container_width=True)

    with tab_nuevo:
        pacientes_dict = {p["nombre"]: p for p in pacientes if "nombre" in p}
        servicios_dict = {s["nombre"]: s for s in servicios if "nombre" in s}
        val_fecha = st.session_state.get("temp_fecha", date.today())
        val_hora = st.session_state.get("temp_hora", "09:00")
        with st.form("nuevo_turno_recepcion"):
            p_nombre = st.selectbox("Paciente", [""] + sorted(list(pacientes_dict.keys())))
            s_nombre = st.selectbox("Servicio", [""] + sorted(list(servicios_dict.keys())))
            f_inicio = st.date_input("Fecha", value=val_fecha, format="DD/MM/YYYY")
            h_cita = st.selectbox("Hora", horas_lista, index=horas_lista.index(val_hora) if val_hora in horas_lista else 0)
            dias_recurrencia = st.multiselect("Días recurrentes (Planes):", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
            if st.form_submit_button("🚀 CONFIRMAR TURNO"):
                if p_nombre and s_nombre:
                    ws_t = sheet.worksheet("turnos")
                    p_data, s_data = pacientes_dict[p_nombre], servicios_dict[s_nombre]
                    fechas_a_generar = []
                    if dias_recurrencia and "PLAN" in s_nombre.upper():
                        cant_sesiones = int(''.join(filter(str.isdigit, s_nombre)))
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
                    rows = [[id_base + i, f_str, h_cita, p_data["id_paciente"], p_nombre, p_data.get("tipo_cliente", "PUBLICO"), s_data["id_servicio"], s_nombre, "RESERVADO", "", ""] for i, f_str in enumerate(fechas_a_generar)]
                    ws_t.append_rows(rows)
                    st.session_state.refresh_data = True
                    st.rerun()

    with tab_paciente:
        st.subheader("👤 Registro")
        with st.form("form_registro_paciente"):
            n_nom, n_dni = st.text_input("Nombre y Apellido"), st.text_input("DNI")
            col_a, col_b = st.columns(2)
            n_tel, n_tipo = col_a.text_input("Celular"), col_b.selectbox("Tipo", ["PUBLICO", "SOCIO_GIM"])
            n_obs = st.text_area("Observaciones")
            if st.form_submit_button("💾 GUARDAR PACIENTE"):
                if n_nom and n_dni:
                    ws_pac = sheet.worksheet("pacientes")
                    ws_pac.append_row([len(pacientes) + 1, n_nom, n_dni, n_tel, n_tipo, date.today().isoformat(), "TRUE", n_obs])
                    st.session_state.refresh_data = True
                    st.success(f"Registrado: {n_nom}")
                    st.rerun()

def marcar_ausencia(sheet, turno, servicios, penalizar=False):
    ws_t = sheet.worksheet("turnos")
    all_t = ws_t.get_all_records()
    f_idx = next((i+2 for i, x in enumerate(all_t) if str(x.get('id_turno')) == str(turno.get('id_turno'))), None)
    if f_idx:
        ws_t.update_cell(f_idx, 9, "AUSENTE")
        if penalizar:
            serv = next((s for s in servicios if str(s['id_servicio']) == str(turno['id_servicio'])), {})
            precio_total = float(serv.get('precio', 0))
            num = 1
            if "PLAN" in str(serv.get('nombre', '')).upper():
                try: num = int(''.join(filter(str.isdigit, serv.get('nombre', '1'))))
                except: num = 1
            precio_sesion = precio_total / num
            ws_t.update_cell(f_idx, 10, precio_sesion)
            ws_t.update_cell(f_idx, 11, precio_sesion)

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
        fila = ids_col.index(str(turno['id_turno'])) + 1
        
        if estado == "ASISTIÓ":
            marcar_turno_asistio(ws_turnos, fila, turno, todos_los_turnos)
        else:
             ws_turnos.update_cell(fila, 9, estado)

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
                turno['id_paciente'],
                turno['id_servicio']
            ])
        st.success(f"Guardado!")
    except Exception as e:
        st.error(f"Error: {e}")