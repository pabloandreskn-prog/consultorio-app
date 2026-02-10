import streamlit as st
import pandas as pd
from datetime import date

from data.sheets_client import get_sheet
from domain.cierres import mes_esta_cerrado
from ui.styles import aplicar_estilos_globales

# =========================
# CARGA DE DATOS (SOLO DATOS, NO OBJETOS)
# =========================
@st.cache_data(ttl=300)
def cargar_datos():
    sheet = get_sheet("Consultorio")

    pagos = sheet.worksheet("pagos").get_all_records()
    cierres = sheet.worksheet("cierres").get_all_records()

    return {
        "pagos": pagos,
        "cierres": cierres
    }

# =========================
# HELPERS
# =========================
def es_pago_sospechoso(pagos, paciente, fecha, monto, metodo):
    for p in pagos:
        if (
            p.get("paciente") == paciente
            and p.get("fecha") == fecha
            and str(p.get("monto")) == str(monto)
            and p.get("metodo") == metodo
        ):
            return True
    return False
def generar_id_numerico(pagos):
    """
    Devuelve el próximo ID numérico disponible.
    Ignora IDs no numéricos (UUID viejos).
    """
    ids_numericos = []

    for p in pagos:
        try:
            ids_numericos.append(int(p.get("id_pago")))
        except (TypeError, ValueError):
            continue

    return max(ids_numericos, default=0) + 1

# =========================
# UI PAGOS
# =========================
def pagos_ui():
    aplicar_estilos_globales()
    st.header("💰 Pagos")

    datos = cargar_datos()
    pagos = datos["pagos"]
    cierres = datos["cierres"]

    # =========================
    # SELECCIÓN DE MES
    # =========================
    meses = sorted({p["mes"] for p in pagos if p.get("mes")})

    mes_actual = date.today().strftime("%Y-%m")
    if mes_actual not in meses:
        meses.append(mes_actual)

    mes = st.selectbox("Mes", sorted(meses))

    cerrado = mes_esta_cerrado(cierres, mes)

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

            if es_pago_sospechoso(pagos, paciente, fecha_str, monto, metodo):
                st.warning(
                    "⚠️ Ya existe un pago con los mismos datos "
                    "(paciente, fecha, monto y método)."
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

            # 🔑 OBJETO FRESCO PARA ESCRIBIR
            sheet = get_sheet("Consultorio")
            ws_pagos = sheet.worksheet("pagos")
            ws_pagos.append_row(nuevo_pago)

            st.success("✅ Pago registrado correctamente")
            st.rerun()

    # =========================
    # LISTADO DE PAGOS
    # =========================
    st.divider()
    st.subheader("📋 Pagos registrados")

    pagos_mes = [p for p in pagos if p.get("mes") == mes]

    if pagos_mes:
        df = pd.DataFrame(pagos_mes)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay pagos registrados para este mes")

    # =========================
    # PAGOS POR TURNO (SEGURO)
    # =========================
    pagos_por_turno = {}

    for pago in pagos:
        id_turno = pago.get("id_turno")
        if not id_turno:
            continue

        pagos_por_turno[id_turno] = (
            pagos_por_turno.get(id_turno, 0) + pago.get("monto", 0)
        )
