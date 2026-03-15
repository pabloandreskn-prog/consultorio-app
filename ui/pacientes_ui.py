import streamlit as st
import pandas as pd
from data.sheets_client import get_sheet, obtener_siguiente_id # Importamos la nueva función
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
        # 1. Calculamos el siguiente ID numérico real
        id_nuevo = obtener_siguiente_id("Consultorio", "pacientes")
        
        # 2. Se lo pasamos a la función del dominio
        paciente = nuevo_paciente(id_nuevo, nombre, dni, telefono, tipo_cliente, observaciones)
        
        # 3. Guardamos
        ws.append_row(list(paciente.values()))
        st.success(f"Paciente registrado correctamente con ID: {id_nuevo}")

    # Mostrar tabla
    data = ws.get_all_records()
    if data:
        st.dataframe(pd.DataFrame(data))