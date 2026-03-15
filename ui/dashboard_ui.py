import streamlit as st
import pandas as pd
import plotly.express as px
import io
from data.sheets_client import get_sheet
from ui.styles import aplicar_estilos_globales
from domain.finanzas import calcular_participacion_dashboard

def limpiar_monto(valor):
    if valor == "" or valor is None: return 0.0
    try:
        if isinstance(valor, str):
            v = valor.replace('$', '').replace('.', '').replace(',', '.').strip()
            return float(v)
        return float(valor)
    except: return 0.0

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

def dashboard_ui():
    aplicar_estilos_globales()
    st.markdown("## 📊 Dashboard de Inteligencia Financiera")

    datos = cargar_datos_dashboard()
    if not datos: return

    turnos, pagos, ventas, servicios = datos["turnos"], datos["pagos"], datos["ventas"], datos["servicios"]
    dict_servicios = {str(s['id_servicio']): s['nombre'] for s in servicios}

    meses = sorted(list({str(v.get("fecha", ""))[:7] for v in ventas if len(str(v.get("fecha", ""))) >= 7}), reverse=True)
    if not meses: return
    mes_sel = st.selectbox("📅 Seleccione mes a analizar", meses)

    # --- CÁLCULOS ---
    ventas_mes = [v for v in ventas if str(v.get("fecha", "")).startswith(mes_sel)]
    facturado_mes = sum(limpiar_monto(v.get("monto_total", 0)) for v in ventas_mes)
    cobrado_mes = sum(limpiar_monto(p.get("monto", 0)) for p in pagos if str(p.get("fecha", "")).startswith(mes_sel))
    
    total_v_hist = sum(limpiar_monto(v.get("monto_total", 0)) for v in ventas)
    total_p_hist = sum(limpiar_monto(p.get("monto", 0)) for p in pagos)
    deuda_total = max(0, total_v_hist - total_p_hist)

    # --- MÉTRICAS SUPERIORES ---
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💼 Facturado", f"${facturado_mes:,.0f}")
    m2.metric("💰 Cobrado", f"${cobrado_mes:,.0f}")
    m3.metric("⚠️ Deuda Global", f"${deuda_total:,.0f}", delta_color="inverse")
    
    cedido_total = 0
    bonif_socios, bonif_gral = 0, 0
    socios_count, gral_count = 0, 0
    filas_detalle = []

    for t in turnos:
        if str(t.get("fecha", "")).startswith(mes_sel) and t.get("estado") == "ASISTIÓ":
            v_data = next((v for v in ventas if str(v.get('id_paciente')) == str(t.get('id_paciente')) 
                           and str(v.get('id_servicio')) == str(t.get('id_servicio'))), {})
            
            es_bonif = str(v_data.get("bonificado (Si/No)", "")).upper() == "SI"
            es_eva = "EVALUACION" in str(t.get("nombre_servicio", "")).upper()
            es_socio = "SOCIO" in str(t.get("condicion_turno", "")).upper()
            pct_texto = "30%" if es_socio else "20%"

            res = calcular_participacion_dashboard(t, turnos)
            cedido_total += res["participacion"]

            if es_socio: socios_count += 1
            else: gral_count += 1

            if es_bonif:
                m_bonif = res.get("bonificacion", 0)
                if es_socio: bonif_socios += m_bonif
                else: bonif_gral += m_bonif

            filas_detalle.append({
                "Fecha": t["fecha"], "Paciente": t["nombre_paciente"], "Servicio": t["nombre_servicio"],
                "1° Eval": "SÍ" if es_eva else "NO", "Bruto ($)": res["bruto"],
                "Bonificación ($)": res.get("bonificacion", 0), "Porcentaje Espacio": pct_texto,
                "Monto Espacio ($)": res["participacion"], "Neto Profesional ($)": res["neto"]
            })

    m4.metric("🏢 Cedido Enjoy", f"${cedido_total:,.0f}")

    # --- PARTICIPACIÓN ENJOY (VISTA) ---
    st.markdown("### 🏢 PARTICIPACIÓN ENJOY")
    c_s1, c_s2, c_s3 = st.columns(3)
    c_s1.write(f"**Total Facturado:** ${facturado_mes:,.0f}")
    with c_s2:
        st.write(f"🏋️ Socios Gym: {socios_count}")
        st.write(f"👥 General: {gral_count}")
    with c_s3:
        st.write(f"🏋️ Bonif. Socios: ${bonif_socios:,.0f}")
        st.write(f"👥 Bonif. General: ${bonif_gral:,.0f}")

    # --- DETALLE Y DESCARGA TAL CUAL XLSX ---
    st.markdown("---")
    h_col, d_col = st.columns([3, 1])
    h_col.subheader("📋 Detalle de Liquidación por Sesión")
    
    if filas_detalle:
        df_liq = pd.DataFrame(filas_detalle)
        
        # CONSTRUCCIÓN DEL REPORTE IGUAL AL XLSX
        output = io.StringIO()
        output.write(f"PARTICIPACIÓN ENJOY,,,,,Resumen General\n")
        output.write(f"Mes: {mes_sel},,,,,Total Facturado,{facturado_mes}\n")
        output.write(f"Estado: CERRADO,,,,,Total Cedido,{cedido_total}\n")
        output.write(f",,,,,Neto Profesional,{facturado_mes - cedido_total}\n\n")
        output.write(f"Sesiones Socios Gym,{socios_count}\n")
        output.write(f"Sesiones General,{gral_count}\n")
        output.write(f"Bonificado Socios Gym,{bonif_socios}\n")
        output.write(f"Bonificado General,{bonif_gral}\n\n")
        
        # Agregamos la tabla de detalle
        df_liq.to_csv(output, index=False)
        
        with d_col:
            st.download_button(
                label="📥 Descargar Reporte Completo",
                data=output.getvalue(),
                file_name=f"estudio_cesion_{mes_sel}.csv",
                mime="text/csv"
            )

        st.dataframe(df_liq.style.format({
            "Bruto ($)": "${:,.0f}", "Bonificación ($)": "${:,.0f}",
            "Monto Espacio ($)": "${:,.0f}", "Neto Profesional ($)": "${:,.0f}"
        }), use_container_width=True)