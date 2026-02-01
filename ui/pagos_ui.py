import streamlit as st
import pandas as pd
import uuid
from datetime import date

from data.sheets_client import get_sheet
from domain.finanzas import mes_cerrado
from ui.styles import aplicar_estilos_globales

def dashboard_ui():
    aplicar_estilos_globales()
    st.header("📊 Dashboard")


# =========================
# HELPERS
# =========================
def es_pago_sospechoso(pagos, paciente, fecha, monto, metodo):
    """
    Devuelve True si existe un pago con:
    mismo paciente + fecha + monto + método
    """
    for p in pagos:
        if (
            p.get("paciente") == paciente
            and p.get("fecha") == fecha
            and str(p.get("monto")) == str(monto)
            and p.get("metodo") == metodo
        ):
            return True
    return False


# =========================
# UI PAGOS
# =========================
def pagos_ui():
    st.header("💰 Pagos")

    sheet = get_sheet("Consultorio")
    ws_pagos = sheet.worksheet("pagos")
    ws_cierres = sheet.worksheet("cierres")

    pagos = ws_pagos.get_all_records()

    # =========================
    # SELECCIÓN DE MES
    # =========================
    meses = sorted(
        {p["mes"] for p in pagos if p.get("mes")}
    )

    mes_actual = date.today().strftime("%Y-%m")
    if mes_actual not in meses:
        meses.append(mes_actual)

    mes = st.selectbox("Mes", sorted(meses))

    cerrado = mes_cerrado(ws_cierres, mes)

    if cerrado:
        st.warning(f"🔒 El mes {mes} está cerrado. No se pueden registrar pagos.")

    # =========================
    # FORMULARIO NUEVO PAGO
    # =========================
    st.subheader("➕ Registrar pago")

    if not cerrado:
        with st.form("form_pago"):
            fecha = st.date_input("Fecha", value=date.today())
            paciente = st.text_input("Paciente")
            monto = st.number_input("Monto", min_value=0, step=100)
            metodo = st.selectbox(
                "Método de pago",
                ["Efectivo", "Transferencia", "Tarjeta", "Otro"]
            )
            observacion = st.text_area("Observación")

            submitted = st.form_submit_button("Guardar pago")

        if submitted:
            fecha_str = fecha.strftime("%Y-%m-%d")
            mes_str = fecha.strftime("%Y-%m")

            # ⚠️ Advertencia por posible duplicado
            if es_pago_sospechoso(pagos, paciente, fecha_str, monto, metodo):
                st.warning(
                    "⚠️ Ya existe un pago con los mismos datos "
                    "(paciente, fecha, monto y método). "
                    "Si corresponde a otra sesión, podés continuar."
                )

            nuevo_pago = [
                str(uuid.uuid4()),
                fecha_str,
                mes_str,
                paciente,
                monto,
                metodo,
                observacion
            ]

            ws_pagos.append_row(nuevo_pago)
            st.success("✅ Pago registrado correctamente")
            st.rerun()

    # =========================
    # LISTADO DE PAGOS
    # =========================
    st.divider()
    st.subheader("📋 Pagos registrados")

    pagos_mes = [
        p for p in pagos
        if p.get("mes") == mes
    ]

    if pagos_mes:
        df = pd.DataFrame(pagos_mes)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay pagos registrados para este mes")
