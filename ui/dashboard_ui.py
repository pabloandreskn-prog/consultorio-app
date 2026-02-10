import streamlit as st
import pandas as pd
from io import BytesIO

from data.sheets_client import get_sheet
from ui.styles import aplicar_estilos_globales

from domain.finanzas import (
    mes_esta_cerrado,
    calcular_cierre_mes,
    calcular_participacion_turno, calcular_precio_teorico, es_primera_evaluacion
)

from domain.pdf_reportes import generar_pdf_liquidacion
from domain.insights_financieros import (
    evaluar_salud_mes,
    detectar_riesgos,
    generar_alertas_accionables
)

# =========================
# CARGA DE DATOS
# =========================
@st.cache_data(ttl=300)
def cargar_datos():
    sheet = get_sheet("Consultorio")
    return {
        "turnos": sheet.worksheet("turnos").get_all_records(),
        "pagos": sheet.worksheet("pagos").get_all_records(),
        "cierres": sheet.worksheet("cierres").get_all_records(),
    }

# =========================
# EXPORTADOR EXCEL
# =========================
def generar_excel_cesion(mes, filas, resumen, cerrado, sesiones, bonificado):
    df = pd.DataFrame(filas)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Detalle Cesión", index=False, startrow=10)
        worksheet = writer.sheets["Detalle Cesión"]

        worksheet.write("A1", "PARTICIPACIÓN ENJOY")
        worksheet.write("A2", f"Mes: {mes}")
        worksheet.write("A3", f"Estado: {'CERRADO' if cerrado else 'PROVISORIO'}")

        worksheet.write("F1", "Resumen General")
        worksheet.write("F2", "Total Facturado")
        worksheet.write("G2", resumen["total_facturado"])
        worksheet.write("F3", "Total Cedido")
        worksheet.write("G3", resumen["total_espacio"])
        worksheet.write("F4", "Neto Profesional")
        worksheet.write("G4", resumen["neto_profesional"])

        worksheet.write("A6", "Sesiones Socios Gym")
        worksheet.write("B6", sesiones["SOCIO_GYM"])
        worksheet.write("A7", "Sesiones General")
        worksheet.write("B7", sesiones["GENERAL"])

        worksheet.write("A8", "Bonificado Socios Gym")
        worksheet.write("B8", bonificado["SOCIO_GYM"])
        worksheet.write("A9", "Bonificado General")
        worksheet.write("B9", bonificado["GENERAL"])

        worksheet.set_column("A:A", 26)
        worksheet.set_column("B:G", 18)

    output.seek(0)
    return output

# =========================
# DASHBOARD
# =========================
def dashboard_ui():
    aplicar_estilos_globales()

    st.markdown("## 📊 Dashboard financiero")
    st.caption("Análisis profesional de facturación y cesión al gimnasio")

    datos = cargar_datos()
    turnos = datos["turnos"]
    pagos = datos["pagos"]
    cierres = datos["cierres"]

    if not turnos:
        st.info("No hay datos disponibles")
        return

    meses = sorted({t["fecha"][:7] for t in turnos if t.get("fecha")})
    mes = st.selectbox("Mes", meses)

