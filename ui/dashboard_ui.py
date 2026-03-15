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

    turnos_raw = datos["turnos"]
    ventas = datos["ventas"]
    
    # Ordenar cronológicamente para detectar la PRIMERA evaluación del historial
    turnos_ordenados = sorted(turnos_raw, key=lambda x: str(x.get('fecha', '')))
    
    meses = sorted(list({str(v.get("fecha", ""))[:7] for v in ventas if len(str(v.get("fecha", ""))) >= 7}), reverse=True)
    if not meses: return
    mes_sel = st.selectbox("📅 Seleccione mes a analizar", meses)

    # Lógica de procesamiento
    cedido_total = 0
    filas_detalle = []
    pacientes_evaluados = set() # Para rastrear la primera evaluación de por vida

    for t in turnos_ordenados:
        id_pac = str(t.get("id_paciente"))
        es_asistio = t.get("estado") == "ASISTIÓ"
        es_eva = "EVALUACION" in str(t.get("nombre_servicio", "")).upper()
        
        # Identificar si es la primera evaluación del paciente
        es_primera_eval = False
        if es_eva and es_asistio:
            if id_pac not in pacientes_evaluados:
                es_primera_eval = True
                pacientes_evaluados.add(id_pac)

        # Solo procesamos para el reporte del mes seleccionado
        if str(t.get("fecha", "")).startswith(mes_sel) and es_asistio:
            es_socio = "SOCIO" in str(t.get("condicion_turno", "")).upper()
            res_base = calcular_participacion_dashboard(t, turnos_raw)
            monto_base = res_base["bruto"]

            if es_primera_eval:
                if es_socio:
                    # REGLA 1: SOCIO 1° EVA -> 100% BONIFICADO (Nadie cobra)
                    bruto, bonif, espacio, neto = 0.0, monto_base, 0.0, 0.0
                    pct_t = "0%"
                else:
                    # REGLA 2: GENERAL 1° EVA -> 50% BONIFICADO (Se cobra el 50%)
                    bruto = monto_base * 0.5
                    bonif = monto_base * 0.5
                    espacio = bruto * 0.20 # Gym cobra 20% sobre lo que se cobró (la mitad)
                    neto = bruto - espacio
                    pct_t = "20%"
            else:
                # REGLA 3: CASO NORMAL
                bruto = monto_base
                bonif = res_base.get("bonificacion", 0)
                pct_val = 0.30 if es_socio else 0.20
                pct_t = "30%" if es_socio else "20%"
                espacio = bruto * pct_val
                neto = bruto - espacio

            cedido_total += espacio
            filas_detalle.append({
                "Fecha": t["fecha"], "Paciente": t["nombre_paciente"], "Servicio": t["nombre_servicio"],
                "1° Eval": "SÍ" if es_primera_eval else "NO", "Bruto ($)": bruto,
                "Bonificación ($)": bonif, "Porcentaje Espacio": pct_t,
                "Monto Espacio ($)": espacio, "Neto Profesional ($)": neto
            })

    # --- MÉTRICAS ---
    ventas_mes = [v for v in ventas if str(v.get("fecha", "")).startswith(mes_sel)]
    fact_total = sum(limpiar_monto(v.get("monto_total", 0)) for v in ventas_mes)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("💼 Facturado", f"${fact_total:,.0f}")
    m2.metric("🏢 Cedido Enjoy", f"${cedido_total:,.0f}")
    m3.metric("👤 Neto Profesional", f"${fact_total - cedido_total:,.0f}")

    # --- GRÁFICO (Aquí es donde daba error) ---
    st.markdown("### 📈 Facturación Últimos Meses")
    datos_grafico = []
    for m in meses[:3][::-1]:
        f = sum(limpiar_monto(v.get("monto_total", 0)) for v in ventas if str(v.get("fecha", "")).startswith(m))
        datos_grafico.append({"Mes": m, "Total": f})
    
    if datos_grafico:
        fig = px.line(pd.DataFrame(datos_grafico), x="Mes", y="Total", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    # --- EXCEL Y TABLA ---
    if filas_detalle:
        df_liq = pd.DataFrame(filas_detalle)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Detalle')
            worksheet.protect('enjoy2026')
            f_h = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
            f_m = workbook.add_format({'num_format': '$#,##0', 'border': 1})
            f_n = workbook.add_format({'border': 1})

            # Estructura del Excel
            worksheet.write('A1', 'PARTICIPACIÓN ENJOY', f_h)
            worksheet.write('F1', 'Resumen General', f_h)
            worksheet.write('F2', 'Total Facturado', f_n); worksheet.write('G2', fact_total, f_m)
            worksheet.write('F3', 'Total Cedido', f_n); worksheet.write('G3', cedido_total, f_m)

            for c, name in enumerate(df_liq.columns): worksheet.write(10, c, name, f_h)
            for r, row in enumerate(df_liq.values):
                for c, val in enumerate(row):
                    worksheet.write(r+11, c, val, f_m if c in [4,5,7,8] else f_n)

        st.download_button("📥 Descargar Reporte XLSX", buffer.getvalue(), f"reporte_{mes_sel}.xlsx")
        st.dataframe(df_liq.style.format({"Bruto ($)": "${:,.0f}", "Bonificación ($)": "${:,.0f}", "Monto Espacio ($)": "${:,.0f}", "Neto Profesional ($)": "${:,.0f}"}), use_container_width=True)