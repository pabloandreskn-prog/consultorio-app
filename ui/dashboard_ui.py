import streamlit as st
import pandas as pd
from datetime import date

from ui.styles import aplicar_estilos_globales

from data.sheets_client import get_sheet
from domain.finanzas import (
    mes_cerrado,
    calcular_cierre_mes,
    calcular_participacion_turno,
    ya_tuvo_evaluacion
)
from domain.pdf_reportes import generar_pdf_liquidacion
from domain.insights_financieros import (
    evaluar_salud_mes,
    detectar_riesgos,
    generar_alertas_accionables
)

# =========================
# COMPONENTES VISUALES
# =========================
def tarjeta_salud_financiera(mensaje, nivel):
    clase = "health"
    if nivel == "rojo":
        clase += " red"
    elif nivel == "amarillo":
        clase += " yellow"

    st.markdown(f"""
    <div class="card {clase}">
        <div class="health-title">Estado financiero del mes</div>
        <div class="health-text">{mensaje}</div>
    </div>
    """, unsafe_allow_html=True)

def tarjeta_insight(titulo, contenido, nivel="info"):
    clase = "alert"
    if nivel == "rojo":
        clase += " red"
    elif nivel == "amarillo":
        clase += " yellow"

    st.markdown(f"""
    <div class="{clase}">
        <div class="alert-title">{titulo}</div>
        <div class="alert-action">{contenido}</div>
    </div>
    """, unsafe_allow_html=True)

def metric_card(titulo, valor):
    st.markdown(f"""
    <div class="card metric">
        <div class="metric-title">{titulo}</div>
        <div class="metric-value">${valor}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# CARGA DE DATOS
# =========================
@st.cache_data(ttl=300)
def cargar_datos():
    sheet = get_sheet("Consultorio")
    return {
        "turnos": sheet.worksheet("turnos").get_all_records(),
        "pagos": sheet.worksheet("pagos").get_all_records(),
        "pacientes": sheet.worksheet("pacientes").get_all_records(),
        "cierres": sheet.worksheet("cierres").get_all_records(),
    }

# =========================
# DASHBOARD
# =========================
def dashboard_ui():
    aplicar_estilos_globales()

    st.markdown("## 📊 Dashboard financiero del consultorio")
    st.caption("Los datos se cargan al cierre del día. Indicadores no críticos en tiempo real.")

    datos = cargar_datos()
    sheet = get_sheet("Consultorio")

    turnos = datos["turnos"]
    pagos = datos["pagos"]
    pacientes = datos["pacientes"]
    cierres = datos["cierres"]

    if not turnos:
        st.info("No hay datos aún")
        return

    meses = sorted({t["fecha"][:7] for t in turnos if t.get("fecha")})
    mes = st.selectbox("Mes", meses)

    cerrado = mes_cerrado(sheet.worksheet("cierres"), mes)

    if cerrado:
        cierre = next(c for c in cierres if c["mes"] == mes)
        total_facturado = cierre["total_facturado"]
        total_cobrado = cierre["total_cobrado"]
        diferencia = cierre["diferencia"]
        st.success(f"🔒 Mes {mes} cerrado")
    else:
        cierre_preview = calcular_cierre_mes(turnos, pagos, mes)
        total_facturado = cierre_preview["total_facturado"]
        total_cobrado = cierre_preview["total_cobrado"]
        diferencia = cierre_preview["diferencia"]

    # =========================
    # MÉTRICAS
    # =========================
    c1, c2, c3 = st.columns(3)
    with c1: metric_card("Facturado", total_facturado)
    with c2: metric_card("Cobrado", total_cobrado)
    with c3: metric_card("Diferencia", diferencia)

    st.divider()
    st.subheader("🧠 Insights financieros")

    salud = evaluar_salud_mes(total_facturado, total_cobrado)
    tarjeta_salud_financiera(salud["mensaje"], salud["nivel"])

    riesgos = detectar_riesgos(total_facturado, total_cobrado, diferencia)
    for r in riesgos:
        tarjeta_insight("Riesgo detectado", r, "rojo")

    alertas = generar_alertas_accionables(salud, riesgos)
    st.subheader("🚨 Alertas y acciones sugeridas")
    for a in alertas:
        tarjeta_insight(a["mensaje"], a["accion"], a["nivel"])

    st.divider()
    st.subheader("📋 Detalle por turno")

    pacientes_por_id = {p["id_paciente"]: p for p in pacientes}
    filas_detalle = []

    for t in turnos:
        if t.get("fecha", "").startswith(mes) and t.get("estado") == "ASISTIÓ":
            paciente = pacientes_por_id.get(t["id_paciente"])
            if not paciente:
                continue

            es_primera = not ya_tuvo_evaluacion(turnos, t["id_paciente"], t["id_servicio"])
            calc = calcular_participacion_turno(t, paciente, es_primera)

            filas_detalle.append({
                "fecha": t["fecha"],
                "paciente": t["nombre_paciente"],
                "servicio": t["nombre_servicio"],
                "precio": calc["precio"],
                "neto": calc["neto_profesional"],
                "espacio": calc["participacion_monto"]
            })

    if filas_detalle:
        st.dataframe(
            pd.DataFrame(filas_detalle),
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    if st.button("📄 Generar PDF de liquidación"):
        generar_pdf_liquidacion(
            archivo=f"liquidacion_{mes}.pdf",
            mes=mes,
            resumen={
                "total_facturado": total_facturado,
                "total_espacio": sum(f["espacio"] for f in filas_detalle),
                "neto_profesional": sum(f["neto"] for f in filas_detalle),
            },
            detalle_turnos=filas_detalle,
            definitivo=cerrado,
            salud=salud,
            riesgos=riesgos
        )
        st.success(f"PDF generado: liquidacion_{mes}.pdf")
