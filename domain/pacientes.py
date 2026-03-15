from datetime import datetime

# Agregamos id_numerico como parámetro
def nuevo_paciente(id_numerico, nombre, dni, telefono, tipo_cliente, observaciones=""):
    return {
        "id_paciente": id_numerico, # Ahora usa el número que le pasamos
        "nombre": nombre,
        "dni": dni,
        "telefono": telefono,
        "tipo_cliente": tipo_cliente,
        "fecha_alta": datetime.now().strftime("%Y-%m-%d"),
        "activo": True,
        "observaciones": observaciones
    }