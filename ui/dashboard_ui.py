import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from datetime import datetime
from data.sheets_client import get_sheet
from ui.styles import aplicar_estilos_globales
from domain.finanzas import calcular_participacion_dashboard

# --- UTILIDADES DE LIMPIEZA Y BUSQUEDA ---
def limpiar_monto(valor):
    if valor == "" or valor is None or str(valor).lower() == 'no': return 0.0
    try:
        if isinstance(valor, str):
            v = str(valor).replace('$', '').replace('.', '').replace(',', '.').strip()
            return float(v)
        return float(valor)
    except: return 0.0

def encontrar_proxima_fila_libre(worksheet):
    """Evita el error de la fila 1000 buscando el final real de los datos."""
    col_id = worksheet.col_values(1) # Lee la columna A
    return len(col_id) + 1

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

# --- LÓGICA DE REGISTRO SEGURO (RECEPCIÓN) ---
def registrar_cobro_completo(datos_cobro):
    """
    Registra simultáneamente en Ventas y Pagos en la primera fila libre.
    datos_cobro: dict con id_paciente, nombre, monto, id_servicio, etc.
    """
    try:
        doc = get_sheet("Consultorio")
        hoja_ventas = doc.worksheet("ventas")
        hoja_pagos = doc.worksheet("pagos")
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        mes_hoy = datetime.now().strftime("%Y-%m")
        
        # 1. Preparar fila para VENTAS
        # Estructura: id_venta, fecha, mes, id_paciente, id_servicio, monto_total, sesiones...
        id_v = encontrar_proxima_fila_libre(hoja_ventas)
        fila_v = [id_v, fecha_hoy, mes_hoy, datos_cobro['id_paciente'], 
                  datos_cobro['id_servicio'], datos_cobro['monto'], 0, "Efectivo", 1, 1, "PAGADO"]
        hoja_ventas.insert_row(fila_v, id_v)
        
        # 2. Preparar fila para PAGOS (con tu nueva columna 'nombre')
        # Estructura: id_pago, fecha, mes, id_paciente, nombre, monto, metodo, observacion...
        id_p = encontrar_proxima_fila_libre(hoja_pagos)
        fila_p = [id_p, fecha_hoy, mes_hoy, datos_cobro['id_paciente'], 
                  datos_cobro['nombre'], datos_cobro['monto'], datos_cobro['metodo'], "Pago desde Recepción"]
        hoja_pagos.insert_row(fila_p, id_p)
        
        return True
    except Exception as e:
        st.error(f"Error al registrar: {e}")
        return False

# --- UI DEL DASHBOARD ---
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

    lista_meses = set()
    for p in pagos_raw:
        f = str(p.get("fecha", ""))
        if len(f) >= 7: lista_meses.add(f[:7])
    
    meses_ordenados = sorted(list(lista_meses), reverse=True)
    if not meses_ordenados:
        st.warning("⚠️ No se detectaron fechas válidas.")
        return
        
    mes_sel = st.selectbox("📅 Seleccione mes a analizar", meses_ordenados)

    # --- CÁLCULOS DEL MES ---
    facturado_real = sum(limpiar_monto(p.get("monto", 0)) for p in pagos_raw 
                        if str(p.get("fecha", "")).startswith(mes_sel))

    cedido_total = 0
    conteo_socios, conteo_general = 0, 0
    bonif_socios, bonif_general = 0, 0
    volumen_cobrado_asistencias = 0 
    filas_detalle = []
    pacientes_evaluados = set()

    turnos_ordenados = sorted(turnos_raw, key=lambda x: str(x.get('fecha', '')))

    for t in turnos_ordenados:
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

            # Lógica quirúrgica de bonificación (Caso Linares Ana y General 50%)
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

            if es_socio:
                conteo_socios += 1
                bonif_socios += bonif_final
            else:
                conteo_general += 1
                bonif_general += bonif_final

            filas_detalle.append({
                "Fecha": f_turno,
                "Paciente": t.get("nombre_paciente"),
                "Servicio": nombre_ser,
                "1° Eval": "SÍ" if es_primera_eval else "NO",
                "Bruto ($)": bruto_final,
                "Bonificación ($)": bonif_final,
                "Porcentaje Espacio": pct_t,
                "Monto Espacio ($)": espacio,
                "Neto Profesional ($)": neto_prof
            })

    # --- DEUDA GENERALIZADA (HISTÓRICA) ---
    balance_pacientes = {}
    for v in ventas_raw:
        id_p = str(v.get("id_paciente"))
        if id_p: balance_pacientes[id_p] = balance_pacientes.get(id_p, 0) + limpiar_monto(v.get("monto_total", 0))
    for p in pagos_raw:
        id_p = str(p.get("id_paciente"))
        if id_p: balance_pacientes[id_p] = balance_pacientes.get(id_p, 0) - limpiar_monto(p.get("monto", 0))

    deuda_total = sum(bal for bal in balance_pacientes.values() if bal > 0)

    # --- UI MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💼 Facturado", f"${facturado_real:,.0f}")
    m2.metric("🎯 Sesiones", f"${volumen_cobrado_asistencias:,.0f}")
    m3.metric("⚠️ Deuda General", f"${deuda_total:,.0f}")
    m4.metric("🏢 Cedido Enjoy", f"${cedido_total:,.0f}")

    st.markdown("---")
    st.markdown("### 🏢 PARTICIPACIÓN ENJOY")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**Total Pagado (Mes)**"); st.subheader(f"${facturado_real:,.0f}")
    with c2:
        st.write("**Sesiones atendidas**")
        st.write(f"🏋️ Socios Gym: {conteo_socios}"); st.write(f"👤 General: {conteo_general}")
    with c3:
        st.write("**Total bonificado**")
        st.write(f"🎁 Socios: ${bonif_socios:,.0f}"); st.write(f"📉 General: ${bonif_general:,.0f}")

    # --- TABLA Y EXCEL ---
    if filas_detalle:
        st.markdown("---")
        df_liq = pd.DataFrame(filas_detalle)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Detalle')
            worksheet.protect('enjoy2026')
            f_h = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})
            f_m = workbook.add_format({'num_format': '$#,##0', 'border': 1})
            f_n = workbook.add_format({'border': 1})
            worksheet.write('A1', 'REPORTES ENJOY - ' + mes_sel, f_h)
            for c, name in enumerate(df_liq.columns): worksheet.write(10, c, name, f_h)
            for r, row in enumerate(df_liq.values):
                for c, val in enumerate(row):
                    worksheet.write(r+11, c, val, f_m if c in [4,5,7,8] else f_n)

        st.download_button("📥 Descargar Reporte XLSX", buffer.getvalue(), f"reporte_{mes_sel}.xlsx")
        st.markdown("### 📑 Detalle de Sesiones")
        st.dataframe(df_liq.style.format({
            "Bruto ($)": "${:,.0f}", "Bonificación ($)": "${:,.0f}", 
            "Monto Espacio ($)": "${:,.0f}", "Neto Profesional ($)": "${:,.0f}"
        }), use_container_width=True)