# ... (código previo del selectbox de mes)

    filas_detalle = []
    sesiones = {"SOCIO_GYM": 0, "GENERAL": 0}
    bonificado = {"SOCIO_GYM": 0, "GENERAL": 0}

    for t in turnos:
            if not t.get("fecha", "").startswith(mes) or t.get("estado") != "ASISTIÓ":
                continue

            condicion = str(t.get("condicion_turno", "GENERAL")).upper()
            tipo = "SOCIO_GYM" if condicion == "SOCIO_GYM" else "GENERAL"
            sesiones[tipo] += 1

            # 1. Obtener datos básicos
            id_serv = t.get("id_servicio", 0)
            nom_serv = str(t.get("nombre_servicio", ""))
            v_facturado = int(t.get("valor_facturado", 0) or 0)
            v_teorico_full = calcular_precio_teorico(id_serv, nom_serv)

            # 2. Verificar si es Primera Evaluación
            # Filtramos los turnos de este paciente para la función educativa
            turnos_paciente = [tp for tp in turnos if tp.get("id_paciente") == t.get("id_paciente")]
            es_primera = es_primera_evaluacion(t, turnos_paciente)
            es_servicio_eval = nom_serv.lower().startswith("evaluacion")

            # 3. LÓGICA DE BONIFICACIÓN SEGÚN TU REGLA
            monto_bonificado = 0
        
            if es_servicio_eval and es_primera:
                if tipo == "SOCIO_GYM":
                    # BONIF 100% -> El ahorro es el total del precio
                    monto_bonificado = v_teorico_full 
                else:
                    # GENERAL: BONIF 50% -> El ahorro es la mitad
                    monto_bonificado = v_teorico_full * 0.5
            else:
                # Si NO es primera evaluación o es otro servicio, 
                # la bonificación es solo si cobraste menos del teórico por otra razón
                monto_bonificado = max(0, v_teorico_full - v_facturado)

            bonificado[tipo] += monto_bonificado

            # 4. Cálculo de participación (Comisión Gimnasio)
            calc = calcular_participacion_turno(t, None, turnos)

            filas_detalle.append({
                "Fecha": t["fecha"],
                "Paciente": t["nombre_paciente"],
                "Servicio": nom_serv,
                "1° Eval": "SÍ" if (es_servicio_eval and es_primera) else "NO",
                "Bruto ($)": v_facturado,
                "Bonificación ($)": int(monto_bonificado),
                "Porcentaje Espacio": f"{calc['porcentaje']}%",
                "Monto Espacio ($)": calc["participacion"],
                "Neto Profesional ($)": calc["neto"]
            })

    # ... (continúa con el resto de la UI de Streamlit)

    cerrado = mes_esta_cerrado(cierres, mes)

    if cerrado:
        cierre = next(c for c in cierres if c["mes"] == mes)
        total_facturado = cierre["total_facturado"]
        total_cobrado = cierre["total_cobrado"]
        total_deuda = 0
    else:
        cierre_preview = calcular_cierre_mes(turnos, pagos, mes)
        total_facturado = cierre_preview["total_facturado"]
        total_cobrado = cierre_preview["total_cobrado"]
        total_deuda = total_facturado - total_cobrado

    total_cedido = sum(f["Monto Espacio ($)"] for f in filas_detalle)
    neto_prof = sum(f["Neto Profesional ($)"] for f in filas_detalle)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💼 Facturado", f"${int(total_facturado)}")
    col2.metric("💰 Cobrado", f"${int(total_cobrado)}")
    col3.metric("⚠️ Deuda", f"${int(total_deuda)}")
    col4.metric("🏢 Cedido al Gimnasio", f"${int(total_cedido)}")


    st.divider()
    st.subheader("🏢 PARTICIPACIÓN ENJOY")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total facturado", f"${int(total_facturado)}")

    col_b.markdown(
        f"**Sesiones atendidas**\n\n"
        f"🏋️ Socios Gym: {sesiones['SOCIO_GYM']}\n\n"
        f"👤 General: {sesiones['GENERAL']}"
    )

    col_c.markdown(
        f"**Total bonificado**\n\n"
        f"🏋️ Socios Gym: ${int(bonificado['SOCIO_GYM'])}\n\n"
        f"👤 General: ${int(bonificado['GENERAL'])}"
    )

    st.divider()
    st.dataframe(pd.DataFrame(filas_detalle), use_container_width=True)

    st.divider()
    st.subheader("📥 Exportar estudio de cesión")

    excel = generar_excel_cesion(
        mes,
        filas_detalle,
        {
            "total_facturado": total_facturado,
            "total_espacio": total_cedido,
            "neto_profesional": neto_prof
        },
        cerrado,
        sesiones,
        bonificado
    )

    st.download_button(
        "⬇️ Descargar estudio en Excel",
        excel,
        f"estudio_cesion_gimnasio_{mes}.xlsx"
    )

    if st.button("📄 Generar PDF de liquidación"):
        generar_pdf_liquidacion(
            archivo=f"liquidacion_{mes}.pdf",
            mes=mes,
            resumen={
                "total_facturado": total_facturado,
                "total_espacio": total_cedido,
                "neto_profesional": neto_prof,
            },
            detalle_turnos=filas_detalle,
            definitivo=cerrado
        )
        st.success("PDF generado correctamente")
