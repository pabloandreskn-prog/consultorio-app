from ui.recepcion_ui import recepcion_ui
import streamlit as st
from ui.pagos_ui import pagos_ui
from ui.dashboard_ui import dashboard_ui


from ui.pacientes_ui import pacientes_ui
from ui.servicios_ui import servicios_ui
from ui.agenda_ui import agenda_ui
st.set_page_config(
    page_title="Consultorio",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
<style>
:root {
    --primary-color: #60b067;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("### Modo")

modo = st.sidebar.selectbox(
    "",
    ["Profesional", "Recepción"]
)

st.sidebar.title("Menú")

if modo == "Profesional":
    menu = st.sidebar.selectbox(
        "",
        ["Pacientes", "Servicios", "Agenda", "Cobros", "Dashboard"]
    )
else:
    menu = st.sidebar.selectbox(
        "",
        ["Agenda", "Cobros"]
    )

if modo == "Recepción":
    recepcion_ui()

else:
    if menu == "Pacientes":
        pacientes_ui()

    elif menu == "Servicios":
        servicios_ui()

    elif menu == "Agenda":
        agenda_ui()

    elif menu == "Cobros":
        pagos_ui()

    elif menu == "Dashboard":
        dashboard_ui()
