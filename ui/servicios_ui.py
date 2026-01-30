import streamlit as st
import pandas as pd
from data.sheets_client import get_sheet
from domain.servicios import nuevo_servicio

def servicios_ui():
    st.header("🧾 Servicios")

    sheet = get_sheet("Consultorio")
    ws = sheet.worksheet("servicios")

    with st.form("form_servicio"):
        categoria = st.selectbox(
            "Categoría",
            ["KINESIO", "MASAJE", "EVALUACION"]
        )
        nombre = st.text_input("Nombre del servicio")
        duracion = st.number_input("Duración (minutos)", min_value=5, step=5)
        precio = st.number_input("Precio base", min_value=0)

        submitted = st.form_submit_button("Guardar servicio")

    if submitted:
        servicio = nuevo_servicio(categoria, nombre, duracion, precio)
        ws.append_row(list(servicio.values()))
        st.success("Servicio guardado")

    data = ws.get_all_records()
    if data:
        st.dataframe(pd.DataFrame(data))
