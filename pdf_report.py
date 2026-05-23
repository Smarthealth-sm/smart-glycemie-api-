import matplotlib.pyplot as plt
from reportlab.platypus import (
    Image,
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime


def generate_pdf(
    values,
    avg,
    max_val,
    min_val,
    score_ia,
    interpretation,
    reco,
    patient_info,
    summary_text="",
report_name="rapport"
):
    date_formatee = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    nom_fichier = f"pdfs/{patient_info['email']}_{report_name}.pdf"

    doc = SimpleDocTemplate(nom_fichier)
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=18,
        alignment=1
    )

    style_section = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor("#0C254A")
    )

    style_text = ParagraphStyle(
        'Text',
        parent=styles['Normal'],
        fontSize=10,
        leading=18
    )

    content = []

    # =========================
    # TITRE
    # =========================
    content.append(Paragraph("SMART GLYCÉMIE MONITOR", style_title))
    content.append(Spacer(1, 10))

    content.append(HRFlowable(
        width="100%",
        thickness=1.5,
        color=colors.HexColor("#0C254A")
    ))

    content.append(Spacer(1, 15))

    # =========================
    # DATE + TYPE
    # =========================
    date_now = datetime.now().strftime("%d/%m/%Y %H:%M")

    content.append(Paragraph("Informations du rapport", style_section))

    report_table = Table([
        ["Date :", date_now],
        ["Type d’analyse :", "Diagnostic global glycémique"]
    ], colWidths=[2 * inch, 4 * inch])

    content.append(report_table)
    content.append(Spacer(1, 20))

    # =========================
    # INFOS PATIENT
    # =========================
    content.append(Paragraph("Coordonnées et informations patient", style_section))

    patient_text = f"""
        <b>Sexe :</b> {patient_info["sexe"]}<br/>
        <b>Âge :</b> {patient_info["age"]} ans<br/>
        <b>BMI :</b> {patient_info["bmi"]}<br/>
        <b>Grossesses :</b> {patient_info["grossesses"]}<br/>
        <b>Diabétique :</b> {patient_info["diabetique"]}<br/>
        <b>Email :</b> {patient_info["email"]}<br/>
        <b>Téléphone :</b> {patient_info["telephone"]}
        """

    content.append(Paragraph(patient_text, style_text))
    content.append(Spacer(1, 20))
    content.append(Spacer(1, 20))

    # =========================
    # INDICATEURS
    # =========================
    content.append(Paragraph("Indicateurs ", style_section))
    hypo_count = len([v for v in values if v < 70])
    hyper_count = len([v for v in values if v > 180])
    stats_table = Table([
    ["Indicateur", "Valeur"],
    ["Moyenne", f"{avg:.2f} mg/dL"],
    ["Maximum", f"{max_val} mg/dL"],
    ["Minimum", f"{min_val} mg/dL"],
    ["Nombre de jours", len(values)],
    ["Hypoglycémies (< 70 mg/dL)", hypo_count],
    ["Hyperglycémies (> 180 mg/dL)", hyper_count]
        ], colWidths=[3 * inch, 3 * inch])

    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0C254A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))

    content.append(stats_table)
    content.append(Spacer(1, 20))

    # =========================
    # IA
    # =========================
    content.append(Paragraph("Analyse par IA", style_section))

    # calcul état global
    if avg < 70:
      etat_global = "RISQUE D’HYPOGLYCÉMIE CHRONIQUE"
    elif avg <= 140:
       etat_global = "ÉQUILIBRE GLYCÉMIQUE SATISFAISANT"
    elif avg <= 180:
       etat_global = "HYPERGLYCÉMIE MODÉRÉE"
    else:
       etat_global = "INSTABILITÉ GLYCÉMIQUE SÉVÈRE"

    ia_text = f"""
    <b>Score de risque :</b> {score_ia*100:.2f}%<br/>
    <b>Interprétation IA :</b> {interpretation}<br/>
    <b>État global :</b> {etat_global}
    """

    content.append(Paragraph(ia_text, style_text))
    content.append(Spacer(1, 20))

    # =========================
    # GRAPHE
    # =========================
    content.append(PageBreak())
    content.append(Paragraph("Graphe glycémique", style_section))

    plt.figure(figsize=(8, 4))
    plt.plot(values, marker='o')
    plt.axhline(70, linestyle='--')
    plt.axhline(180, linestyle='--')
    plt.title("Suivi glycémique")
    plt.xlabel("Jours")
    plt.ylabel("mg/dL")
    plt.grid(True)

    plt.savefig("graph.png", dpi=300, bbox_inches='tight')
    plt.close()

    content.append(Image("graph.png", width=450, height=220))
    content.append(Spacer(1, 20))

    # =========================
    # DIAGNOSTIC
    # =========================
    content.append(Paragraph("Diagnostic médical", style_section))

    diagnostic = f"""
    Le profil glycémique montre une évolution nécessitant
    une surveillance régulière du patient.

    Résultat IA : {interpretation}
    """

    content.append(Paragraph(diagnostic, style_text))
    content.append(Spacer(1, 20))

    # =========================
    # RECOMMANDATIONS
    # =========================
    content.append(Paragraph("Recommandations", style_section))

    recommendation = f"""
    • {reco}<br/>
    • Maintenir le suivi quotidien<br/>
    • Contrôle alimentaire<br/>
    • Consultation médicale en cas de pics répétés
    """

    recommendation_block = Table(
    [[Paragraph(recommendation, style_text)]],
    colWidths=[6 * inch]
)

    recommendation_block.setStyle(TableStyle([
    ('BOX', (0, 0), (-1, -1), 1.2, colors.red),
    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FDEDEC")),
    ('PADDING', (0, 0), (-1, -1), 12),
]))

    content.append(recommendation_block)

    doc.build(content)

    return nom_fichier