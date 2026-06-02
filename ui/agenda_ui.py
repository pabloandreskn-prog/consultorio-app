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
    horarios = []
    for h in range(8, 21):  
        horarios.append(f"{h:02d}:00")
        horarios.append(f"{h:02d}:30")
    return horarios

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
    
    ventas_set = {(str(v.get('id_paciente', '')), str(v.get('id_servicio', '')), str(v.get('fecha', ''))) for v in ventas_existentes}
    nuevas_ventas, nuevos_planes = [], []
    nid_v = obtener_siguiente_id_local(ventas_existentes, "id_venta")
    nid_pl = obtener_siguiente_id_local(planes_existentes, "id_plan_paciente")
    
    for t in turnos:
        if str(t.get("estado", "")) == "CANCELADO": continue
        id_p, id_s, fecha_t = str(t.get('id_paciente', '')), str(t.get('id_servicio', '')), str(t.get('fecha', ''))
        
        # Ignorar filas vacías
        if not id_p or not id_s: continue

        if (id_p, id_s, fecha_t) not in ventas_set:
            ser = next((s for s in servicios if str(s.get('id_servicio', '')) == id_s), None)
            if ser:
                sesiones = int(ser.get('sesiones', 1))
                procesar = True
                if sesiones > 1:
                    procesar = not any(str(pl.get('id_paciente')) == id_p and str(pl.get('id_servicio')) == id_s and str(pl.get('estado')) == 'ACTIVO' for pl in planes_existentes)
                
                if procesar:
                    nuevas_ventas.append([nid_v, fecha_t, fecha_t[:7], id_p, t.get('nombre_paciente', ''), id_s, t.get('tipo_cliente','GENERAL'), limpiar_monto(ser.get('precio_teorico', 0)), "NO", "PENDIENTE", sesiones, 0])
                    if sesiones > 1:
                        nuevos_planes.append([nid_pl, id_p, id_s, sesiones, 0, "ACTIVO", fecha_t, t.get('nombre_paciente', '')])
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

    # --- PRE-CÁLCULO DE DEUDAS (Optimizado para evitar lentitud) ---
    df_ventas = pd.DataFrame(datos["ventas"])
    df_pagos = pd.DataFrame(datos["pagos"])
    
    # Manejo seguro por si las hojas están vacías o faltan columnas
    if not df_ventas.empty and 'id_paciente' in df_ventas.columns:
        df_ventas['monto_total'] = df_ventas.get('monto_total', pd.Series(dtype=float)).apply(limpiar_monto)
        resumen_ventas = df_ventas.groupby('id_paciente')['monto_total'].sum()
    else: resumen_ventas = pd.Series(dtype=float)

    if not df_pagos.empty and 'id_paciente' in df_pagos.columns:
        df_pagos['monto'] = df_pagos.get('monto', pd.Series(dtype=float)).apply(limpiar_monto)
        resumen_pagos = df_pagos.groupby('id_paciente')['monto'].sum()
    else: resumen_pagos = pd.Series(dtype=float)

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

        # Filtro de turnos usando .get() para proteger contra KeyErrors en filas vacías
        t_dia = [(i + 2, t) for i, t in enumerate(datos["turnos"]) 
                 if str(t.get("fecha", "")) == str(f_sel) and str(t.get("estado", "")) != "CANCELADO" and (busq.lower() in str(t.get("nombre_paciente", "")).lower())]

        t_dia.sort(key=lambda x: str(x[1].get("hora", "23:59")).strip())

        if not t_dia:
            st.info("No hay turnos para esta fecha.")
        else:
            cols = st.columns(3)
            for idx, (fila_real, t) in enumerate(t_dia):
                with cols[idx % 3]:
                    # --- CÁLCULO DE DEUDA INTEGRAL ---
                    id_pac = t.get("id_paciente", "")
                    total_v = resumen_ventas.get(id_pac, 0.0)
                    total_p = resumen_pagos.get(id_pac, 0.0)
                    deuda = round(max(0.0, total_v - total_p), 2)
                    es_deudor = deuda > 50 # Margen de error por centavos

                    # --- LÓGICA DE SESIONES ---
                    us, tot = 0, 0
                    id_serv = t.get("id_servicio", "")
                    plan_activo = next((pl for pl in datos["planes"] 
                                      if str(pl.get("id_paciente", "")) == str(id_pac) 
                                      and str(pl.get("id_servicio", "")) == str(id_serv) 
                                      and str(pl.get("estado", "")) == "ACTIVO"), None)
                    
                    if plan_activo:
                        tot = int(plan_activo.get("sesiones_totales", 0))
                        asistencias = [tn for tn in datos["turnos"] 
                                     if str(tn.get("id_paciente", "")) == str(id_pac) 
                                     and str(tn.get("id_servicio", "")) == str(id_serv) 
                                     and str(tn.get("estado", "")).strip().upper() == "ASISTIÓ"]
                        us = len(asistencias)
                    
                    # --- ESTILO VISUAL ---
                    estado_turno = str(t.get("estado", ""))
                    color_borde = "#d32f2f" if es_deudor else ("#ffc107" if estado_turno == "RESERVADO" else "#4caf50")
                    color_fondo = "#fff0f0" if es_deudor else "#ffffff"
                    porcentaje = (min(us, tot) / tot * 100) if tot > 0 else 0

                    with st.container(border=True):
                        # Usamos .get() en el renderizado HTML por seguridad
                        st.markdown(f"""
                            <div style='background-color:{color_fondo}; padding:5px; border-radius:5px;'>
                                <div style='display:flex; justify-content:space-between; align-items:center;'>
                                    <b style='font-size:1.1em;'>{str(t.get('hora', ''))} hs</b>
                                    <div style='width:40%; background:#e0e0e0; border-radius:10px; height:6px;'>
                                        <div style='width:{porcentaje}%; background:#4caf50; border-radius:10px; height:6px;'></div>
                                    </div>
                                </div>
                                <div style='border-left:5px solid {color_borde}; padding-left:10px; margin:8px 0;'>
                                    <div style='font-weight:bold; font-size:1.05em; color:{"#b71c1c" if es_deudor else "#000000"};'>{str(t.get('nombre_paciente', ''))}</div>
                                    <div style='font-size:0.85em; color:#444;'>{str(t.get('nombre_servicio', ''))}</div>
                                    <div style='text-align:right; font-size:0.75em; color:#666;'>Sesiones: {us}/{tot}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if es_deudor:
                            st.markdown(f"""
                                <div style='background-color:#d32f2f; color:white; text-align:center; 
                                border-radius:4px; font-weight:bold; font-size:0.9em; padding:3px; margin: 5px 0;'>
                                    ⚠️ DEUDA: ${deuda:,.0f}
                                </div>
                            """, unsafe_allow_html=True)

                        if estado_turno == "RESERVADO":
                            cb1, cb2 = st.columns(2)
                            id_turno_real = t.get('id_turno', idx)
                            if cb1.button("✅ Asistió", key=f"as_{id_turno_real}_{idx}", use_container_width=True):
                                ws["turnos"].update_cell(fila_real, 9, "ASISTIÓ")
                                if plan_activo: actualizar_contador_plan(sheet, id_pac, id_serv)
                                st.cache_data.clear(); st.rerun()
                            if cb2.button("🚫 Faltó", key=f"fa_{id_turno_real}_{idx}", use_container_width=True):
                                ws["turnos"].update_cell(fila_real, 9, "AUSENTE")
                                st.cache_data.clear(); st.rerun()
                        
                        exp = st.expander("🛠 Gestión / Cobro")
                        with exp:
                            c_rep, c_can = st.columns(2)
                            id_turno_real = t.get('id_turno', idx)
                            with c_rep:
                                with st.popover("📅 Mover", use_container_width=True):
                                    n_f = st.date_input("Nueva Fecha", value=f_sel, key=f"nf_{id_turno_real}")
                                    n_h = st.selectbox("Nueva Hora", generar_horarios(), key=f"nh_{id_turno_real}")
                                    if st.button("Confirmar", key=f"re_{id_turno_real}", use_container_width=True):
                                        ws["turnos"].update_cell(fila_real, 2, str(n_f))
                                        ws["turnos"].update_cell(fila_real, 3, n_h)
                                        st.cache_data.clear(); st.rerun()
                            
                            if c_can.button("🗑 Borrar", key=f"can_{id_turno_real}", use_container_width=True):
                                ws["turnos"].update_cell(fila_real, 9, "CANCELADO")
                                st.cache_data.clear(); st.rerun()

                            st.divider()
                            with st.form(f"pago_{id_turno_real}"):
                                m_p = st.number_input("Registrar Pago ($)", value=float(deuda) if es_deudor else 0.0, step=500.0)
                                met = st.selectbox("Método", ["EFECTIVO", "TRANSFERENCIA", "MP"])
                                if st.form_submit_button("💰 Confirmar Pago", use_container_width=True):
                                    fh = datetime.now().strftime("%Y-%m-%d")
                                    nid_p = obtener_siguiente_id_local(datos["pagos"], "id_pago")
                                    ws["pagos"].append_row([nid_p, fh, fh[:7], t.get("nombre_paciente", ""), m_p, met, "Agenda", id_pac, id_serv])
                                    st.success("Pago registrado")
                                    st.cache_data.clear(); time.sleep(1); st.rerun()

    with tab_lib:
        st.subheader("🔍 Horarios libres")
        c_i, c_m, c_d = st.columns([1, 2, 1])
        if c_i.button("⬅️ Anterior"): st.session_state.semana_offset -= 1; st.rerun()
        if c_d.button("Siguiente ➡️"): st.session_state.semana_offset += 1; st.rerun()
        
        hoy = date.today()
        inicio = (hoy - timedelta(days=hoy.weekday())) + timedelta(weeks=st.session_state.semana_offset)
        c_m.markdown(f"<h4 style='text-align:center;'>Semana del {inicio.strftime('%d/%m')}</h4>", unsafe_allow_html=True)
        
        dias_esp = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        cols_dias = st.columns(len(dias_esp))
        for i, d_label in enumerate(dias_esp):
            d = inicio + timedelta(days=i)
            with cols_dias[i]:
                st.markdown(f"**{d_label} {d.day}/{d.month}**")
                
                # --- SOLUCIÓN QUIRÚRGICA AL KEYERROR 'fecha' ---
                ocup = [str(tn.get("hora", "")) for tn in datos["turnos"] 
                        if str(tn.get("fecha", "")) == str(d) and str(tn.get("estado", "")) != "CANCELADO"]
                
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
            p_sel = st.selectbox("Paciente", [p.get("nombre", "") for p in datos["pacientes"] if p.get("nombre")])
            s_sel = st.selectbox("Servicio", [s.get("nombre", "") for s in datos["servicios"] if s.get("nombre")])
            
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
                pac = next(p for p in datos["pacientes"] if p.get("nombre") == p_sel)
                ser = next(s for s in datos["servicios"] if s.get("nombre") == s_sel)
                nid_t = obtener_siguiente_id_local(datos["turnos"], "id_turno")
                
                nuevos_turnos = []
                if tipo_agenda == "Turno Único":
                    nuevos_turnos.append([nid_t, str(f_n), h_n, pac.get("id_paciente",""), pac.get("nombre",""), pac.get("tipo_cliente","GENERAL"), ser.get("id_servicio",""), ser.get("nombre",""), "RESERVADO"])
                else:
                    mapa_dias = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                    dias_num = [mapa_dias[d] for d in dias_sel]
                    t_creados, f_actual = 0, f_n
                    while t_creados < cant_turnos:
                        if f_actual.weekday() in dias_num:
                            nuevos_turnos.append([nid_t + t_creados, str(f_actual), h_n, pac.get("id_paciente",""), pac.get("nombre",""), pac.get("tipo_cliente","GENERAL"), ser.get("id_servicio",""), ser.get("nombre",""), "RESERVADO"])
                            t_creados += 1
                        f_actual += timedelta(days=1)
                
                if len(nuevos_turnos) == 1: ws["turnos"].append_row(nuevos_turnos[0])
                else: ws["turnos"].append_rows(nuevos_turnos)
                
                nid_v = obtener_siguiente_id_local(datos["ventas"], "id_venta")
                sesiones = int(ser.get("sesiones", 1))
                ws["ventas"].append_row([nid_v, str(f_n), str(f_n)[:7], pac.get("id_paciente",""), pac.get("nombre",""), ser.get("id_servicio",""), pac.get("tipo_cliente","GENERAL"), limpiar_monto(ser.get("precio_teorico", 0)), "NO", "PENDIENTE", sesiones, 0])
                if sesiones > 1:
                    nid_pl = obtener_siguiente_id_local(datos["planes"], "id_plan_paciente")
                    ws["planes"].append_row([nid_pl, pac.get("id_paciente",""), ser.get("id_servicio",""), sesiones, 0, "ACTIVO", str(f_n), pac.get("nombre","")])
                
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