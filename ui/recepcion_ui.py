import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from datetime import datetime
from data.sheets_client import get_sheet
from ui.styles import aplicar_estilos_globales
from domain.finanzas import calcular_participacion_dashboard

# --- UTILIDADES DE LIMPIEZA Y BUSQUEDA (Ajuste para fila 1000) ---
def limpiar_monto(valor):
    if valor == "" or valor is None or str(valor).lower() == 'no': return 0.0
    try:
        if isinstance(valor, str):
            v = str(valor).replace('$', '').replace('.', '').replace(',', '.').strip()
            return float(v)
        return float(valor)
    except: return 0.0

def encontrar_proxima_fila_libre(worksheet):
    col_id = worksheet.col_values(1) 
    return len(col_id) + 1

def registrar_cobro_recepcion(datos_cobro):
    try:
        doc = get_sheet("Consultorio")
        hoja_v = doc.worksheet("ventas")
        hoja_p = doc.worksheet("pagos")
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        mes_hoy = datetime.now().strftime("%Y-%m")
        
        id_v = encontrar_proxima_fila_libre(hoja_v)
        fila_v = [id_v, fecha_hoy, mes_hoy, datos_cobro['id_paciente'], 
                  datos_cobro['id_servicio'], datos_cobro['monto'], 0, 
                  datos_cobro['metodo'], 1, 1, "PAGADO"]
        hoja_v.insert_row(fila_v, id_v)
        
        id_p = encontrar_proxima_fila_libre(hoja_p)
        fila_p = [id_p, fecha_hoy, mes_hoy, datos_cobro['id_paciente'], 
                  datos_cobro['nombre_paciente'], datos_cobro['monto'], 
                  datos_cobro['metodo'], "Cobro individual - Recepción"]
        hoja_p.insert_row(fila_p, id_p)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error en registro: {e}")
        return False

# --- UI DE RECEPCIÓN (Tus 4 pestañas originales) ---
def recepcion_ui():
    aplicar_estilos_globales()
    st.title("🏨 Gestión de Recepción")
    
    # Importación corregida para que coincida con tu archivo agenda_ui.py
    from ui.agenda_ui import agenda_ui 

    tab_agenda, tab_libres, tab_turno, tab_paciente = st.tabs([
        "📅 Agenda", "🔍 Libres", "➕ Turno", "👤 Paciente"
    ])

    sheet = get_sheet("Consultorio")
    pacientes = sheet.worksheet("pacientes").get_all_records()
    servicios = sheet.worksheet("servicios").get_all_records()
    planes = sheet.worksheet("planes_pacientes").get_all_records()

    with tab_agenda:
        agenda_ui(sheet, pacientes, servicios, planes)
    with tab_libres:
        st.info("🔍 Buscador de horarios libres")
    with tab_turno:
        st.info("➕ Formulario de nuevo turno")
    with tab_paciente:
        st.info("👤 Gestión de pacientes")

