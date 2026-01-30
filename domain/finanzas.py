import pandas as pd

def resumen_financiero(turnos, pagos):
    df_turnos = pd.DataFrame(turnos)
    df_pagos = pd.DataFrame(pagos)

    pagos_sum = (
        df_pagos.groupby("id_turno")["monto"]
        .sum()
        .reset_index()
    )

    df = df_turnos.merge(pagos_sum, on="id_turno", how="left")
    df["monto"].fillna(0, inplace=True)

    df["deuda"] = df["precio"] - df["monto"]

    return df
