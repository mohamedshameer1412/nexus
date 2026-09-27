"""
sih/reports.py - PDF generation for NEXUS SIH career evidence reports.
Maps to PS 26101 Section 7, Phase 8: "Promotion evidence report".
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def generate_career_evidence_report_pdf(user, profile, twin, record, domains):
    """
    Generate the officer's verified competency evidence report — the
    document a promotion committee would review in place of self-declared
    skills. Pulls straight from the Competency Digital Twin and Career
    Competency Record, both continuously updated by the diagnostic and
    learning pathway flows.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    title_style.textColor = colors.HexColor('#1e40af')

    subtitle_style = styles['Heading2']
    subtitle_style.textColor = colors.HexColor('#4b5563')

    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.leading = 15

    small_muted = ParagraphStyle('SmallMuted', fontSize=9, textColor=colors.HexColor('#6b7280'))

    stats_style = ParagraphStyle('Stats', fontSize=24, leading=28, textColor=colors.HexColor('#1e40af'), alignment=1)
    stats_label_style = ParagraphStyle('StatsLabel', fontSize=10, textColor=colors.HexColor('#6b7280'), alignment=1)

    elements = []

    elements.append(Paragraph("Verified Competency Evidence Report", title_style))
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(f"Officer: {user.get_full_name() or user.username}", subtitle_style))
    elements.append(Paragraph(f"Designation: {profile.designation or 'Not set'} &nbsp;|&nbsp; Department: {profile.department or 'Not set'}", normal_style))
    elements.append(Paragraph(f"Generated: {record.last_updated.strftime('%B %d, %Y')}", small_muted))
    elements.append(Spacer(1, 0.35 * inch))

    # --- Promotion readiness ---
    elements.append(Paragraph("Promotion Readiness", subtitle_style))
    elements.append(Spacer(1, 0.15 * inch))
    readiness = record.promotion_readiness or 0
    data = [
        [Paragraph(f"{readiness:.0f}%", stats_style), Paragraph(f"{twin.overall_competency_score:.0f}%", stats_style), Paragraph(f"{len(record.gaps_closed or [])}", stats_style)],
        [Paragraph("Promotion Readiness", stats_label_style), Paragraph("Overall Competency", stats_label_style), Paragraph("Gaps Closed", stats_label_style)],
    ]
    t = Table(data, colWidths=[2.3 * inch, 2.3 * inch, 2.3 * inch])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f3f4f6')),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(
        "Promotion ready" if record.next_role_ready else f"{max(80 - readiness, 0):.0f}% more needed for promotion readiness (target 80%)",
        normal_style
    ))
    elements.append(Spacer(1, 0.4 * inch))

    # --- Domain competency breakdown ---
    elements.append(Paragraph("Competency by Domain (Verified, not self-declared)", subtitle_style))
    elements.append(Spacer(1, 0.15 * inch))
    domain_rows = [['Domain', 'Verified score', 'Required for role']]
    for d in domains:
        domain_rows.append([d['name'], f"{d['score']:.0f}%", f"{d['required']:.0f}%"])
    t2 = Table(domain_rows, colWidths=[3.2 * inch, 1.6 * inch, 1.6 * inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 0.4 * inch))

    # --- Verified learning timeline ---
    elements.append(Paragraph("Verified Learning Timeline", subtitle_style))
    elements.append(Spacer(1, 0.15 * inch))
    history = list(reversed(record.assessment_history or []))[:15]
    if not history:
        elements.append(Paragraph("No learning history recorded yet.", normal_style))
    else:
        timeline_rows = [['Date', 'Activity', 'Domain']]
        for item in history:
            date_str = str(item.get('date', ''))[:10]
            timeline_rows.append([date_str, item.get('activity', ''), item.get('domain', '')])
        t3 = Table(timeline_rows, colWidths=[1.4 * inch, 4.0 * inch, 1.0 * inch])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        elements.append(t3)

    elements.append(Spacer(1, 0.6 * inch))
    elements.append(Paragraph(
        "This report is generated from the officer's Competency Digital Twin, which is updated after every "
        "assessment session. It replaces self-declaration with a verified, evidence-backed record for HR and "
        "promotion review, per PS 26101 (MoSPI / DIID).",
        small_muted
    ))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Generated by NEXUS — Agentic Learner Intelligence OS", small_muted))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
