import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

@st.cache_resource
def get_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets no configurados correctamente en la web de Streamlit.")
        st.stop()
    
    info = dict(st.secrets["gcp_service_account"])
    
    if "private_key" in info:
        pk = info["private_key"].strip()
        pk = pk.replace("\\n", "\n")
        info["private_key"] = pk
    
    try:
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error en la autenticación: {e}")
        st.stop()

def get_sheet(sheet_name):
    return get_client().open(sheet_name)

def obtener_siguiente_id(worksheet_name, id_column_name="id"):
    """
    Busca el ID más alto en la columna especificada y devuelve el siguiente.
    """
    try:
        # Abrimos la hoja 'Consultorio' y la pestaña específica
        sheet = get_sheet("Consultorio")
        ws = sheet.worksheet(worksheet_name)
        data = ws.get_all_records()
        
        if not data:
            return 1
            
        # Extraemos los IDs asegurándonos de que sean números
        ids = []
        for row in data:
            val = row.get(id_column_name)
            if str(val).isdigit():
                ids.append(int(val))
        
        return max(ids) + 1 if ids else 1
    except Exception:
        # Si algo falla (hoja vacía, columna inexistente), empezamos en 1
<<<<<<< HEAD
        return 1
=======
        return 1
>>>>>>> 359cd74a60f532b46dac154006f5cd950f24a29a
