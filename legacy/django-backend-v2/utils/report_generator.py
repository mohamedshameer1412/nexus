import os
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

def generate_diagnostic_report_pdf(user, profile, stats):
    """
    Generate an enterprise-quality PDF report for the diagnostic test results.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center
    title_style.textColor = colors.HexColor('#1e40af')  # Admin blue

    subtitle_style = styles['Heading2']
    subtitle_style.textColor = colors.HexColor('#4b5563')

    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.leading = 14

    stats_style = ParagraphStyle(
        'Stats',
        # removed parent connection
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e40af'),
        alignment=1
    )

    stats_label_style = ParagraphStyle(
        'StatsLabel',
        # removed parent connection
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        alignment=1
    )
    
    elements = []

    # --- Header ---
    elements.append(Paragraph("Diagnostic Test Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"For: {user.get_full_name() or user.username}", subtitle_style))
    elements.append(Paragraph(f"Date: {stats['completed_at'].strftime('%B %d, %Y')}", normal_style))
    elements.append(Spacer(1, 0.5*inch))

    # --- Overview Section ---
    elements.append(Paragraph("Learning Profile Overview", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    overview_text = """
    Based on your diagnostic test performance, we have analyzed your learning DNA. 
    This report summarizes your current ability, learning speed, and other key metrics 
    that will help customize your learning experience.
    """
    elements.append(Paragraph(overview_text, normal_style))
    elements.append(Spacer(1, 0.3*inch))

    # --- Key Metrics Grid ---
    # Create a table for key metrics
    data = [
        [
            Paragraph(f"{stats['final_ability']}", stats_style), 
            Paragraph(f"{stats['accuracy']}%", stats_style), 
            Paragraph(f"{stats['learning_speed']}x", stats_style)
        ],
        [
            Paragraph("Ability Score", stats_label_style),
            Paragraph("Accuracy", stats_label_style),
            Paragraph("Learning Speed", stats_label_style)
        ]
    ]
    t = Table(data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f3f4f6')),
        ('GRID', (0,0), (-1,-1), 1, colors.white),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.4*inch))

    # --- Analysis Section ---
    elements.append(Paragraph("Detailed Analysis", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    analysis_data = [
        ['Metric', 'Score/Value', 'Analysis'],
        ['Recommended Level', stats['recommended_starting_level'], 'Suggested starting point for coursework'],
        ['Consistency', f"{int(stats['consistency_score']*100)}%", 'Stability of performance across questions'],
        ['Guessing Tendency', f"{int(stats['guessing_tendency']*100)}%", 'Likelihood of guessing on hard questions'],
        ['Total Questions', stats['total_questions'], 'Total items attempted'],
        ['Correct Answers', stats['correct_answers'], 'Successfully answered items']
    ]

    t2 = Table(analysis_data, colWidths=[2.0*inch, 1.5*inch, 3.5*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')]),
        ('topPadding', (0,1), (-1,-1), 8),
        ('bottomPadding', (0,1), (-1,-1), 8),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 0.4*inch))

    # Footer
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph("Generated by AI Learning Platform - Deep Aspects", stats_label_style))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

def send_diagnostic_report_email(user, profile, stats):
    """
    Send the diagnostic report via email with enterprise-grade HTML template.
    """
    pdf_content = generate_diagnostic_report_pdf(user, profile, stats)
    
    subject = f"Your Learning DNA Report - {user.get_full_name() or user.username}"
    
    # Enterprise HTML Template
    # Using inline styles for maximum email client compatibility
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Learning DNA Report</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f6f8; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            .header {{ background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); padding: 30px 20px; text-align: center; color: white; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 0.5px; }}
            .header p {{ margin: 5px 0 0; opacity: 0.9; font-size: 14px; }}
            .content {{ padding: 30px 20px; }}
            .greeting {{ font-size: 16px; margin-bottom: 20px; color: #1f2937; }}
            .card-grid {{ display: flex; gap: 15px; margin-bottom: 30px; }}
            .card {{ flex: 1; background-color: #f8fafc; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #e2e8f0; }}
            .card-value {{ display: block; font-size: 24px; font-weight: 800; color: #1e40af; margin-bottom: 5px; }}
            .card-label {{ display: block; font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }}
            .chart-section {{ margin: 30px 0; padding: 20px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }}
            .chart-bar {{ height: 24px; background-color: #e2e8f0; border-radius: 12px; margin-bottom: 15px; position: relative; overflow: hidden; }}
            .chart-fill {{ height: 100%; border-radius: 12px; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; color: white; font-size: 11px; font-weight: bold; transition: width 1s ease; }}
            .bar-label {{ font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 5px; display: flex; justify-content: space-between; }}
            .btn-container {{ text-align: center; margin-top: 30px; margin-bottom: 20px; }}
            .btn {{ display: inline-block; padding: 12px 24px; background-color: #1e40af; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; transition: background-color 0.2s; }}
            .btn:hover {{ background-color: #1e3a8a; }}
            .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
            .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
            .badge-easy {{ background-color: #dcfce7; color: #166534; }}
            .badge-medium {{ background-color: #dbeafe; color: #1e40af; }}
            .badge-hard {{ background-color: #fee2e2; color: #991b1b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Learning DNA Report</h1>
                <p>Diagnostic Test Results & Analysis</p>
            </div>
            
            <div class="content">
                <div class="greeting">
                    <strong>Hello {user.get_full_name() or user.username},</strong>
                    <p>We've analyzed your diagnostic test results. Here is your personalized learning profile breakdown.</p>
                </div>

                <div class="card-grid">
                    <div class="card">
                        <span class="card-value">{stats['final_ability']}</span>
                        <span class="card-label">Ability Score</span>
                    </div>
                    <div class="card">
                        <span class="card-value">{stats['learning_speed']}x</span>
                        <span class="card-label">Learning Speed</span>
                    </div>
                </div>

                <!-- Simulating Charts with HTML/CSS Progress Bars -->
                <div class="chart-section">
                    <h3 style="margin-top: 0; color: #334155; font-size: 16px; margin-bottom: 20px;">Performance Metrics</h3>
                    
                    <div class="bar-label">
                        <span>Accuracy</span>
                        <span>{stats['accuracy']}%</span>
                    </div>
                    <div class="chart-bar">
                        <div class="chart-fill" style="width: {min(stats['accuracy'], 100)}%; background: linear-gradient(90deg, #3b82f6, #2563eb);"></div>
                    </div>

                    <div class="bar-label">
                        <span>Consistency</span>
                        <span>{int(stats['consistency_score'] * 100)}%</span>
                    </div>
                    <div class="chart-bar">
                        <div class="chart-fill" style="width: {min(stats['consistency_score'] * 100, 100)}%; background: linear-gradient(90deg, #10b981, #059669);"></div>
                    </div>

                    <div class="bar-label">
                        <span>Guessing Tendency</span>
                        <span>{int(stats['guessing_tendency'] * 100)}%</span>
                    </div>
                    <div class="chart-bar">
                        <div class="chart-fill" style="width: {min(stats['guessing_tendency'] * 100, 100)}%; background: linear-gradient(90deg, #f59e0b, #d97706);"></div>
                    </div>
                </div>

                <div style="background-color: #f0f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #0ea5e9;">
                    <h4 style="margin: 0 0 5px 0; color: #0369a1;">Recommended Starting Level</h4>
                    <p style="margin: 0; color: #0c4a6e; font-size: 14px;">
                        Based on your profile, we recommend starting at the <strong>{stats['recommended_starting_level']}</strong> level to maximize your learning efficiency.
                    </p>
                </div>

                <div class="btn-container">
                    <p style="font-size: 13px; color: #64748b; margin-bottom: 15px;">A detailed PDF report is attached to this email.</p>
                </div>
            </div>

            <div class="footer">
                <p>&copy; {timezone.now().year} AI Learning Platform. All rights reserved.</p>
                <p>This is an automated message. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    email = EmailMessage(
        subject,
        html_content, # Use the HTML content here but email.body is usually text? 
        # Actually EmailMessage takes body as second arg. We need to set content_subtype to html.
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.content_subtype = "html" # Main content is now text/html
    email.attach('Learning_DNA_Report.pdf', pdf_content, 'application/pdf')
    email.send()

