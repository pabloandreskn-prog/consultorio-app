import streamlit as st
from datetime import date, timedelta
from data.sheets_client import get_sheet
from domain.finanzas import mes_esta_cerrado, calcular_deuda_turno
from ui.caja_modal import caja_modal_ui


# ==========================
# RECEPCIÓN – VISTA SEMANAL
# ==========================

def recepcion_semanal_ui():
    st.markdown("## 📅 Recepción – Vista semanal")

    sheet = get_sheet("Consultorio")
    ws_turnos = sheet.worksheet("turnos")
    ws_cierres = sheet.worksheet("cierres")

    turnos = ws_turnos.get_all_records()
    cierres = ws_cierres.get_all_records()

    # ------------------
    # Selección de semana
    # ------------------
    hoy = date.today()
    inicio_semana = st.date_input(
        "Semana desde",
        hoy - timedelta(days=hoy.weekday())
    )

    fin_semana = inicio_semana + timedelta(days=6)

    st.caption(
        f"Semana: {inicio_semana.isoformat()} → {fin_semana.isoformat()}"
    )

    # ------------------
    # Filtrar turnos
    # ------------------
    turnos_semana = [
        t for t in turnos
        if inicio_semana.isoformat() <= t.get("fecha", "") <= fin_semana.isoformat()
    ]

    if not turnos_semana:
        st.info("No hay turnos en esta semana")
        return

    # ------------------
    # Mostrar por día
    # ------------------
    for d in range(7):
        dia = inicio_semana + timedelta(days=d)
        fecha_str = dia.isoformat()

        turnos_dia = [
            t for t in turnos_semana
            if t.get("fecha") == fecha_str
        ]

        if not turnos_dia:
            continue

        st.markdown(f"### 🗓️ {dia.strftime('%A %d/%m')}")

        for i, t in enumerate(turnos_dia, start=2):
            mes_turno = t["fecha"][:7]
            cerrado = mes_esta_cerrado(cierres, mes_turno)

            with st.container(border=True):

                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    st.markdown(
                        f"**{t['hora']}**  \n"
                        f"{t['nombre_paciente']}"
                    )

                with col2:
                    st.write(t["nombre_servicio"])

                with col3:
                    estado = st.selectbox(
                        "Asistencia",
                        ["PENDIENTE", "ASISTIÓ", "AUSENTE"],
                        index=["PENDIENTE", "ASISTIÓ", "AUSENTE"].index(
                            t.get("estado", "PENDIENTE")
                        ),
                        key=f"estado_sem_{t['id_turno']}"
                    )

                with col4:
                    if cerrado:
                        st.markdown("🔒")
                    else:
                        st.markdown("🟢")

    # ==================
    # BADGE DE DEUDA + COBRO
    # ==================

    deuda = calcular_deuda_turno(t)

    col_a, col_b = st.columns([2, 1])

    with col_a:
        if deuda == 0:
            st.success("🟢 Sin deuda")
        else:
            st.warning(f"🟡 Debe ${deuda:,.0f}".replace(",", "."))

    with col_b:
        if deuda > 0 and not cerrado:
            if st.button(
                "💰 Cobro pendiente",
                key=f"cobro_{t['id_turno']}"
            ): 
                st.session_state["turno_a_cobrar"] = t
                st.info("Cobro preparado (continuar en caja)")
        elif cerrado:
            st.caption("🔒 Mes cerrado")

                # ------------------
                # Guardar asistencia
                # ------------------
                if st.button(
                    "Guardar",
                    key=f"save_sem_{t['id_turno']}"
                ):
                    COL_ESTADO = 6  # ajustá si cambia
                    ws_turnos.update_cell(i, COL_ESTADO, estado)
                    st.success("Asistencia actualizada")

# ==================
# MODAL DE CAJA
# ==================
caja_modal_ui()
