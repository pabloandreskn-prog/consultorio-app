from datetime import datetime

def hay_solapamiento(turnos_existentes, fecha, inicio_nuevo, fin_nuevo):
    inicio_nuevo = datetime.strptime(inicio_nuevo, "%H:%M")
    fin_nuevo = datetime.strptime(fin_nuevo, "%H:%M")

    for t in turnos_existentes:
        if t["fecha"] != fecha:
            continue

        inicio_existente = datetime.strptime(t["hora_inicio"], "%H:%M")
        fin_existente = datetime.strptime(t["hora_fin"], "%H:%M")

        if inicio_nuevo < fin_existente and fin_nuevo > inicio_existente:
            return True

    return False
