import streamlit as st
from datetime import date
from data.sheets_client import get_sheet
from domain.finanzas import detectar_deuda

def recepcion_ui():
    st.header("🛎️ Recepción")

    sheet = get_sheet("Consultorio")
    ws = sheet.worksheet("Turnos")
    turnos = ws.get_all_records()

    # Alerta de deuda (ahora sí, con turnos definidos)
    if detectar_deuda(turnos):
        st.warning("⚠️ Atención: hay pacientes con deuda activa")

    hoy = st.date_input("Fecha", value=date.today())

    turnos_hoy = [
        (i + 2, t)
        for i, t in enumerate(turnos)
        if t.get("fecha") == str(hoy)
    ]

    if not turnos_hoy:
        st.info("No hay turnos para hoy")
        return

    for fila, t in turnos_hoy:
        c1, c2, c3 = st.columns([4, 1, 1])

        c1.write(f"🕒 {t.get('hora', '')} — {t.get('paciente', '')}")

        if c2.button("✔️ Asistió", key=f"a{fila}"):
            ws.update_cell(fila, 5, "SI")
            st.success("Asistencia registrada")

        if c3.button("💰 Cobrar", key=f"c{fila}"):
            ws.update_cell(fila, 6, "SI")
            st.success("Pago registrado")
