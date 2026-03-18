import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import time
from domain.agenda_logic import (
    marcar_turno_asistio, marcar_turno_cancelado,
    actualizar_contador_plan, crear_entrada_plan
)

# --- CARGA DE DATOS MASTER (Protección Anti-Bloqueos) ---
@st.cache_data(ttl=60)
def cargar_todo_el_sistema(_sheet):
    """Carga única para máxima velocidad y ahorro de cuota."""
    try:
        return {
            "turnos": _sheet.worksheet("turnos").get_all_records(),
            "planes": _sheet.worksheet("planes_pacientes").get_all_records(),
            "ventas": _sheet.worksheet("ventas").get_all_records(),
            "pagos": _sheet.worksheet("pagos").get_all_records(),
            "pacientes": _sheet.worksheet("pacientes").get_all_records(),
            "servicios": _sheet.worksheet("servicios").get_all_records()
        }
    except Exception as e:
        st.error(f"Error de conexión crítica: {e}")
        return None

def limpiar_monto(valor):
    if valor == "" or valor is None: return 0.0
    if isinstance(valor, str):
        valor = str(valor).replace('$', '').replace('.', '').replace(',', '.')
    try:
        return float(valor)
    except:
        return 0.0

def generar_horarios():
    return [f"{h:02d}:00" for h in range(8, 21)]

def obtener_siguiente_id_local(datos_lista, nombre_columna):
    """Busca el ID más alto localmente para evitar consultas extra a Google."""
    if not datos_lista: return 1
    try:
        ids = []
        for row in datos_lista:
            val = row.get(nombre_columna)
            if val is not None and str(val).isdigit():
                ids.append(int(val))
        return max(ids) + 1 if ids else 1
    except:
        return 1

