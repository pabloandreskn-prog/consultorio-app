import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import time
from domain.agenda_logic import (
    marcar_turno_asistio, marcar_turno_cancelado,
    actualizar_contador_plan, crear_entrada_plan
)

# ---- PROTECCIÓN ANTI-BLOQUEO (CACHE MAESTRO) ----
@st.cache_resource
def obtener_hojas_estaticas(_sheet):
    return {
        "turnos": _sheet.worksheet("turnos"),
        "planes": _sheet.worksheet("planes_pacientes"),
        "ventas": _sheet.worksheet("ventas"),
        "pagos": _sheet.worksheet("pagos"),
        "pacientes": _sheet.worksheet("pacientes"),
        "servicios": _sheet.worksheet("servicios")
    }

@st.cache_data(ttl=30)
def cargar_datos_seguros(_sheet):
    hojas = ["turnos", "planes_pacientes", "ventas", "pagos", "pacientes", "servicios"]
    resultados = {}
    try:
        for h in hojas:
            for intento in range(3):
                try:
                    nombre_clave = h if h != "planes_pacientes" else "planes"
                    resultados[nombre_clave] = _sheet.worksheet(h).get_all_records()
                    break
                except:
                    time.sleep(1)
        return resultados
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None

def limpiar_monto(valor):
    if valor == "" or valor is None: return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    if isinstance(valor, str):
        valor = valor.replace('$', '').replace('.', '').replace(',', '.')
    try: return float(valor)
    except: return 0.0

def generar_horarios():
    return [f"{h:02d}:00" for h in range(8, 21)]

def obtener_siguiente_id_local(datos_lista, nombre_columna):
    if not datos_lista: return 1
    try:
        ids = [int(row.get(nombre_columna, 0)) for row in datos_lista if str(row.get(nombre_columna)).isdigit()]
        return max(ids) + 1 if ids else 1
    except: return 1

# --- FUNCIÓN DE SINCRONIZACIÓN ---
def ejecutar_sincronizacion_maestra(sheet, datos):
    ws = obtener_hojas_estaticas(sheet)
    turnos = datos["turnos"]
    ventas_existentes = datos["ventas"]
    planes_existentes = datos["planes"]
    servicios = datos["servicios"]
    
    ventas_set = {(str(v['id_paciente']), str(v['id_servicio']), str(v['fecha'])) for v in ventas_existentes}
    nuevas_ventas, nuevos_planes = [], []
    nid_v = obtener_siguiente_id_local(ventas_existentes, "id_venta")
    nid_pl = obtener_siguiente_id_local(planes_existentes, "id_plan_paciente")
    
    for t in turnos:
        if t.get("estado") == "CANCELADO": continue
        id_p, id_s, fecha_t = str(t['id_paciente']), str(t['id_servicio']), str(t['fecha'])
        
        if (id_p, id_s, fecha_t) not in ventas_set:
            ser = next((s for s in servicios if str(s['id_servicio']) == id_s), None)
            if ser:
                sesiones = int(ser.get('sesiones', 1))
                procesar = True
                if sesiones > 1:
                    procesar = not any(str(pl['id_paciente']) == id_p and str(pl['id_servicio']) == id_s and pl['estado'] == 'ACTIVO' for pl in planes_existentes)
                
                if procesar:
                    nuevas_ventas.append([nid_v, fecha_t, fecha_t[:7], id_p, t['nombre_paciente'], id_s, t.get('tipo_cliente','GENERAL'), limpiar_monto(ser.get('precio_teorico', 0)), "NO", "PENDIENTE", sesiones, 0])
                    if sesiones > 1:
                        nuevos_planes.append([nid_pl, id_p, id_s, sesiones, 0, "ACTIVO", fecha_t, t['nombre_paciente']])
                        nid_pl += 1
                    nid_v += 1

    if nuevas_ventas: ws["ventas"].append_rows(nuevas_ventas)
    if nuevos_planes: ws["planes"].append_rows(nuevos_planes)
    return len(nuevas_ventas)

