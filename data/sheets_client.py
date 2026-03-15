import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

@st.cache_resource
def get_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets no configurados correctamente en la web de Streamlit.")
        st.stop()
    
    # Convertimos los secretos a un diccionario real
    info = dict(st.secrets["gcp_service_account"])
    
    # LIMPIEZA QUIRÚRGICA:
    if "private_key" in info:
        # Quitamos espacios en blanco accidentales al inicio y final
        pk = info["private_key"].strip()
        # Si por alguna razón los saltos de línea se pegaron como texto literal "\n"
        pk = pk.replace("\\n", "\n")
        info["private_key"] = pk
    
    try:
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        # Esto nos dirá si el problema es de formato o de permisos
        st.error(f"Error en la autenticación: {e}")
        st.stop()

def get_sheet(sheet_name):
    return get_client().open(sheet_name)
