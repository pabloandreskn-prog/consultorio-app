from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def generar_pdf_liquidacion(
    archivo: str,
    mes: str,
    resumen: dict,
    detalle_turnos: list[dict],
    definitivo: bool,
    salud: dict | None = None,
    riesgos: list[str] | None = None
):
    """
    Genera un PDF profesional de liquidación mensual
    """

    doc = SimpleDocTemplate(
        archivo,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    story = []

    # =========================
    # TÍTULO
    # =========================
    estado = "DEFINITIVO" if definitivo else "PROVISORIO"
    story.append(Paragraph(f"Liquidación mensual – {mes}", styles["Title"]))
    story.append(Paragraph(f"Estado: {estado}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # =========================
    # RESUMEN
    # =========================
    story.append(Paragraph("Resumen financiero", styles["Heading2"]))
    story.append(Paragraph(
        f"Total facturado: ${resumen['total_facturado']}", styles["Normal"]
    ))
    story.append(Paragraph(
        f"Participación del espacio: ${resumen['total_espacio']}", styles["Normal"]
    ))
    story.append(Paragraph(
        f"Neto profesional: ${resumen['neto_profesional']}", styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    # =========================
    # INSIGHTS FINANCIEROS
    # =========================
    if salud or riesgos:
        story.append(Paragraph("Insights financieros", styles["Heading2"]))

        if salud:
            story.append(Paragraph(
                f"Salud financiera: {salud.get('mensaje', '')}",
                styles["Normal"]
            ))

        if riesgos:
            story.append(Paragraph("Riesgos detectados:", styles["Normal"]))
            for r in riesgos:
                story.append(Paragraph(f"- {r}", styles["Normal"]))
        else:
            story.append(Paragraph(
                "No se detectaron riesgos financieros relevantes.",
                styles["Normal"]
            ))

        story.append(Spacer(1, 12))

    # =========================
    # TABLA DE TURNOS
    # =========================
    story.append(Paragraph("Detalle de turnos", styles["Heading2"]))

    tabla_data = [
        ["Fecha", "Paciente", "Servicio", "Precio", "Espacio", "Neto"]
    ]

    for f in detalle_turnos:
        tabla_data.append([
            f["fecha"],
            f["paciente"],
            f["servicio"],
            f"${f['precio']}",
            f"${f['espacio']}",
            f"${f['neto']}",
        ])

    tabla = Table(tabla_data, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    story.append(tabla)

    # =========================
    # GENERAR PDF
    # =========================
    doc.build(story)
