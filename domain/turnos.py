import uuid

def nuevo_turno(fecha, hora, id_paciente, nombre_paciente,
                id_servicio, nombre_servicio):
    return {
        "id_turno": str(uuid.uuid4()),
        "fecha": fecha,
        "hora": hora,
        "id_paciente": id_paciente,
        "nombre_paciente": nombre_paciente,
        "id_servicio": id_servicio,
        "nombre_servicio": nombre_servicio,
        "estado": "RESERVADO"
    }