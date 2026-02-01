import streamlit as st
import pandas as pd
from data.sheets_client import get_sheet
from domain.pacientes import nuevo_paciente
from ui.styles import aplicar_estilos_globales


def pacientes_ui():
    st.header("👤 Pacientes")

    sheet = get_sheet("Consultorio")
    ws = sheet.worksheet("pacientes")

    with st.form("form_paciente"):
        nombre = st.text_input("Nombre")
        dni = st.text_input("DNI")
        telefono = st.text_input("Teléfono")
        tipo_cliente = st.selectbox("Tipo de cliente", ["SOCIO_GIM", "PUBLICO"])
        observaciones = st.text_area("Observaciones")

        submitted = st.form_submit_button("Guardar paciente")

    if submitted:
        paciente = nuevo_paciente(nombre, dni, telefono, tipo_cliente, observaciones)
        ws.append_row(list(paciente.values()))
        st.success("Paciente registrado correctamente")

    data = ws.get_all_records()
    if data:
        st.dataframe(pd.DataFrame(data))
