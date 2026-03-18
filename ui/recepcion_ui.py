import streamlit as st
from data.sheets_client import get_sheet
from ui.styles import aplicar_estilos_globales

def limpiar_monto(valor):
    """Limpia formatos de moneda para cálculos matemáticos."""
    if valor == "" or valor is None or str(valor).lower() == 'no': 
        return 0.0
    try:
        if isinstance(valor, str):
            v = str(valor).replace('$', '').replace('.', '').replace(',', '.').strip()
            return float(v)
        return float(valor)
    except: 
        return 0.0

def recepcion_ui():
    # 1. Aplicar estética
    aplicar_estilos_globales()
    
    st.markdown("<h1 style='text-align: center;'>🏨 Gestión de Recepción</h1>", unsafe_allow_html=True)
    
    # 2. Conexión a la base de datos
    sheet = get_sheet("Consultorio")
    
    # 3. Llamada a la Agenda (Arquitectura Centralizada)
    # Importamos aquí para evitar problemas de recursión.
    # No pasamos 'pacientes' ni 'servicios' manualmente para no saturar la cuota de Google.
    # La nueva agenda_ui se encarga de cargar todo de forma protegida (anti-error 429).
    from ui.agenda_ui import agenda_ui 
    
    agenda_ui(sheet, None, None, None)

# Nota: El resto de la lógica de carga y visualización ahora vive 
# dentro de la carga centralizada de agenda_ui.py para máxima estabilidad.