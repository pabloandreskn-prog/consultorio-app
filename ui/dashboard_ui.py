import streamlit as st
import pandas as pd
from data.sheets_client import get_sheet
from domain.finanzas import resumen_financiero

def dashboard_ui():
    st.header("📊 Dashboard Financiero")

    sheet = get_sheet("Consultorio")
    turnos = sheet.worksheet("turnos").get_all_records()
    pagos = sheet.worksheet("pagos").get_all_records()

    if not turnos:
        st.warning("No hay datos")
        return

    df = resumen_financiero(turnos, pagos)

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos", f"${df['monto'].sum():,.0f}")
    col2.metric("Deuda pendiente", f"${df['deuda'].sum():,.0f}")
    col3.metric("Turnos", len(df))

    st.subheader("Detalle")
    st.dataframe(df)
