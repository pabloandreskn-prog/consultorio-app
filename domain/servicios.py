import uuid

def nuevo_servicio(categoria, nombre, duracion_min, precio_base):
    return {
        "id_servicio": str(uuid.uuid4()),
        "categoria": categoria,
        "nombre": nombre,
        "duracion_min": duracion_min,
        "precio_base": precio_base,
        "activo": True
    }
