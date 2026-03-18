import streamlit as st
import gspread
import time
from google.oauth2.service_account import Credentials

@st.cache_resource
def get_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets no configurados correctamente.")
        st.stop()
    
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        info["private_key"] = info["private_key"].strip().replace("\\n", "\n")
    
    try:
        creds = Credentials.from_service_account_info(
            info, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de autenticación: {e}")
        st.stop()

def get_sheet(sheet_name="Consultorio"):
    client = get_client()
    for i in range(3):
        try:
            return client.open(sheet_name)
        except Exception:
            if i < 2:
                time.sleep(2)
                continue
    return client.open(sheet_name)

def obtener_siguiente_id(datos_lista, nombre_columna="id"):
    """Calcula el ID localmente para no gastar cuota de Google."""
    if not datos_lista:
        return 1
    try:
        ids = [int(row.get(nombre_columna, 0)) for row in datos_lista if str(row.get(nombre_columna)).isdigit()]
        return max(ids) + 1 if ids else 1
    except:
        return 1