def obtener_plan_activo(id_paciente, id_servicio, planes_pacientes):
    for plan in planes_pacientes:
        if (
            plan["id_paciente"] == id_paciente
            and plan["id_servicio"] == id_servicio
            and plan["estado"] == "ACTIVO"
        ):
            return plan
    return None

def calcular_valor_sesion(df_servicios, id_servicio):
    servicio = df_servicios[df_servicios["id_servicio"] == id_servicio].iloc[0]
    return servicio["precio"] / servicio["sesiones"]


def procesar_turno_asistido(turno, df_planes, df_servicios):
    plan = obtener_plan_activo(
        df_planes,
        turno["id_paciente"],
        turno["id_servicio"]
    )

    if plan is None:
        return None

    valor_sesion = calcular_valor_sesion(df_servicios, turno["id_servicio"])

    idx = df_planes["id_plan_paciente"] == plan["id_plan_paciente"]

    df_planes.loc[idx, "sesiones_usadas"] += 1

    sesiones_usadas = df_planes.loc[idx, "sesiones_usadas"].iloc[0]
    sesiones_totales = plan["sesiones_totales"]

    if sesiones_usadas >= sesiones_totales:
        df_planes.loc[idx, "estado"] = "CERRADO"

    return valor_sesion

def consumir_sesion_plan(plan):
    plan["sesiones_usadas"] = int(plan["sesiones_usadas"]) + 1
    """
    Consume 1 sesión de un plan activo si quedan sesiones.
    Retorna True si se consumió, False si no había sesiones.
    """

    for plan in planes_pacientes:
        if (
            plan["id_paciente"] == id_paciente
            and plan["id_servicio"] == id_servicio
            and plan["estado"] == "ACTIVO"
        ):
            sesiones_usadas = int(plan.get("sesiones_usadas", 0))
            sesiones_totales = int(plan.get("sesiones_totales", 0))

            if sesiones_usadas < sesiones_totales:
                plan["sesiones_usadas"] = sesiones_usadas + 1
                return True

    return False


def guardar_planes(ws_planes, df_planes):
    ws_planes.clear()
    ws_planes.append_row(df_planes.columns.tolist())
    ws_planes.append_rows(df_planes.values.tolist())
