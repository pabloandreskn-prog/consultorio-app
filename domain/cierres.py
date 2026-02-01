def mes_esta_cerrado(cierres, mes):
    """
    cierres: lista de dicts desde Google Sheets
    mes: string 'YYYY-MM'
    """
    for c in cierres:
        if c["mes"] == mes and c["cerrado"] == "SI":
            return True
    return False
