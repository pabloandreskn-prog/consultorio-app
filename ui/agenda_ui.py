import streamlit as st
import pandas as pd
from datetime import date, time
import uuid

from data.sheets_client import get_sheet
from domain.finanzas import mes_cerrado
from ui.styles import aplicar_estilos_globales


# =========================
# HELPERS
# =========================
def hay_turno_en_mismo_horario(turnos, fecha, hora):
    return any(
        t.get("fecha") == fecha and t.get("hora") == hora
        for t in turnos
    )


# =========================
# UI AGENDA
# =========================
def agenda_ui():
    st.header("📅 Agenda")

    sheet = get_sheet("Consultorio")
    ws_turnos = sheet.worksheet("turnos")
    ws_pacientes = sheet.worksheet("pacientes")
    ws_servicios = sheet.worksheet("servicios")
    ws_cierres = sheet.worksheet("cierres")

    turnos = ws_turnos.get_all_records()
    pacientes = ws_pacientes.get_all_records()
    servicios = ws_servicios.get_all_records()

    # =========================
    # FECHA
    # =========================
    fecha = st.date_input("Fecha", value=date.today())
    fecha_str = fecha.strftime("%Y-%m-%d")
    mes_str = fecha.strftime("%Y-%m")

    cerrado = mes_cerrado(ws_cierres, mes_str)

    if cerrado:
        st.warning(f"🔒 El mes {mes_str} está cerrado. Edición bloqueada.")

    # =========================
    # FORMULARIO NUEVO TURNO
    # =========================
    st.subheader("➕ Agendar nuevo turno")

    if cerrado:
        st.info("No se pueden crear turnos en meses cerrados.")
    elif not pacientes or not servicios:
        st.warning("Debe haber pacientes y servicios cargados.")
    else:
        df_pac = pd.DataFrame(pacientes)
        df_serv = pd.DataFrame(servicios)

        with st.form("form_nuevo_turno"):
            col1, col2 = st.columns(2)

            with col1:
                paciente = st.selectbox(
                    "Paciente",
                    df_pac["nombre"].tolist()
                )

            with col2:
                servicio = st.selectbox(
                    "Servicio",
                    df_serv["nombre"].tolist()
                )

            hora = st.time_input("Hora", value=time(9, 0))
            sobreturno = st.checkbox("Permitir sobreturno")

            submitted = st.form_submit_button("Agendar turno")

        if submitted:
            hora_str = hora.strftime("%H:%M")

            existe = hay_turno_en_mismo_horario(
                turnos,
                fecha_str,
                hora_str
            )

            if existe and not sobreturno:
                st.error(
                    "⛔ Ya existe un turno en ese horario. "
                    "Activá 'Permitir sobreturno' para continuar."
                )
                return

            estado = "SOBRETURNO" if existe and sobreturno else "RESERVADO"

            fila = [
                str(uuid.uuid4()),   # id_turno
                fecha_str,
                hora_str,
                "",                  # id_paciente
                paciente,
                "",                  # id_servicio
                servicio,
                estado,
                ""                   # precio
            ]

            ws_turnos.append_row(fila)
            st.success("✅ Turno agendado correctamente")
            st.rerun()

    # =========================
    # TURNOS DEL DÍA
    # =========================
    st.divider()
    st.subheader("📋 Turnos del día")

    turnos_dia = [
        (i + 2, t)
        for i, t in enumerate(turnos)
        if t.get("fecha") == fecha_str
    ]

    if not turnos_dia:
        st.info("No hay turnos para esta fecha")
        return

    for fila, t in turnos_dia:
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 4, 3, 2])

            hora_txt = f"🕒 {t.get('hora', '')}"
            if t.get("estado") == "SOBRETURNO":
                hora_txt += " ⚠️"

            c1.write(hora_txt)
            c2.write(f"🧍 {t.get('nombre_paciente', '')}")
            c3.write(f"📌 {t.get('estado', '')}")

            if cerrado:
                c4.write("🔒")
            else:
                if c4.button("✔️ Asistió", key=f"a{fila}"):
                    ws_turnos.update_cell(fila, 8, "ASISTIÓ")
                    st.success("Asistencia registrada")
                    st.rerun()
