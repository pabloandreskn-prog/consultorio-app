import uuid
from datetime import datetime

def nuevo_paciente(nombre, dni, telefono, tipo_cliente, observaciones=""):
    return {
        "id_paciente": str(uuid.uuid4()),
        "nombre": nombre,
        "dni": dni,
        "telefono": telefono,
        "tipo_cliente": tipo_cliente,
        "fecha_alta": datetime.now().strftime("%Y-%m-%d"),
        "activo": True,
        "observaciones": observaciones
    }
