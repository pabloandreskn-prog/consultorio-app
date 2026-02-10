import streamlit as st
from datetime import date
from data.sheets_client import get_sheet
from domain.finanzas import mes_esta_cerrado, calcular_deuda_turno


def caja_modal_ui():
    if "turno_a_cobrar" not in st.session_state:
        return

    t = st.session_state["turno_a_cobrar"]

    sheet = get_sheet("Consultorio")
    ws_turnos = sheet.worksheet("turnos")
    ws_pagos = sheet.worksheet("pagos")
    ws_cierres = sheet.worksheet("cierres")

    cierres = ws_cierres.get_all_records()

    mes_turno = t["fecha"][:7]
    cerrado = mes_esta_cerrado(cierres, mes_turno)

    with st.dialog("💰 Cobro de turno"):
        st.markdown(
            f"""
            **Paciente:** {t['nombre_paciente']}  
            **Servicio:** {t['nombre_servicio']}  
            **Fecha:** {t['fecha']} {t.get('hora','')}
            """
        )

        if cerrado:
            st.error(f"🔒 El mes {mes_turno} está cerrado. No se puede cobrar.")
            if st.button("Cerrar"):
                del st.session_state["turno_a_cobrar"]
            return

        monto = st.number_input(
            "Monto a cobrar",
            min_value=0,
            step=1000,
            value=int(t.get("valor_facturado", 0) or 0)
        )

        medio = st.selectbox(
            "Medio de pago",
            ["Efectivo", "Transferencia", "MP", "Débito"]
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("❌ Cancelar"):
                del st.session_state["turno_a_cobrar"]
                st.rerun()

        with col2:
            if st.button("💾 Confirmar cobro"):
                turnos = ws_turnos.get_all_records()

                # Buscar fila real del turno
                fila_turno = next(
                    i + 2 for i, x in enumerate(turnos)
                    if x.get("id_turno") == t["id_turno"]
                )

                COL_FACTURADO = 7  # ajustá si cambia
                ws_turnos.update_cell(fila_turno, COL_FACTURADO, monto)

                ws_pagos.append_row([
                    "",                     # id_pago
                    date.today().isoformat(),
                    mes_turno,
                    t["id_turno"],
                    t["id_paciente"],
                    t["nombre_paciente"],
                    monto,
                    medio
                ])

                st.success("Cobro registrado correctamente")
                del st.session_state["turno_a_cobrar"]
                st.rerun()
