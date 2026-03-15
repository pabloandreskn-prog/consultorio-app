import streamlit as st
import pandas as pd
from datetime import datetime
from data.sheets_client import get_sheet

def obtener_siguiente_id(pagos_ws):
    """Busca el primer número disponible (rellena huecos) o sigue la secuencia."""
    try:
        datos = pagos_ws.get_all_records()
        if not datos:
            return 1
        
        ids_existentes = []
        for d in datos:
            try:
                ids_existentes.append(int(d.get("id_pago", 0)))
            except:
                continue
        
        if not ids_existentes:
            return 1
            
        ids_existentes.sort()
        
        for i in range(1, max(ids_existentes) + 1):
            if i not in ids_existentes:
                return i
        
        return max(ids_existentes) + 1
    except:
        return 1

def pagos_ui():
    st.subheader("💰 Registro de Pagos")
    
    try:
        sheet = get_sheet("Consultorio")
        turnos_data = sheet.worksheet("turnos").get_all_records()
        
        dict_pacientes = {t["nombre_paciente"]: t["id_paciente"] for t in turnos_data if t.get("nombre_paciente")}
        dict_servicios = {t["nombre_paciente"]: t["id_servicio"] for t in turnos_data if t.get("nombre_paciente")}
        
        lista_pacientes = sorted(list(dict_pacientes.keys()))
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return

    with st.form("form_nuevo_pago", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            paciente_sel = st.selectbox("Seleccione Paciente", lista_pacientes)
            monto = st.number_input("Monto abonado ($)", min_value=0, step=1000)
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Débito", "Crédito"])
        with col2:
            # CAMBIO QUIRÚRGICO: Sustituimos el selectbox de mes por calendario
            fecha_cobro_dt = st.date_input("Fecha de Cobro", datetime.now())
            nota = st.text_input("Nota / Concepto (Opcional)")

        submitted = st.form_submit_button("💾 Guardar Pago")

        if submitted and monto > 0:
            try:
                pagos_ws = sheet.worksheet("pagos")
                nuevo_id = obtener_siguiente_id(pagos_ws)
                
                # Extraemos el mes en formato YYYY-MM para las estadísticas
                mes_estadistica = fecha_cobro_dt.strftime("%Y-%m")
                
                nueva_fila = [
                    nuevo_id,                                    # id_pago
                    fecha_cobro_dt.strftime("%Y-%m-%d"),         # fecha de cobro elegida
                    mes_estadistica,                             # mes (para dashboard/stats)
                    paciente_sel,                                # paciente
                    float(monto),                                # monto
                    metodo,                                      # metodo
                    nota,                                        # observacion
                    dict_pacientes.get(paciente_sel, ""),        # id_paciente
                    dict_servicios.get(paciente_sel, "")         # id_servicio
                ]
                
                pagos_ws.append_row(nueva_fila)
                st.success(f"✅ Pago #{nuevo_id} registrado para {paciente_sel}")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    st.divider()
    st.markdown("### 📄 Últimos movimientos")
    try:
        pagos_raw = sheet.worksheet("pagos").get_all_records()
        if pagos_raw:
            # Mostramos los últimos 10 de forma descendente
            df_pagos = pd.DataFrame(pagos_raw)
            st.dataframe(df_pagos.tail(10).iloc[::-1], use_container_width=True)
    except: pass