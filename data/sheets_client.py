import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_client():
    # 1. Verificar que existan los secretos
    if "gcp_service_account" not in st.secrets:
        st.error("Error: No se encontraron los Secrets 'gcp_service_account'.")
        st.stop()
        
    # 2. Convertir a diccionario y limpiar la llave
    info = dict(st.secrets["gcp_service_account"])
    
    if "private_key" in info:
        # Esto arregla tanto \n como saltos de línea reales
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    
    # 3. Crear credenciales
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet(sheet_name):
    client = get_client()
    return client.open(sheet_name)
