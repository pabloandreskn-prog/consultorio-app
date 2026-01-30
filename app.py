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

st.sidebar.title("Menú")

menu = st.sidebar.selectbox(
    "",
    ["Pacientes", "Servicios", "Agenda", "Cobros", "Dashboard"]
)

if menu == "Pacientes":
    pacientes_ui()

elif menu == "Servicios":
    servicios_ui()

elif menu == "Agenda":
    agenda_ui()

elif menu == "Cobros":
    pagos_ui()

elif menu == "dashboard":
    dashboard_ui()
    dashboard_ui()
