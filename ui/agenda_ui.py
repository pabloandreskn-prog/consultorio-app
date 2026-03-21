import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import time
from domain.agenda_logic import (
    marcar_turno_asistio, marcar_turno_cancelado,
    actualizar_contador_plan, crear_entrada_plan
)

# --- PROTECCIÓN ANTI-BLOQUEO (CACHE MAESTRO) ---
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

@st.cache_data(ttl=60)
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
                    time.sleep(2)
        return resultados
    except Exception as e:
        st.error(f"Saturación de Google Sheets. Reintentando... {e}")
        return None

def limpiar_monto(valor):
    if valor == "" or valor is None: return 0.0
    if isinstance(valor, str):
        valor = str(valor).replace('$', '').replace('.', '').replace(',', '.')
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

# --- INTERFAZ PRINCIPAL ---
def agenda_ui(sheet, p_old, s_old, pl_old):
    datos = cargar_datos_seguros(sheet)
    ws = obtener_hojas_estaticas(sheet)

    if not datos:
        st.warning("⚠️ Sincronizando con Google...")
        if st.button("🔄 Reintentar"):
            st.cache_data.clear(); st.rerun()
        st.stop()

    tab_ag, tab_lib, tab_tur, tab_pac = st.tabs(["📅 Agenda Diaria", "🔍 Buscador Libres", "➕ Agendar Turno/Venta", "👤 Ficha Paciente"])

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
                    
                    restantes = tot - us
                    color_barra = "#d32f2f" if restantes <= 1 and tot > 0 else "#4caf50"
                    porcentaje = (us / tot * 100) if tot > 0 else 0
                    color_borde = "#d32f2f" if deuda > 0 else ("#ffc107" if t["estado"] == "RESERVADO" else "#4caf50")
                    
                    with st.container(border=True):
                        st.markdown(f"""
                            <div style='display:flex; justify-content:space-between; align-items:center;'>
                                <b style='font-size:1.1em;'>{t['hora']} hs</b>
                                <div style='width:60%; background:#e0e0e0; border-radius:10px; height:8px;'>
                                    <div style='width:{porcentaje}%; background:{color_barra}; border-radius:10px; height:8px;'></div>
                                </div>
                            </div>
                            <div style='border-left:5px solid {color_borde}; padding-left:10px; background-color:{color_borde}10; margin:10px 0;'>
                                <div style='font-weight:bold; color:#333;'>{t['nombre_paciente']}</div>
                                <div style='font-size:0.85em; color:#666;'>{t['nombre_servicio']}</div>
                                <div style='text-align:right; font-size:0.8em; color:#444;'>Sesiones: {us}/{tot}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if deuda > 0:
                            st.markdown(f"<p style='color:#d32f2f; font-weight:bold; font-size:0.85em; margin:0;'>⚠️ DEUDA: ${deuda:,.0f}</p>", unsafe_allow_html=True)

                        if t["estado"] == "RESERVADO":
                            cb1, cb2 = st.columns(2)
                            if cb1.button("✅ Asistió", key=f"as_{t['id_turno']}_{fila}", use_container_width=True):
                                ws["turnos"].update_cell(fila, 9, "ASISTIÓ")
                                actualizar_contador_plan(sheet, t["id_paciente"], t["id_servicio"])
                                st.cache_data.clear(); st.rerun()
                            if cb2.button("🚫 Faltó", key=f"fa_{t['id_turno']}_{fila}", use_container_width=True):
                                ws["turnos"].update_cell(fila, 9, "AUSENTE")
                                st.cache_data.clear(); st.rerun()
                        else:
                            st.info(f"Estado: {t['estado']}")

                        with st.expander("⚙️ Gestión / Cobrar / Renovar"):
                            st.markdown("**💰 Registrar Pago**")
                            with st.form(f"f_pag_{t['id_turno']}"):
                                m_c = st.number_input("Monto", value=0.0, key=f"mc_{t['id_turno']}")
                                f_p = st.selectbox("Método", ["EFECTIVO", "TRANSFERENCIA", "MP"], key=f"fp_{t['id_turno']}")
                                if st.form_submit_button("Confirmar Pago", use_container_width=True):
                                    fh = datetime.now().strftime("%Y-%m-%d")
                                    nid_p = obtener_siguiente_id_local(datos["pagos"], "id_pago")
                                    ws["pagos"].append_row([nid_p, fh, fh[:7], t["nombre_paciente"], m_c, f_p, "Agenda", t["id_paciente"], t["id_servicio"]])
                                    st.success("✅ Pago registrado con éxito en Google Sheets")
                                    time.sleep(1); st.cache_data.clear(); st.rerun()

                            st.divider()
                            # REPROGRAMAR
                            lista_h = generar_horarios()
                            idx_h = lista_h.index(t['hora']) if t['hora'] in lista_h else 0
                            f_rep = st.date_input("Nueva Fecha", value=pd.to_datetime(t['fecha']).date(), key=f"fr_{t['id_turno']}")
                            h_rep = st.selectbox("Nueva Hora", lista_h, index=idx_h, key=f"hr_{t['id_turno']}")
                            if st.button("Guardar Reprogramación", key=f"br_{t['id_turno']}", use_container_width=True):
                                ws["turnos"].update_cell(fila, 2, str(f_rep))
                                ws["turnos"].update_cell(fila, 3, h_rep)
                                st.cache_data.clear(); st.rerun()

                            st.divider()
                            # RENOVAR
                            if st.button("🔄 Renovar Venta/Plan", key=f"ren_{t['id_turno']}", use_container_width=True):
                                ser = next(s for s in datos["servicios"] if s["nombre"] == t["nombre_servicio"])
                                pac = next(p for p in datos["pacientes"] if str(p["id_paciente"]) == str(t["id_paciente"]))
                                fh = datetime.now().strftime("%Y-%m-%d")
                                nid_v = obtener_siguiente_id_local(datos["ventas"], "id_venta")
                                ws["ventas"].append_row([nid_v, fh, fh[:7], pac["id_paciente"], pac["nombre"], ser["id_servicio"], pac.get("condicion_turno","GENERAL"), limpiar_monto(ser.get("precio_teorico", 0)), "NO", "PENDIENTE", int(ser.get("sesiones", 1)), 0])
                                if int(ser.get("sesiones", 1)) > 1:
                                    nid_pl = obtener_siguiente_id_local(datos["planes"], "id_plan_paciente")
                                    ws["planes"].append_row([nid_pl, pac["id_paciente"], ser["id_servicio"], int(ser.get("sesiones", 1)), 0, "ACTIVO", fh])
                                st.cache_data.clear(); st.rerun()

    with tab_lib:
        st.subheader("Horarios libres")
        hoy = date.today()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        cols_dias = st.columns(5)
        for i_d, d in enumerate([inicio_semana + timedelta(days=i) for i in range(5)]):
            with cols_dias[i_d]:
                st.markdown(f"**{['Lun','Mar','Mié','Jue','Vie'][i_d]} {d.day}/{d.month}**")
                ocup = [turn["hora"] for turn in datos["turnos"] if str(turn["fecha"]) == str(d) and turn["estado"] != "CANCELADO"]
                for h in generar_horarios():
                    if h in ocup: st.button(f"🔴 {h}", key=f"l_{d}_{h}", disabled=True, use_container_width=True)
                    else:
                        if st.button(f"🟢 {h}", key=f"l_{d}_{h}", use_container_width=True):
                            st.session_state.temp_fecha, st.session_state.temp_hora = d, h
                            st.toast(f"Seleccionado: {d} {h}")

    with tab_tur:
        st.subheader("➕ Agendar Turno/Venta")
        with st.form("f_nuevo"):
            p_sel = st.selectbox("Paciente", [p["nombre"] for p in datos["pacientes"]])
            s_sel = st.selectbox("Servicio", [s["nombre"] for s in datos["servicios"]])
            f_n = st.date_input("Fecha", value=st.session_state.get('temp_fecha', date.today()))
            h_n = st.selectbox("Hora", generar_horarios(), index=generar_horarios().index(st.session_state.get('temp_hora', '08:00')) if st.session_state.get('temp_hora') in generar_horarios() else 0)
            
            if st.form_submit_button("Confirmar Todo", use_container_width=True):
                pac = next(p for p in datos["pacientes"] if p["nombre"] == p_sel)
                ser = next(s for s in datos["servicios"] if s["nombre"] == s_sel)
                fh = datetime.now().strftime("%Y-%m-%d")
                nid_t = obtener_siguiente_id_local(datos["turnos"], "id_turno")
                nid_v = obtener_siguiente_id_local(datos["ventas"], "id_venta")
                
                # Guardar Turno y Venta
                ws["turnos"].append_row([nid_t, str(f_n), h_n, pac["id_paciente"], pac["nombre"], pac.get("tipo_cliente","GENERAL"), ser["id_servicio"], ser["nombre"], "RESERVADO"])
                ws["ventas"].append_row([nid_v, fh, fh[:7], pac["id_paciente"], pac["nombre"], ser["id_servicio"], pac.get("tipo_cliente","GENERAL"), limpiar_monto(ser.get("precio_teorico", 0)), "NO", "EFECTIVO", int(ser.get("sesiones", 1)), 0])
                
                if int(ser.get("sesiones", 1)) > 1:
                    nid_pl = obtener_siguiente_id_local(datos["planes"], "id_plan_paciente")
                    ws["planes"].append_row([nid_pl, pac["id_paciente"], ser["id_servicio"], int(ser.get("sesiones", 1)), 0, "ACTIVO", fh])
                
                st.success(f"Turno y Venta registrados para {pac['nombre']}")
                time.sleep(1); st.cache_data.clear(); st.rerun()

    with tab_pac:
        st.subheader("👤 Nuevo Paciente")
        with st.form("f_paciente"):
            n_n = st.text_input("Nombre y Apellido")
            d_n = st.text_input("DNI")
            t_n = st.text_input("Teléfono (Ej: 5492920...)")
            tipo = st.selectbox("Tipo de Cliente", ["GENERAL", "SOCIO_GIM", "PUBLICO"])
            obs = st.text_area("Observaciones/Patología")
            
            if st.form_submit_button("Guardar Paciente"):
                if n_n:
                    nid_p = obtener_siguiente_id_local(datos["pacientes"], "id_paciente")
                    fecha_h = datetime.now().strftime("%Y-%m-%d")
                    # ORDEN EXACTO: id, nombre, dni, telefono, tipo, fecha, activo, observaciones
                    ws["pacientes"].append_row([nid_p, n_n, d_n, t_n, tipo, fecha_h, "TRUE", obs])
                    st.success(f"Paciente {n_n} registrado correctamente")
                    time.sleep(1); st.cache_data.clear(); st.rerun()