import streamlit as st
import pandas as pd
from data.sheets_client import get_sheet
from domain.turnos import calcular_hora_fin, nuevo_turno
from domain.agenda import hay_solapamiento

def agenda_ui():
    st.header("📅 Agenda")

    sheet = get_sheet("Consultorio")
    ws_turnos = sheet.worksheet("turnos")
    ws_pacientes = sheet.worksheet("pacientes")
    ws_servicios = sheet.worksheet("servicios")

    pacientes = ws_pacientes.get_all_records()
    servicios = ws_servicios.get_all_records()
    turnos = ws_turnos.get_all_records()

    if not pacientes or not servicios:
        st.warning("Debe haber pacientes y servicios cargados")
        return

    df_pac = pd.DataFrame(pacientes)
    df_serv = pd.DataFrame(servicios)

    with st.form("form_turno"):
        fecha = st.date_input("Fecha")
        hora_inicio = st.time_input("Hora inicio")

        paciente = st.selectbox(
            "Paciente",
            df_pac["nombre"].tolist()
        )

        servicio = st.selectbox(
            "Servicio",
            df_serv["nombre"].tolist()
        )

        submitted = st.form_submit_button("Crear turno")

    if submitted:
        pac = df_pac[df_pac["nombre"] == paciente].iloc[0]
        serv = df_serv[df_serv["nombre"] == servicio].iloc[0]

        hora_inicio_str = hora_inicio.strftime("%H:%M")
        hora_fin = calcular_hora_fin(hora_inicio_str, serv["duracion_min"])

        if hay_solapamiento(turnos, fecha.strftime("%Y-%m-%d"), hora_inicio_str, hora_fin):
            st.error("⛔ Turno solapado con otro existente")
            return

        turno = nuevo_turno(
            fecha.strftime("%Y-%m-%d"),
            hora_inicio_str,
            hora_fin,
            pac["id_paciente"],
            pac["nombre"],
            serv["id_servicio"],
            serv["nombre"]
        )

        ws_turnos.append_row(list(turno.values()))
        st.success("Turno creado correctamente")

    if turnos:
        st.subheader("Turnos del día")
        df_turnos = pd.DataFrame(turnos)
        st.dataframe(df_turnos)