# --- DASHBOARD (Tu lógica de Excel y participación original) ---
def dashboard_ui():
    aplicar_estilos_globales()
    st.markdown("## 📊 Dashboard de Inteligencia Financiera")
    datos = cargar_datos_dashboard()
    if not datos: return

    pagos_raw = datos["pagos"]
    ventas_raw = datos["ventas"]
    turnos_raw = datos["turnos"]
    servicios_raw = datos["servicios"]

    precios_lista = {str(s['nombre']).upper().strip(): limpiar_monto(s['precio']) for s in servicios_raw}
    
    lista_meses = sorted(list(set(str(p.get("fecha", ""))[:7] for p in pagos_raw if len(str(p.get("fecha", ""))) >= 7)), reverse=True)
    if not lista_meses:
        st.warning("⚠️ No se detectaron fechas válidas.")
        return
    mes_sel = st.selectbox("📅 Seleccione mes a analizar", lista_meses)

    facturado_real = sum(limpiar_monto(p.get("monto", 0)) for p in pagos_raw if str(p.get("fecha", "")).startswith(mes_sel))
    
    cedido_total = 0
    volumen_cobrado_asistencias = 0 
    filas_detalle = []
    pacientes_evaluados = set()

    for t in sorted(turnos_raw, key=lambda x: str(x.get('fecha', ''))):
        f_turno = str(t.get("fecha", ""))
        if f_turno.startswith(mes_sel) and t.get("estado") == "ASISTIÓ":
            id_pac = str(t.get("id_paciente"))
            nombre_ser = str(t.get("nombre_servicio", "Sin Especificar")).strip()
            cond = str(t.get("condicion_turno", t.get("condicion_turnos", ""))).upper()
            es_socio = "SOCIO" in cond
            
            precio_oficial = precios_lista.get(nombre_ser.upper(), limpiar_monto(t.get("precio_teorico", 0)))
            res_base = calcular_participacion_dashboard(t, turnos_raw)
            
            es_eva = "EVALUACION" in nombre_ser.upper()
            es_primera_eval = False
            if es_eva and id_pac not in pacientes_evaluados:
                es_primera_eval = True
                pacientes_evaluados.add(id_pac)

            if es_primera_eval:
                if es_socio:
                    bruto_final, bonif_final = 0.0, precio_oficial
                    pct_t, pct_val = "0%", 0.0
                else:
                    bruto_final, bonif_final = precio_oficial * 0.5, precio_oficial * 0.5
                    pct_t, pct_val = "20%", 0.20
            else:
                bruto_final = res_base["bruto"]
                bonif_final = res_base.get("bonificacion", 0)
                pct_val = 0.30 if es_socio else 0.20
                pct_t = "30%" if es_socio else "20%"

            volumen_cobrado_asistencias += bruto_final
            espacio = bruto_final * pct_val
            neto_prof = bruto_final - espacio
            cedido_total += espacio

            filas_detalle.append({
                "Fecha": f_turno, "Paciente": t.get("nombre_paciente"),
                "Servicio": nombre_ser, "1° Eval": "SÍ" if es_primera_eval else "NO",
                "Bruto ($)": bruto_final, "Bonificación ($)": bonif_final,
                "Porcentaje Espacio": pct_t, "Monto Espacio ($)": espacio,
                "Neto Profesional ($)": neto_prof
            })

    # Lógica de Deuda
    balance_pacientes = {}
    for v in ventas_raw:
        id_p = str(v.get("id_paciente"))
        if id_p: balance_pacientes[id_p] = balance_pacientes.get(id_p, 0) + limpiar_monto(v.get("monto_total", 0))
    for p in pagos_raw:
        id_p = str(p.get("id_paciente"))
        if id_p: balance_pacientes[id_p] = balance_pacientes.get(id_p, 0) - limpiar_monto(p.get("monto", 0))
    deuda_total = sum(bal for bal in balance_pacientes.values() if bal > 0)

    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💼 Facturado", f"${facturado_real:,.0f}")
    m2.metric("🎯 Cobrado", f"${volumen_cobrado_asistencias:,.0f}")
    m3.metric("⚠️ Deuda General", f"${deuda_total:,.0f}")
    m4.metric("🏢 Cedido Enjoy", f"${cedido_total:,.0f}")

    st.markdown("---")
    if filas_detalle:
        df_liq = pd.DataFrame(filas_detalle)
        
        # Generador Excel original
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Detalle')
            f_h = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
            f_m = workbook.add_format({'num_format': '$#,##0', 'border': 1})
            f_n = workbook.add_format({'border': 1})
            for c, name in enumerate(df_liq.columns): worksheet.write(0, c, name, f_h)
            for r, row in enumerate(df_liq.values):
                for c, val in enumerate(row):
                    worksheet.write(r+1, c, val, f_m if c in [4,5,7,8] else f_n)

        st.download_button("📥 Descargar Reporte XLSX", buffer.getvalue(), f"reporte_{mes_sel}.xlsx")
        st.dataframe(df_liq.style.format({
            "Bruto ($)": "${:,.0f}", "Bonificación ($)": "${:,.0f}", 
            "Monto Espacio ($)": "${:,.0f}", "Neto Profesional ($)": "${:,.0f}"
        }), use_container_width=True)

@st.cache_data(ttl=60)
def cargar_datos_dashboard():
    try:
        sheet = get_sheet("Consultorio")
        return {
            "turnos": sheet.worksheet("turnos").get_all_records(),
            "pagos": sheet.worksheet("pagos").get_all_records(),
            "ventas": sheet.worksheet("ventas").get_all_records(),
            "servicios": sheet.worksheet("servicios").get_all_records()
        }
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None