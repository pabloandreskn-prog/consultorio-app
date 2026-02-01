from statistics import mean
from datetime import datetime


# ======================================================
# 1️⃣ SALUD FINANCIERA DEL MES
# ======================================================
def evaluar_salud_mes(total_facturado, total_cobrado):
    if total_facturado == 0:
        return {
            "nivel": "gris",
            "mensaje": "ℹ️ No hay facturación registrada este mes."
        }

    ratio = total_cobrado / total_facturado

    if ratio >= 0.95:
        return {
            "nivel": "verde",
            "mensaje": "✅ Mes financieramente saludable. Excelente nivel de cobranza."
        }
    elif ratio >= 0.85:
        return {
            "nivel": "amarillo",
            "mensaje": "🟡 Cobranza aceptable, pero con margen de mejora."
        }
    else:
        return {
            "nivel": "rojo",
            "mensaje": "🔴 Riesgo financiero: nivel de cobranza bajo."
        }


# ======================================================
# 2️⃣ DETECCIÓN DE RIESGOS FINANCIEROS
# ======================================================
def detectar_riesgos(total_facturado, total_cobrado, diferencia):
    riesgos = []

    if total_facturado > 0:
        ratio = total_cobrado / total_facturado

        if ratio < 0.85:
            riesgos.append(
                "⚠️ Se cobró menos del 85% de lo facturado. Revisar pagos pendientes."
            )

    if diferencia > 0:
        riesgos.append(
            "📉 Existe una diferencia pendiente entre facturado y cobrado."
        )

    return riesgos


# ======================================================
# 3️⃣ PROYECCIÓN DE CIERRE DE MES
# ======================================================
def proyectar_cierre_mes(turnos, mes):
    montos = []

    for t in turnos:
        if not t.get("fecha", "").startswith(mes):
            continue
        if t.get("estado") != "ASISTIÓ":
            continue
        try:
            montos.append(float(t.get("precio", 0)))
        except ValueError:
            continue

    if not montos:
        return None

    hoy = datetime.today()
    dias_transcurridos = hoy.day
    dias_mes = 30  # aproximado (suficiente para gestión)

    promedio_diario = sum(montos) / dias_transcurridos
    proyeccion = promedio_diario * dias_mes

    return round(proyeccion, 2)


# ======================================================
# 4️⃣ INGRESO PROMEDIO POR TURNO
# ======================================================
def ingreso_promedio_por_turno(filas_detalle):
    if not filas_detalle:
        return 0

    return round(
        mean(f["neto"] for f in filas_detalle),
        2
    )


# ======================================================
# 5️⃣ PARTICIPACIÓN DEL ESPACIO
# ======================================================
def participacion_espacio(filas_detalle):
    if not filas_detalle:
        return {
            "porcentaje": 0,
            "monto": 0
        }

    total_bruto = sum(f["precio"] for f in filas_detalle)
    total_espacio = sum(f["espacio"] for f in filas_detalle)

    if total_bruto == 0:
        return {
            "porcentaje": 0,
            "monto": total_espacio
        }

    return {
        "porcentaje": round((total_espacio / total_bruto) * 100, 2),
        "monto": round(total_espacio, 2)
    }

# =========================
# 6️⃣ Alertas con acciones sugeridas
# =========================
def generar_alertas_accionables(
    salud: dict,
    riesgos: list[str]
) -> list[dict]:

    alertas = []

    if salud["nivel"] == "rojo":
        alertas.append({
            "nivel": "rojo",
            "mensaje": "La salud financiera es crítica.",
            "accion": "Revisar cobranzas, políticas de pago y turnos no cobrados."
        })

    if salud["nivel"] == "amarillo":
        alertas.append({
            "nivel": "amarillo",
            "mensaje": "Hay cobranzas pendientes.",
            "accion": "Enviar recordatorios de pago y reforzar cobro en el día."
        })

    for r in riesgos:
        if "pendientes" in r.lower():
            alertas.append({
                "nivel": "amarillo",
                "mensaje": r,
                "accion": "Identificar pacientes con deuda y contactar."
            })

        if "inferior al 80%" in r.lower():
            alertas.append({
                "nivel": "rojo",
                "mensaje": r,
                "accion": "Revisar modalidad de cobro y anticipos."
            })

    return alertas

# =========================
# 7️⃣ Rentabilidad por servicio
# =========================
def rentabilidad_por_servicio(filas_detalle: list[dict]) -> dict:
    servicios = {}

    for f in filas_detalle:
        nombre = f["servicio"]
        servicios.setdefault(nombre, {
            "facturado": 0,
            "neto": 0,
            "espacio": 0,
            "turnos": 0
        })

        servicios[nombre]["facturado"] += f["precio"]
        servicios[nombre]["neto"] += f["neto"]
        servicios[nombre]["espacio"] += f["espacio"]
        servicios[nombre]["turnos"] += 1

    return servicios
