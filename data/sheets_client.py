import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Error: No se encontraron los Secrets 'gcp_service_account'.")
        st.stop()
        
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet(sheet_name):
    client = get_client()
    return client.open(sheet_name)

def obtener_siguiente_id(worksheet_name, id_column_name="id"):
    """Función auxiliar para autogenerar IDs en las hojas de cálculo"""
    try:
        sheet = get_sheet("Consultorio")
        ws = sheet.worksheet(worksheet_name)
        data = ws.get_all_records()
        if not data:
            return 1
        ids = [int(row[id_column_name]) for row in data if str(row[id_column_name]).isdigit()]
        return max(ids) + 1 if ids else 1
    except Exception:
        return 1
