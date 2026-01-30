import uuid
from datetime import datetime, timedelta

def calcular_hora_fin(hora_inicio_str, duracion_min):
    hora_inicio = datetime.strptime(hora_inicio_str, "%H:%M")
    hora_fin = hora_inicio + timedelta(minutes=duracion_min)
    return hora_fin.strftime("%H:%M")

def nuevo_turno(fecha, hora_inicio, hora_fin, id_paciente, nombre_paciente,
                id_servicio, nombre_servicio):
    return {
        "id_turno": str(uuid.uuid4()),
        "fecha": fecha,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "id_paciente": id_paciente,
        "nombre_paciente": nombre_paciente,
        "id_servicio": id_servicio,
        "nombre_servicio": nombre_servicio,
        "estado": "RESERVADO"
    }
