import streamlit as st
from data.sheets_client import get_sheet

def cierres_ui():
    st.header("🔐 Cierre mensual")

    sheet = get_sheet("Consultorio")
    ws_cierres = sheet.worksheet("cierres")

    mes = st.text_input("Mes a cerrar (YYYY-MM)")

    total_facturado = st.number_input("Total facturado", min_value=0.0)
    total_cobrado = st.number_input("Total cobrado", min_value=0.0)

    if st.button("Cerrar mes"):
        diferencia = total_facturado - total_cobrado

        fila = [
            mes,
            total_facturado,
            total_cobrado,
            diferencia,
            "SI"
        ]

        ws_cierres.append_row(fila)
        st.success(f"✅ Mes {mes} cerrado correctamente")
        st.rerun()
