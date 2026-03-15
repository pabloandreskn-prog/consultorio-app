import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_client():
    # Intentar obtener la sección de secretos
    if "gcp_service_account" not in st.secrets:
        st.error("Faltan las credenciales 'gcp_service_account' en los Secrets de Streamlit.")
        st.stop()
        
    info = dict(st.secrets["gcp_service_account"])
    
    # Arreglar posibles errores de formato en la llave privada
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet(sheet_name):
    client = get_client()
    return client.open(sheet_name)import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_client():
    # Intentar obtener la sección de secretos
    if "gcp_service_account" not in st.secrets:
        st.error("Faltan las credenciales 'gcp_service_account' en los Secrets de Streamlit.")
        st.stop()
        
    info = dict(st.secrets["gcp_service_account"])
    
    # Arreglar posibles errores de formato en la llave privada
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet(sheet_name):
    client = get_client()
    return client.open(sheet_name)
