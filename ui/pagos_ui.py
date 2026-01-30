import streamlit as st
import pandas as pd
from data.sheets_client import get_sheet
from domain.pagos import nuevo_pago

def pagos_ui():
    st.header("💰 Cobros")

    sheet = get_sheet("Consultorio")
    ws_turnos = sheet.worksheet("turnos")
    ws_pagos = sheet.worksheet("pagos")

    turnos = ws_turnos.get_all_records()
    pagos = ws_pagos.get_all_records()

    if not turnos:
        st.warning("No hay turnos cargados")
        return

    df_turnos = pd.DataFrame(turnos)
    df_pagos = pd.DataFrame(pagos) if pagos else pd.DataFrame()

    turno_sel = st.selectbox(
        "Seleccionar turno",
        df_turnos["id_turno"] + " - " + df_turnos["nombre_paciente"]
    )

    id_turno = turno_sel.split(" - ")[0]

    monto = st.number_input("Monto a cobrar", min_value=0)
    metodo = st.selectbox("Método de pago", ["EFECTIVO", "TRANSFERENCIA", "MP"])
    obs = st.text_input("Observaciones")

    if st.button("Registrar pago"):
        pago = nuevo_pago(id_turno, monto, metodo, obs)
        ws_pagos.append_row(list(pago.values()))
        st.success("Pago registrado")

    if not df_pagos.empty:
        pagos_turno = df_pagos[df_pagos["id_turno"] == id_turno]
        st.subheader("Pagos del turno")
        st.dataframe(pagos_turno)
