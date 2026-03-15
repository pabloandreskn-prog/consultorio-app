import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime
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

    turnos_raw = datos["turnos"]
    pagos = datos["pagos"]
    ventas = datos["ventas"]
    servicios = datos["servicios"]
    dict_servicios = {str(s['id_servicio']): s['nombre'] for s in servicios}

    # Ordenar por fecha para detectar la PRIMERA evaluación
    turnos_ordenados = sorted(turnos_raw, key=lambda x: str(x.get('fecha', '')))

    meses = sorted(list({str(v.get("fecha", ""))[:7] for v in ventas if len(str(v.get("fecha", ""))) >= 7}), reverse=True)
    if not meses: return
    mes_sel = st.selectbox("📅 Seleccione mes a analizar", meses)

    # --- MÉTRICAS ---
    ventas_mes = [v for v in ventas if str(v.get("fecha", "")).startswith(mes_sel)]
    facturado_mes = sum(limpiar_monto(v.get("monto_total", 0)) for v in ventas_mes)
    cobrado_mes = sum(limpiar_monto(p.get("monto", 0)) for p in pagos if str(p.get("fecha", "")).startswith(mes_sel))
    
    total_v_h = sum(limpiar_monto(v.get("monto_total", 0)) for v in ventas)
    total_p_h = sum(limpiar_monto(p.get("monto", 0)) for p in pagos)
    deuda_total = max(0, total_v_h - total_p_h)

    # --- LÓGICA QUIRÚRGICA DE LIQUIDACIÓN ---
    cedido_total = 0
    bonif_socios, bonif_gral = 0, 0
    socios_count, gral_count = 0, 0
    filas_detalle = []
    pacientes_con_evaluacion = set()

    for t in turnos_ordenados:
        es_asistio = t.get("estado") == "ASISTIÓ"
        id_paciente = str(t.get("id_paciente"))
        es_eva = "EVALUACION" in str(t.get("nombre_servicio", "")).upper()
        
        # Identificar Primera Evaluación
        es_primera_eval = False
        if es_eva and es_asistio:
            if id_paciente not in pacientes_con_evaluacion:
                es_primera_eval = True
                pacientes_con_evaluacion.add(id_paciente)

        if str(t.get("fecha", "")).startswith(mes_sel) and es_asistio:
            es_socio = "SOCIO" in str(t.get("condicion_turno", "")).upper()
            res = calcular_participacion_dashboard(t, turnos_raw)
            
            monto_bruto_base = res["bruto"]
            
            # APLICACIÓN DE REGLAS DE NEGOCIO
            if es_primera_eval:
                if es_socio:
                    # REGLA 1: SOCIO + 1° EVA = 100% BONIFICADO (Nadie cobra)
                    bruto_final = 0.0
                    monto_bonif = monto_bruto_base
                    monto_espacio = 0.0
                    neto_profesional = 0.0
                    pct_texto = "0%"
                else:
                    # REGLA 2: GENERAL + 1° EVA = 50% BONIFICADO (Se cobra el 50%)
                    bruto_final = monto_bruto_base * 0.5
                    monto_bonif = monto_bruto_base * 0.5
                    monto_espacio = bruto_final * 0.20 # 20% para el gym sobre lo cobrado
                    neto_profesional = bruto_final - monto_espacio
                    pct_texto = "20%"
            else:
                # REGLA 3: CASO NORMAL
                bruto_final = monto_bruto_base
                monto_bonif = res.get("bonificacion", 0)
                pct_val = 0.30 if es_socio else 0.20
                pct_texto = "30%" if es_socio else "20%"
                monto_espacio = bruto_final * pct_val
                neto_profesional = bruto_final - monto_espacio

            cedido_total += monto_espacio
            if es_socio: 
                socios_count += 1
                bonif_socios += monto_bonif
            else: 
                gral_count += 1
                bonif_gral += monto_bonif

            filas_detalle.append({
                "Fecha": t["fecha"], "Paciente": t["nombre_paciente"], "Servicio": t["nombre_servicio"],
                "1° Eval": "SÍ" if es_primera_eval else "NO", "Bruto ($)": bruto_final,
                "Bonificación ($)": monto_bonif, "Porcentaje Espacio": pct_texto,
                "Monto Espacio ($)": monto_espacio, "Neto Profesional ($)": neto_profesional
            })

    # --- INTERFAZ ---
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💼 Facturado", f"${facturado_mes:,.0f}")
    m2.metric("💰 Cobrado", f"${cobrado_mes:,.0f}")
    m3.metric("⚠️ Deuda Global", f"${deuda_total:,.0f}")
    m4.metric("🏢 Cedido Enjoy", f"${cedido_total:,.0f}")

    st.markdown("---")
    h_col, d_col = st.columns([3, 1])
    h_col.subheader("📋 Detalle de Liquidación")
    
    if filas_detalle:
        df_liq = pd.DataFrame(filas_detalle)
        
        # EXCEL BLOQUEADO
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Detalle Cesión')
            worksheet.protect('enjoy2024')
            f_h = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
            f_m = workbook.add_format({'num_format': '$#,##0', 'border': 1})
            f_n = workbook.add_format({'border': 1})

            worksheet.write('A1', 'PARTICIPACIÓN ENJOY', f_h)
            worksheet.write('F1', 'Resumen General', f_h)
            worksheet.write('F2', 'Total Facturado', f_n); worksheet.write('G2', facturado_mes, f_m)
            worksheet.write('F3', 'Total Cedido', f_n); worksheet.write('G3', cedido_total, f_m)
            
            for c, name in enumerate(df_liq.columns): worksheet.write(10, c, name, f_h)
            for r, row in enumerate(df_liq.values):
                for c, val in enumerate(row):
                    worksheet.write(r+11, c, val, f_m if c in [4,5,7,8] else f_n)

        with d_col:
            st.download_button("📥 Descargar XLSX", buffer.getvalue(), f"estudio_cesion_{mes_sel}.xlsx")

        st.dataframe(df_liq.style.format({"Bruto ($)": "${:,.0f}", "Bonificación ($)": "${:,.0f}", "Monto Espacio ($)": "${:,.0f}", "Neto Profesional ($)": "${:,.0f}"}), use_container_width=True)