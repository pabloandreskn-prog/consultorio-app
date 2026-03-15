import streamlit as st

from datetime import date, timedelta

from domain.cierres import mes_esta_cerrado

from domain.agenda_logic import (

    marcar_turno_asistio, 

    marcar_turno_cancelado,

    contar_sesiones_realizadas,

    obtener_alerta_renovacion,

    crear_entrada_plan,

    actualizar_contador_plan  # Asegúrate de tenerla en agenda_logic.py

)



# =========================
# HELPERS
# =========================

def generar_horarios():

    return [f"{h:02d}:00" for h in range(8, 21)]

def siguiente_id_turno(turnos):
    ids = [int(t["id_turno"]) for t in turnos if str(t.get("id_turno")).isdigit()]
    return max(ids) + 1 if ids else 1

def extraer_sesiones(nombre_servicio):
    numeros = "".join(filter(str.isdigit, nombre_servicio))
    return int(numeros) if numeros else 1



def generar_fechas_plan(fecha_inicio, d_semana, sesiones):
    fechas = []
    fecha = fecha_inicio
    while len(fechas) < sesiones:
        if fecha.weekday() in d_semana:
            fechas.append(fecha)
        fecha += timedelta(days=1)

    return fechas



def sesiones_acumuladas(id_paciente, id_servicio, planes_pacientes):
    """Busca asistencias y totales en la lista de planes."""
    for plan in planes_pacientes:

        p_id_match = str(plan.get("id_paciente")) == str(id_paciente)
        s_id_match = str(plan.get("id_servicio")) == str(id_servicio)
        es_activo = str(plan.get("estado", "")).upper() == "ACTIVO"
        

        if p_id_match and s_id_match and es_activo:
            return (
                int(plan.get("sesiones_usadas", 0)), 
                int(plan.get("sesiones_totales", 0))
            )
    return 0, 0


# =========================
# AGENDA UI
# =========================

