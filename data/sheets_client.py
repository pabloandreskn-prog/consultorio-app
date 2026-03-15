import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource(show_spinner=False)
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_sheet(sheet_name: str):
    client = get_client()
    return client.open(sheet_name)

def obtener_siguiente_id(sheet_name: str, worksheet_name: str):
    try:
        sheet = get_sheet(sheet_name)
        ws = sheet.worksheet(worksheet_name)
        ids_col = ws.col_values(1)[1:]  
        ids_numericos = [int(val) for val in ids_col if str(val).strip().isdigit()]
        return max(ids_numericos) + 1 if ids_numericos else 1
    except Exception:
        return 1

def obtener_precio_servicio(id_servicio):
    """Busca el precio oficial en la pestaña 'servicios'"""
    try:
        sheet = get_sheet("Consultorio")
        srv_ws = sheet.worksheet("servicios")
        servicios = srv_ws.get_all_records()
        for s in servicios:
            if str(s['id_servicio']) == str(id_servicio):
                return float(s['precio'])
        return 0
    except:
        return 0

def registrar_venta_automatica(datos_venta):
    """Registra venta con precio automático y lógica de bonificación estricta"""
    try:
        sheet = get_sheet("Consultorio")
        ws_ventas = sheet.worksheet("ventas")
        id_v = obtener_siguiente_id("Consultorio", "ventas")
        
        id_s = datos_venta.get('id_servicio')
        precio_base = obtener_precio_servicio(id_s)
        
        # --- LÓGICA DE BONIFICACIÓN ESTRICTA ---
        # Solo se aplica descuento si es EVALUACIÓN (ID 1, 2, 3 según tu config)
        # Y si la condición lo requiere. Para Sesión Individual (ID 6, 7, 8) es PRECIO FULL.
        es_evaluacion = id_s in [1, 2, 3]
        monto_final = precio_base
        
        if es_evaluacion and datos_venta.get('bonificado') == "SI":
            # Aquí aplicas tu regla de descuento (ej: 50% o el monto que definas)
            monto_final = precio_base * 0.5 

        es_plan = id_s in [4, 5]
        sesiones_totales = 10 if id_s == 5 else (5 if id_s == 4 else 1)
        sesiones_usadas = 1 if not es_plan else 0
        estado = "FINALIZADO" if not es_plan else "ACTIVO"
        
        fila = [
            id_v, 
            datos_venta['fecha'], 
            datos_venta['fecha'][:7],
            datos_venta['id_paciente'],
            id_s,
            datos_venta['condicion_turno'],
            monto_final,
            "SI" if monto_final < precio_base else "NO",
            datos_venta.get('metodo_pago', 'Efectivo'),
            sesiones_totales,
            sesiones_usadas,
            estado,
            datos_venta.get('fecha_inicio_plan', datos_venta['fecha'])
        ]
        ws_ventas.append_row(fila)
        return id_v
    except Exception as e:
        st.error(f"Error en venta: {e}")
        return None

def obtener_deuda_paciente(id_paciente):
    """Calcula deuda real: Suma de monto_total en ventas - Suma de montos en pagos"""
    try:
        sheet = get_sheet("Consultorio")
        ventas = sheet.worksheet("ventas").get_all_records()
        pagos = sheet.worksheet("pagos").get_all_records()
        
        total_v = sum(float(v['monto_total']) for v in ventas if str(v['id_paciente']) == str(id_paciente))
        total_p = sum(float(p['monto']) for p in pagos if str(p['id_paciente']) == str(id_paciente))
        
        deuda = total_v - total_p
        return max(0, deuda) # No devuelve deudas negativas
    except:
        return 0