# --- INTERFAZ PRINCIPAL ---
def agenda_ui(sheet, pacientes=None, servicios=None, planes_pacientes=None):
    if 'semana_offset' not in st.session_state: st.session_state.semana_offset = 0

    datos = cargar_datos_seguros(sheet)
    ws = obtener_hojas_estaticas(sheet)
    if not datos: st.stop()

    with st.sidebar:
        st.divider()
        st.markdown("### 🛠 Herramientas de Datos")
        if st.button("🔄 Sincronizar Ventas/Planes Faltantes"):
            with st.spinner("Procesando..."):
                cant = ejecutar_sincronizacion_maestra(sheet, datos)
                st.success(f"Se recuperaron {cant} registros.")
                st.cache_data.clear(); time.sleep(1); st.rerun()

    tab_ag, tab_lib, tab_tur, tab_pac = st.tabs(["📅 Agenda Diaria", "🔍 Buscador Libres", "➕ Agendar Turno/Venta", "👤 Ficha Paciente"])

    with tab_ag:
        c1, c2 = st.columns(2)
        f_sel = c1.date_input("Ver día:", value=date.today(), key="ag_f")
        busq = c2.text_input("🔍 Buscar paciente...", key="ag_b")

        # Obtenemos los turnos del día
        t_dia = [(i + 2, t) for i, t in enumerate(datos["turnos"]) 
                 if str(t.get("fecha")) == str(f_sel) and t.get("estado") != "CANCELADO" and (busq.lower() in str(t.get("nombre_paciente", "")).lower())]

        # --- MODIFICACIÓN QUIRÚRGICA: ORDENAMIENTO POR HORA ---
        # Ordenamos la lista t_dia basándonos en el campo 'hora' del diccionario del turno (índice 1 de la tupla)
        t_dia.sort(key=lambda x: x[1].get("hora", "00:00"))
        # --------------------------------------------------------

        if not t_dia:
            st.info("No hay turnos para esta fecha.")
        else:
            cols = st.columns(3)
            for idx, (fila_real, t) in enumerate(t_dia):
                with cols[idx % 3]:
                    # Cálculo de Deuda
                    v_pac = sum(limpiar_monto(v.get("monto_total", 0)) for v in datos["ventas"] if str(v.get("id_paciente")) == str(t["id_paciente"]))
                    p_pac = sum(limpiar_monto(p.get("monto", 0)) for p in datos["pagos"] if str(p.get("id_paciente")) == str(t["id_paciente"]))
                    deuda = max(0.0, v_pac - p_pac)
                    
                    # --- LÓGICA DE CONTEO ROBUSTA ---
                    us, tot = 0, 0
                    plan_activo = next((pl for pl in datos["planes"] 
                                      if str(pl.get("id_paciente")) == str(t["id_paciente"]) 
                                      and str(pl.get("id_servicio")) == str(t["id_servicio"]) 
                                      and pl.get("estado") == "ACTIVO"), None)
                    
                    if plan_activo:
                        tot = int(plan_activo.get("sesiones_totales", 0))
                        fecha_inicio_plan = str(plan_activo.get("fecha_inicio", "1900-01-01"))
                        # Contamos solo asistencias desde la fecha de este plan específico
                        asistencias = [tn for tn in datos["turnos"] 
                                     if str(tn.get("id_paciente")) == str(t["id_paciente"]) 
                                     and str(tn.get("id_servicio")) == str(t["id_servicio"]) 
                                     and str(tn.get("estado")).strip().upper() == "ASISTIÓ"
                                     and str(tn.get("fecha")) >= fecha_inicio_plan]
                        us = len(asistencias)
                    
                    # UI de la tarjeta
                    restantes = tot - us
                    color_barra = "#d32f2f" if restantes <= 1 and tot > 0 else "#4caf50"
                    porcentaje = (min(us, tot) / tot * 100) if tot > 0 else 0
                    color_borde = "#d32f2f" if deuda > 0 else ("#ffc107" if t["estado"] == "RESERVADO" else "#4caf50")
                    
                    with st.container(border=True):
                        st.markdown(f"""
                            <div style='display:flex; justify-content:space-between; align-items:center;'>
                                <b style='font-size:1.1em;'>{t['hora']} hs</b>
                                <div style='width:50%; background:#e0e0e0; border-radius:10px; height:6px;'>
                                    <div style='width:{porcentaje}%; background:{color_barra}; border-radius:10px; height:6px;'></div>
                                </div>
                            </div>
                            <div style='border-left:5px solid {color_borde}; padding-left:10px; background-color:{color_borde}15; margin:8px 0; border-radius:4px;'>
                                <div style='font-weight:bold;'>{t['nombre_paciente']}</div>
                                <div style='font-size:0.8em; color:#555;'>{t['nombre_servicio']}</div>
                                <div style='text-align:right; font-size:0.75em;'>Sesiones: {us}/{tot}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if deuda > 0:
                            st.markdown(f"<p style='color:#d32f2f; font-weight:bold; font-size:0.8em; margin:0;'>⚠️ DEUDA: ${deuda:,.0f}</p>", unsafe_allow_html=True)

                        # --- RECUPERACIÓN DE BOTONES ASISTIÓ / FALTÓ ---
                        if t["estado"] == "RESERVADO":
                            cb1, cb2 = st.columns(2)
                            if cb1.button("✅ Asistió", key=f"as_{t['id_turno']}_{idx}", use_container_width=True):
                                ws["turnos"].update_cell(fila_real, 9, "ASISTIÓ")
                                # Sincronizar con el contador de la hoja planes si es necesario
                                if plan_activo:
                                    actualizar_contador_plan(sheet, t["id_paciente"], t["id_servicio"])
                                st.cache_data.clear(); st.rerun()
                            if cb2.button("🚫 Faltó", key=f"fa_{t['id_turno']}_{idx}", use_container_width=True):
                                ws["turnos"].update_cell(fila_real, 9, "AUSENTE")
                                st.cache_data.clear(); st.rerun()
                        
                        exp = st.expander("🛠 Acciones")
                        with exp:
                            c_rep, c_can = st.columns(2)
                            with c_rep:
                                with st.popover("📅 Reprogramar", use_container_width=True):
                                    n_f = st.date_input("Nueva Fecha", value=f_sel, key=f"nf_{t['id_turno']}")
                                    n_h = st.selectbox("Nueva Hora", generar_horarios(), key=f"nh_{t['id_turno']}")
                                    if st.button("Confirmar", key=f"re_{t['id_turno']}", use_container_width=True):
                                        ws["turnos"].update_cell(fila_real, 2, str(n_f))
                                        ws["turnos"].update_cell(fila_real, 3, n_h)
                                        st.cache_data.clear(); st.rerun()
                            
                            if c_can.button("🗑 Cancelar", key=f"can_{t['id_turno']}", use_container_width=True):
                                ws["turnos"].update_cell(fila_real, 9, "CANCELADO")
                                st.cache_data.clear(); st.rerun()

                            st.divider()
                            st.markdown("**💰 Cobrar**")
                            with st.form(f"pago_{t['id_turno']}"):
                                m_p = st.number_input("Monto", value=deuda if deuda > 0 else 0.0)
                                met = st.selectbox("Método", ["EFECTIVO", "TRANSFERENCIA", "MP"])
                                if st.form_submit_button("Registrar Pago", use_container_width=True):
                                    fh = datetime.now().strftime("%Y-%m-%d")
                                    nid_p = obtener_siguiente_id_local(datos["pagos"], "id_pago")
                                    ws["pagos"].append_row([nid_p, fh, fh[:7], t["nombre_paciente"], m_p, met, "Agenda", t["id_paciente"], t["id_servicio"]])
                                    st.cache_data.clear(); st.rerun()

    with tab_lib:
        st.subheader("🔍 Horarios libres")
        c_i, c_m, c_d = st.columns([1, 2, 1])
        if c_i.button("⬅️ Anterior"): st.session_state.semana_offset -= 1; st.rerun()
        if c_d.button("Siguiente ➡️"): st.session_state.semana_offset += 1; st.rerun()
        
        hoy = date.today()
        inicio = (hoy - timedelta(days=hoy.weekday())) + timedelta(weeks=st.session_state.semana_offset)
        c_m.markdown(f"<h4 style='text-align:center;'>Semana del {inicio.strftime('%d/%m')}</h4>", unsafe_allow_html=True)
        
        # --- MODIFICACIÓN QUIRÚRGICA: DÍAS EN ESPAÑOL Y FORMATO AMIGABLE ---
        dias_esp = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        # -------------------------------------------------------------------
        
        cols_dias = st.columns(len(dias_esp))
        for i, d_label in enumerate(dias_esp):
            d = inicio + timedelta(days=i)
            with cols_dias[i]:
                st.markdown(f"**{d_label} {d.day}/{d.month}**")
                ocup = [tn["hora"] for tn in datos["turnos"] if str(tn["fecha"]) == str(d) and tn["estado"] != "CANCELADO"]
                for h in generar_horarios():
                    if h in ocup: st.button(f"🔴 {h}", key=f"lib_{d}_{h}", disabled=True, use_container_width=True)
                    else:
                        if st.button(f"🟢 {h}", key=f"lib_{d}_{h}", use_container_width=True):
                            st.session_state.temp_fecha, st.session_state.temp_hora = d, h
                            st.toast(f"Seleccionado: {d} {h}")

    with tab_tur:
        st.subheader("➕ Agendar Turno y Venta")
        tipo_agenda = st.radio("Modalidad:", ["Turno Único", "Días fijos (Plan)"], horizontal=True)
        with st.form("nuevo_turno"):
            p_sel = st.selectbox("Paciente", [p["nombre"] for p in datos["pacientes"]])
            s_sel = st.selectbox("Servicio", [s["nombre"] for s in datos["servicios"]])
            
            if tipo_agenda == "Turno Único":
                f_n = st.date_input("Fecha", value=st.session_state.get('temp_fecha', date.today()))
                h_n = st.selectbox("Hora", generar_horarios(), index=generar_horarios().index(st.session_state.get('temp_hora', '08:00')) if st.session_state.get('temp_hora') in generar_horarios() else 0)
            else:
                c_d, c_h = st.columns(2)
                dias_sel = c_d.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
                h_n = c_h.selectbox("Hora Fija", generar_horarios())
                c_f, c_c = st.columns(2)
                f_n = c_f.date_input("Desde:", value=date.today())
                cant_turnos = c_c.number_input("Cantidad total", min_value=2, max_value=40, value=10)
            
            if st.form_submit_button("Confirmar Reserva"):
                pac = next(p for p in datos["pacientes"] if p["nombre"] == p_sel)
                ser = next(s for s in datos["servicios"] if s["nombre"] == s_sel)
                nid_t = obtener_siguiente_id_local(datos["turnos"], "id_turno")
                
                nuevos_turnos = []
                if tipo_agenda == "Turno Único":
                    nuevos_turnos.append([nid_t, str(f_n), h_n, pac["id_paciente"], pac["nombre"], pac.get("tipo_cliente","GENERAL"), ser["id_servicio"], ser["nombre"], "RESERVADO"])
                else:
                    mapa_dias = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                    dias_num = [mapa_dias[d] for d in dias_sel]
                    t_creados, f_actual = 0, f_n
                    while t_creados < cant_turnos:
                        if f_actual.weekday() in dias_num:
                            nuevos_turnos.append([nid_t + t_creados, str(f_actual), h_n, pac["id_paciente"], pac["nombre"], pac.get("tipo_cliente","GENERAL"), ser["id_servicio"], ser["nombre"], "RESERVADO"])
                            t_creados += 1
                        f_actual += timedelta(days=1)
                
                if len(nuevos_turnos) == 1: ws["turnos"].append_row(nuevos_turnos[0])
                else: ws["turnos"].append_rows(nuevos_turnos)
                
                nid_v = obtener_siguiente_id_local(datos["ventas"], "id_venta")
                sesiones = int(ser.get("sesiones", 1))
                ws["ventas"].append_row([nid_v, str(f_n), str(f_n)[:7], pac["id_paciente"], pac["nombre"], ser["id_servicio"], pac.get("tipo_cliente","GENERAL"), limpiar_monto(ser.get("precio_teorico", 0)), "NO", "PENDIENTE", sesiones, 0])
                if sesiones > 1:
                    nid_pl = obtener_siguiente_id_local(datos["planes"], "id_plan_paciente")
                    ws["planes"].append_row([nid_pl, pac["id_paciente"], ser["id_servicio"], sesiones, 0, "ACTIVO", str(f_n), pac["nombre"]])
                
                st.success("✅ Reserva completada")
                st.cache_data.clear(); time.sleep(1); st.rerun()

    with tab_pac:
        st.subheader("👤 Registro de Paciente")
        with st.form("alta_pac"):
            nom = st.text_input("Nombre y Apellido")
            dni = st.text_input("DNI")
            tel = st.text_input("Teléfono")
            tip = st.selectbox("Categoría", ["GENERAL", "SOCIO_GIM", "PUBLICO"])
            if st.form_submit_button("Guardar"):
                if nom:
                    nid = obtener_siguiente_id_local(datos["pacientes"], "id_paciente")
                    ws["pacientes"].append_row([nid, nom, dni, tel, tip, datetime.now().strftime("%Y-%m-%d"), "TRUE", ""])
                    st.success("Paciente registrado")
                    st.cache_data.clear(); time.sleep(1); st.rerun()
