import streamlit as st

from ui.recepcion_ui import recepcion_ui
from ui.pagos_ui import pagos_ui
from ui.dashboard_ui import dashboard_ui
from ui.pacientes_ui import pacientes_ui
from ui.servicios_ui import servicios_ui
from ui.agenda_ui import agenda_ui

from data.sheets_client import get_sheet


# =========================
# CONFIG STREAMLIT
# =========================

st.set_page_config(
    page_title="Consultorio",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================
# HELPERS DE LECTURA (CACHE)
# =========================

@st.cache_data(show_spinner=False)
def leer_hoja(_sheet, nombre_hoja):
    """
    _sheet NO se hashea (objeto gspread)
    nombre_hoja SÍ se usa como clave de cache
    """
    return _sheet.worksheet(nombre_hoja).get_all_records()


# =========================
# CARGA GLOBAL (UNA SOLA VEZ)
# =========================

sheet = get_sheet("Consultorio")

pacientes = leer_hoja(sheet, "pacientes")
servicios = leer_hoja(sheet, "servicios")
planes_pacientes = leer_hoja(sheet, "planes_pacientes")


# =========================
# ESTILOS
# =========================

st.markdown("""
<style>
:root {
    --primary-color: #60b067;
}
</style>
""", unsafe_allow_html=True)


# =========================
# SIDEBAR
# =========================

st.sidebar.markdown("### Modo")

modo = st.sidebar.selectbox(
    "",
    ["Recepción", "Profesional"])

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


# =========================
# NAVEGACIÓN
# =========================

if modo == "Recepción":
    recepcion_ui()

else:
    if menu == "Pacientes":
        pacientes_ui()

    elif menu == "Servicios":
        servicios_ui()

    elif menu == "Agenda":
        agenda_ui(
            sheet=sheet,
            pacientes=pacientes,
            servicios=servicios,
            planes_pacientes=planes_pacientes
        )

    elif menu == "Cobros":
        pagos_ui()

    elif menu == "Dashboard":
        dashboard_ui()