# --- INTERFAZ PRINCIPAL ---
def agenda_ui(sheet, p_old, s_old, pl_old):
    datos = cargar_todo_el_sistema(sheet)
    if not datos: st.stop()

    ws_turnos = sheet.worksheet("turnos")
    ws_ventas = sheet.worksheet("ventas")
    ws_pagos = sheet.worksheet("pagos")
    ws_planes = sheet.worksheet("planes_pacientes")

    tab_ag, tab_lib, tab_tur, tab_pac = st.tabs(["📅 Agenda Diaria", "🔍 Buscador Semanal Libres", "➕ Agendar Turno/Venta", "👤 Ficha/Nuevo Paciente"])

    with tab_ag:
        c1, c2 = st.columns(2)
        f_sel = c1.date_input("Ver día:", value=date.today(), key="ag_f")
        busq = c2.text_input("🔍 Buscar paciente...", key="ag_b")

        t_dia = [(i + 2, t) for i, t in enumerate(datos["turnos"]) 
                 if str(t.get("fecha")) == str(f_sel) and (busq.lower() in str(t.get("nombre_paciente", "")).lower())]

        if not t_dia:
            st.info("No hay turnos para esta fecha.")
        else:
            cols = st.columns(3)
            for idx, (fila, t) in enumerate(t_dia):
                with cols[idx % 3]:
                    t_v = sum(limpiar_monto(v.get("monto_total", 0)) for v in datos["ventas"] if str(v.get("id_paciente")) == str(t["id_paciente"]))
                    t_p = sum(limpiar_monto(p.get("monto", 0)) for p in datos["pagos"] if str(p.get("id_paciente")) == str(t["id_paciente"]))
                    deuda = max(0.0, t_v - t_p)
                    
                    us, tot = 0, 0
                    for pl in datos["planes"]:
                        if str(pl.get("id_paciente")) == str(t["id_paciente"]) and str(pl.get("id_servicio")) == str(t["id_servicio"]):
                            us, tot = int(pl.get("sesiones_usadas", 0)), int(pl.get("sesiones_totales", 0))

                    color_borde = "#d32f2f" if deuda > 0 else ("#ffc107" if t["estado"] == "RESERVADO" else "#4caf50")
                    
                    with st.container(border=True):
                        st.markdown(f"""
                            <div style='display:flex; justify-content:space-between; align-items:center;'>
                                <b style='font-size:1.1em;'>{t['hora']} hs</b>
                                <span style='background:#f0f2f6; padding:2px 6px; border-radius:4px; font-size:0.75em; color:#666;'>ID {t['id_turno']}</span>
                            </div>
                            <div style='border-left:5px solid {color_borde}; padding-left:10px; background-color:{color_borde}10; margin:10px 0;'>
                                <div style='font-weight:bold; color:#333;'>{t['nombre_paciente']}</div>
                                <div style='font-size:0.85em; color:#666;'>{t['nombre_servicio']}</div>
                                <div style='text-align:right; font-size:0.8em; color:#444;'>📊 {us}/{tot}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if deuda > 0:
                            st.markdown(f"<p style='color:#d32f2f; font-weight:bold; font-size:0.85em; margin:0;'>⚠️ DEUDA: ${deuda:,.0f}</p>", unsafe_allow_html=True)

                        nuevo_est = st.selectbox("Estado", ["RESERVADO", "ASISTIÓ", "AUSENTE", "CANCELADO"], 
                                                index=["RESERVADO", "ASISTIÓ", "AUSENTE", "CANCELADO"].index(t["estado"]) if t["estado"] in ["RESERVADO", "ASISTIÓ", "AUSENTE", "CANCELADO"] else 0,
                                                key=f"st_{t['id_turno']}_{fila}")
                        
                        if nuevo_est != t["estado"]:
                            ws_turnos.update_cell(fila, 9, nuevo_est)
                            if nuevo_est == "ASISTIÓ":
                                actualizar_contador_plan(sheet, t["id_paciente"], t["id_servicio"])
                            st.cache_data.clear()
                            st.rerun()

                        with st.expander("⚙️ Modificar / Cobrar"):
                            fecha_reprog = st.date_input("Nueva Fecha", value=pd.to_datetime(t['fecha']).date(), key=f"f_re_{t['id_turno']}_{fila}")
                            hora_reprog = st.selectbox("Nueva Hora", generar_horarios(), index=generar_horarios().index(t['hora']), key=f"h_re_{t['id_turno']}_{fila}")
                            
                            if st.button("🔄 Guardar Cambios", key=f"btn_re_{t['id_turno']}_{fila}", use_container_width=True):
                                ws_turnos.update_cell(fila, 2, str(fecha_reprog))
                                ws_turnos.update_cell(fila, 3, hora_reprog)
                                st.cache_data.clear()
                                st.rerun()

                            st.divider()
                            with st.form(f"fc_{t['id_turno']}_{fila}"):
                                m_c = st.number_input("Monto a cobrar", value=0.0, key=f"mc_{t['id_turno']}")
                                f_p = st.selectbox("Método", ["EFECTIVO", "TRANSFERENCIA", "MP"], key=f"fp_{t['id_turno']}")
                                if st.form_submit_button("💰 Confirmar Pago", use_container_width=True):
                                    fh = datetime.now().strftime("%Y-%m-%d")
                                    nid_pag = obtener_siguiente_id_local(datos["pagos"], "id_pago")
                                    ws_pagos.append_row([nid_pag, fh, fh[:7], t["nombre_paciente"], m_c, f_p, "Agenda", t["id_paciente"], t["id_servicio"]])
                                    st.cache_data.clear()
                                    st.rerun()

    with tab_lib:
        st.subheader("Buscador de horarios libres")
        hoy = date.today()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        dias_semana = [inicio_semana + timedelta(days=i) for i in range(5)]
        
        cols_dias = st.columns(5)
        for idx_d, d in enumerate(dias_semana):
            with cols_dias[idx_d]:
                st.markdown(f"**{['Lun','Mar','Mié','Jue','Vie'][idx_d]} {d.day}/{d.month}**")
                ocupados = [turn["hora"] for turn in datos["turnos"] if str(turn["fecha"]) == str(d) and turn["estado"] != "CANCELADO"]
                for h in generar_horarios():
                    if h in ocupados:
                        st.button(f"🔴 {h}", key=f"lib_{d}_{h}", disabled=True, use_container_width=True)
                    else:
                        if st.button(f"🟢 {h}", key=f"lib_{d}_{h}", use_container_width=True):
                            st.session_state.temp_fecha = d
                            st.session_state.temp_hora = h
                            st.toast(f"Seleccionado: {d} {h}")

    with tab_tur:
        st.subheader("➕ Agendar Turno y Venta")
        with st.form("f_nuevo_turbo_full"):
            p_sel = st.selectbox("Paciente", [p["nombre"] for p in datos["pacientes"]])
            s_sel = st.selectbox("Servicio", [s["nombre"] for s in datos["servicios"]])
            f_n = st.date_input("Fecha", value=st.session_state.get('temp_fecha', date.today()))
            h_n = st.selectbox("Hora", generar_horarios(), index=generar_horarios().index(st.session_state.get('temp_hora', '08:00')))
            
            if st.form_submit_button("Confirmar Turno y Generar Venta", use_container_width=True):
                # 1. Obtener objetos de datos
                pac = next(p for p in datos["pacientes"] if p["nombre"] == p_sel)
                ser = next(s for s in datos["servicios"] if s["nombre"] == s_sel)
                fh = datetime.now().strftime("%Y-%m-%d")
                
                # 2. Extraer valores del servicio (QUIRÚRGICO)
                precio_real = limpiar_monto(ser.get("precio_teorico", 0))
                sesiones_reales = int(ser.get("sesiones", 1))
                
                # 3. Generar IDs dinámicos basados en los nombres de columna reales
                nid_t = obtener_siguiente_id_local(datos["turnos"], "id_turno")
                nid_v = obtener_siguiente_id_local(datos["ventas"], "id_venta")
                nid_p = obtener_siguiente_id_local(datos["planes"], "id_plan_paciente")
                
                # --- EJECUCIÓN DE REGISTROS ---
                # A. REGISTRO EN TURNOS
                ws_turnos.append_row([nid_t, str(f_n), h_n, pac["id_paciente"], pac["nombre"], pac.get("condicion","GENERAL"), ser["id_servicio"], ser["nombre"], "RESERVADO"])
                
                # B. REGISTRO EN VENTAS
                ws_ventas.append_row([nid_v, fh, fh[:7], pac["id_paciente"], pac["nombre"], ser["id_servicio"], precio_real, "NO", "PENDIENTE", sesiones_reales, 0, "PENDIENTE"])
                
                # C. REGISTRO EN PLANES (Solo si sesiones > 1)
                if sesiones_reales > 1:
                    ws_planes.append_row([nid_p, pac["id_paciente"], ser["id_servicio"], sesiones_reales, 0, "ACTIVO", fh])
                
                if 'temp_fecha' in st.session_state: del st.session_state['temp_fecha']
                if 'temp_hora' in st.session_state: del st.session_state['temp_hora']
                
                st.cache_data.clear()
                st.success(f"✅ Registrado: Turno, Venta (${precio_real:,.0f}) y Plan.")
                time.sleep(1)
                st.rerun()

    with tab_pac:
        st.subheader("👤 Alta de Nuevo Paciente")
        with st.form("f_alta_ag"):
            nom_n = st.text_input("Nombre Completo (Apellido Nombre)")
            dni_n = st.text_input("DNI")
            cat_n = st.selectbox("Categoría", ["GENERAL", "SOCIO", "PLAN"])
            tel_n = st.text_input("Teléfono")
            if st.form_submit_button("Guardar Paciente", use_container_width=True):
                if nom_n and dni_n:
                    nid_pac = obtener_siguiente_id_local(datos["pacientes"], "id_paciente")
                    sheet.worksheet("pacientes").append_row([nid_pac, nom_n, cat_n, dni_n, tel_n, "Alta Agenda"])
                    st.cache_data.clear()
                    st.success(f"Paciente {nom_n} creado.")
                    time.sleep(1)
                    st.rerun()