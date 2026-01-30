import uuid
from datetime import datetime

def nuevo_pago(id_turno, monto, metodo, observaciones=""):
    return {
        "id_pago": str(uuid.uuid4()),
        "id_turno": id_turno,
        "fecha_pago": datetime.now().strftime("%Y-%m-%d"),
        "monto": monto,
        "metodo": metodo,
        "observaciones": observaciones
    }