def agenda_ui(sheet, pacientes, servicios, planes_pacientes):

    st.title("📅 Agenda")

    # --- GESTIÓN DE CACHÉ ---

    if "ws_turnos" not in st.session_state:

        st.session_state.ws_turnos = sheet.worksheet("turnos")

    if "ws_cierres" not in st.session_state:

        st.session_state.ws_cierres = sheet.worksheet("cierres")

    if "ws_planes" not in st.session_state:

        st.session_state.ws_planes = sheet.worksheet("planes_pacientes")



    # Recarga de datos desde Google Sheets si no están en caché

    if "turnos" not in st.session_state:

        st.session_state.turnos = st.session_state.ws_turnos.get_all_records()

    if "cierres" not in st.session_state:

        st.session_state.cierres = st.session_state.ws_cierres.get_all_records()

    if "planes_pacientes" not in st.session_state:

        st.session_state.planes_pacientes = st.session_state.ws_planes.get_all_records()



    turnos = st.session_state.turnos

    cierres = st.session_state.cierres

    planes_actuales = st.session_state.planes_pacientes



    # --- VISTA DEL DÍA ---

    fecha_vista = st.date_input("📅 Ver agenda del día", value=date.today())

    mes_actual = fecha_vista.strftime("%Y-%m")



    turnos_dia = [(i + 2, t) for i, t in enumerate(turnos) if t.get("fecha") == str(fecha_vista)]



    st.subheader("🟩 Turnos del día")



    if turnos_dia:

        cols = st.columns(4)

        for i, (_, t) in enumerate(turnos_dia):

            # Usamos los planes frescos de la sesión

            usadas, totales = sesiones_acumuladas(t["id_paciente"], t["id_servicio"], planes_actuales)

            with cols[i % 4]:

                st.markdown(

                    f"""

                    <div style="background: rgba(96,176,103,0.18); padding: 14px; border-radius: 14px; 

                         border: 1px solid rgba(96,176,103,0.45); margin-bottom: 12px;">

                        <b>🕒 {t['hora']}</b><br>

                        <span>{t['nombre_paciente']}</span><br>

                        <small>{t['nombre_servicio']}</small><br>

                        <small>📊 {usadas}/{totales} sesiones</small>

                    </div>

                    """, unsafe_allow_html=True

                )

    else:

        st.info("No hay turnos para este día")



    # --- FORMULARIO NUEVO TURNO ---

    st.markdown("---")

    st.subheader("➕ Crear turno / plan")



    pacientes_dict = {p["nombre"]: p for p in pacientes}

    servicios_dict = {s["nombre"]: s for s in servicios}

    dias_opciones = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5}



    with st.form("nuevo_turno"):

        fecha_ini = st.date_input("📅 Fecha de inicio", value=fecha_vista)

        c1, c2, c3 = st.columns(3)

        p_nombre = c1.selectbox("Paciente", pacientes_dict.keys())

        s_nombre = c2.selectbox("Servicio", servicios_dict.keys())

        h_turno = c3.selectbox("Hora", generar_horarios())



        servicio_obj = servicios_dict[s_nombre]

        cant_sesiones = extraer_sesiones(servicio_obj["nombre"])

        es_plan = cant_sesiones > 1



        dias_seleccionados = []

        if es_plan:

            st.markdown("### 📆 Configuración del PLAN")

            dias_seleccionados = st.multiselect("Días fijos", options=dias_opciones.keys())



        crear = st.form_submit_button("🟢 Crear turnos")



        if crear:

            paciente_obj = pacientes_dict[p_nombre]

            if es_plan:

                crear_entrada_plan(sheet, paciente_obj, servicio_obj, cant_sesiones, fecha_ini)

                if "planes_pacientes" in st.session_state: del st.session_state.planes_pacientes



            if es_plan and dias_seleccionados:

                dias_nums = [dias_opciones[d] for d in dias_seleccionados]

                fechas_lista = generar_fechas_plan(fecha_ini, dias_nums, cant_sesiones)

            else:

                fechas_lista = [fecha_ini]



            id_t = siguiente_id_turno(turnos)

            for f in fechas_lista:

                st.session_state.ws_turnos.append_row([

                    id_t, str(f), h_turno, paciente_obj["id_paciente"], paciente_obj["nombre"],

                    paciente_obj.get("condicion", "GENERAL"), servicio_obj["id_servicio"],

                    servicio_obj["nombre"], "RESERVADO", "", ""

                ])

                id_t += 1



            if "turnos" in st.session_state: del st.session_state.turnos

            st.rerun()



    # --- OPERACIÓN DEL DÍA ---

    st.markdown("---")

    st.subheader("📋 Operación del día")



    for fila, t in turnos_dia:

        estado_act = t.get("estado", "RESERVADO")

        

        # Obtenemos datos del plan para la fila actual

        usadas_r, t_plan = sesiones_acumuladas(t["id_paciente"], t["id_servicio"], planes_actuales)



        alerta_msg = obtener_alerta_renovacion(usadas_r, t_plan, t["nombre_servicio"])

        if alerta_msg and estado_act == "RESERVADO":

            st.warning(alerta_msg)



        col1, col2, col3, col4, col5 = st.columns([2, 3, 1.5, 1.5, 1.5])

        col1.write(f"🕒 {t['hora']}")

        col2.write(f"**{t['nombre_paciente']}**")

        col3.write(f"📊 {usadas_r}/{t_plan}")



        if estado_act == "ASISTIÓ":

            col4.markdown("✅ *Asistió*")

        elif estado_act == "CANCELADO":

            col4.markdown("❌ *Cancelado*")

        else:

            if col4.button("✔️", key=f"as_btn_{t['id_turno']}"):

                # 1. Marcar asistencia en Turnos

                marcar_turno_asistio(st.session_state.ws_turnos, fila, t, turnos)

                

                # 2. Actualizar contador en Planes si corresponde (IDs 4 y 5)

                if str(t["id_servicio"]) in ["4", "5"]:

                    actualizar_contador_plan(sheet, t["id_paciente"], t["id_servicio"])

                    # Borramos caché de planes para que al refrescar lea el nuevo valor

                    if "planes_pacientes" in st.session_state:

                        del st.session_state.planes_pacientes

                

                # 3. Limpiar caché de turnos y recargar

                if "turnos" in st.session_state: del st.session_state.turnos

                st.rerun()

            

            if col5.button("🚫", key=f"canc_btn_{t['id_turno']}"):

                marcar_turno_cancelado(st.session_state.ws_turnos, fila)

                if "turnos" in st.session_state: del st.session_state.turnos

                st.rerun()

