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
        pk = info["private_key"]
        # 1. Quitar comillas accidentales al inicio/final
        pk = pk.strip("'").strip('"')
        # 2. Convertir los \n literales en saltos de línea reales
        pk = pk.replace("\\n", "\n")
        # 3. Si por alguna razón se pegó todo en una línea sin \n (pasa a veces), 
        # intentamos reconstruir los saltos básicos del formato PEM
        if "-----BEGIN PRIVATE KEY-----" in pk and "\n" not in pk.replace("-----BEGIN PRIVATE KEY-----", ""):
             pk = pk.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
             pk = pk.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
        
        info["private_key"] = pk

    try:
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error crítico al configurar credenciales: {e}")
        st.stop()

def get_sheet(sheet_name):
    client = get_client()
    return client.open(sheet_name)

def obtener_siguiente_id(worksheet_name, id_column_name="id"):
    try:
        sheet = get_sheet("Consultorio")
        ws = sheet.worksheet(worksheet_name)
        data = ws.get_all_records()
        if not data: return 1
        ids = [int(row[id_column_name]) for row in data if str(row[id_column_name]).isdigit()]
        return max(ids) + 1 if ids else 1
    except: return 1
