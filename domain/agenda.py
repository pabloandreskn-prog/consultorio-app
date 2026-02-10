agenda figura asi y mi codigo es este_: 

import streamlit as st
from datetime import date
from data.sheets_client import get_sheet
from domain.finanzas import facturar_turno_individual
from domain.cierres import mes_esta_cerrado

def agenda_ui():
    st.header("📅 Agenda")

    sheet = get_sheet("Consultorio")
    ws_turnos = sheet.worksheet("turnos")
    ws_planes = sheet.worksheet("planes_pacientes")
    planes = ws_planes.get_all_records()
    df_planes = pd.DataFrame(planes)
    ws_cierres = sheet.worksheet("cierres")

    turnos = ws_turnos.get_all_records()
    cierres = ws_cierres.get_all_records()

    fecha = st.date_input("Fecha", value=date.today())
    mes_actual = fecha.strftime("%Y-%m")

    if mes_esta_cerrado(cierres, mes_actual):
        st.warning("🔒 Este mes está cerrado. La agenda es solo de lectura.")

    turnos_dia = [
        (i + 2, t) for i, t in enumerate(turnos)
        if t["fecha"] == str(fecha)
    ]

    if not turnos_dia:
        st.info("No hay turnos para esta fecha")
        return

    for fila, t in turnos_dia:
        c1, c2, c3, c4 = st.columns([2, 4, 2, 2])

        c1.write(f"🕒 {t['hora']}")
        c2.write(f"🧍 {t['paciente']}")

        estado = "🟢 Pagado" if t["pagado"] == "SI" else "🔴 Pendiente"
        c3.write(estado)

        if not mes_esta_cerrado(cierres, mes_actual):
            if c4.button("✔️ Asistió", key=f"a{fila}"):
                ws_turnos.update_cell(fila, 5, "SI")
                st.success("Asistencia registrada")

