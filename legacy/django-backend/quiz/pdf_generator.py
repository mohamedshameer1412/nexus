"""
PDF Report Generator for Quiz Results
Uses ReportLab to create professional, secure PDF reports
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from io import BytesIO
from datetime import datetime


class QuizReportGenerator:
    """Generate professional PDF reports for quiz results"""
    
    def __init__(self, session_data):
        """
        Initialize report generator with session data
        
        Args:
            session_data: Dictionary containing quiz session information
        """
        self.session_data = session_data
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # Section heading style
        self.section_style = ParagraphStyle(
            'SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#3b82f6'),
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=8,
            fontName='Helvetica'
        )
        
    def _create_header(self):
        """Create report header"""
        elements = []
        
        # Platform branding
        elements.append(Paragraph("ADAPTIVE AI QUIZ PLATFORM", self.title_style))
        elements.append(Paragraph("Quiz Results Report", self.subtitle_style))
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_student_info_section(self):
        """Create student information section"""
        elements = []
        
        # Student info table
        data = [
            ['Student Name:', self.session_data.get('student_name', 'N/A')],
            ['Email:', self.session_data.get('student_email', 'N/A')],
            ['Quiz Title:', self.session_data.get('quiz_title', 'N/A')],
            ['Date Taken:', self.session_data.get('completed_at', 'N/A')],
            ['Attempt Number:', str(self.session_data.get('attempt_number', 1))],
        ]
        
        table = Table(data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1'))
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.4*inch))
        
        return elements
    
    def _create_performance_summary(self):
        """Create performance summary section"""
        elements = []
        
        elements.append(Paragraph("Performance Summary", self.section_style))
        
        # Get score and determine color
        score = self.session_data.get('total_score', 0)
        if score >= 80:
            score_color = colors.HexColor('#22c55e')  # Green
        elif score >= 60:
            score_color = colors.HexColor('#eab308')  # Yellow
        else:
            score_color = colors.HexColor('#ef4444')  # Red
        
        # Performance metrics table
        data = [
            ['Overall Score', f"{score}%", f"Grade: {self._get_grade(score)}"],
            ['Accuracy', f"{self.session_data.get('accuracy', 0)}%", ''],
            ['Correct Answers', str(self.session_data.get('correct_answers', 0)), ''],
            ['Incorrect Answers', str(self.session_data.get('incorrect_answers', 0)), ''],
            ['Time Taken', f"{self.session_data.get('time_taken', 0)} minutes", ''],
            ['Avg Response Time', f"{self.session_data.get('avg_response_time', 0):.1f} seconds", ''],
        ]
        
        table = Table(data, colWidths=[2.5*inch, 2*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('SPAN', (1, 1), (2, 1)),
            ('SPAN', (1, 2), (2, 2)),
            ('SPAN', (1, 3), (2, 3)),
            ('SPAN', (1, 4), (2, 4)),
            ('SPAN', (1, 5), (2, 5)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_topic_performance_chart(self):
        """Create topic performance bar chart"""
        elements = []
        
        topic_data = self.session_data.get('topic_performance', [])
        if not topic_data:
            return elements
        
        elements.append(Paragraph("Topic Performance Breakdown", self.section_style))
        
        # Create bar chart
        drawing = Drawing(400, 200)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300
        
        # Prepare data
        topics = [item['topic'] for item in topic_data]
        scores = [item['accuracy'] for item in topic_data]
        
        chart.data = [scores]
        chart.categoryAxis.categoryNames = topics
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 100
        chart.valueAxis.valueStep = 20
        
        # Styling
        chart.bars[0].fillColor = colors.HexColor('#3b82f6')
        chart.categoryAxis.labels.angle = 45
        chart.categoryAxis.labels.fontSize = 8
        chart.valueAxis.labels.fontSize = 10
        
        drawing.add(chart)
        elements.append(drawing)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_proctoring_summary(self):
        """Create proctoring summary section"""
        elements = []
        
        # Only include if proctoring was enabled
        if not self.session_data.get('proctoring_enabled', False):
            return elements
        
        elements.append(Paragraph("Behavior & Integrity Summary", self.section_style))
        
        behavior_score = min(100, self.session_data.get('behavior_score', 100))
        
        # Determine integrity status
        if behavior_score >= 90:
            status = "Excellent"
            status_color = colors.HexColor('#22c55e')
        elif behavior_score >= 70:
            status = "Good"
            status_color = colors.HexColor('#eab308')
        else:
            status = "Needs Review"
            status_color = colors.HexColor('#ef4444')
        
        # Helper for metric ratings
        tabs = self.session_data.get('total_tab_switches', 0)
        hesitations = self.session_data.get('total_hesitations', 0)
        
        tab_rating = "Excellent" if tabs == 0 else "Good" if tabs < 5 else "Review"
        hesitation_rating = "Excellent" if hesitations == 0 else "Good" if hesitations < 5 else "Distracted"
        
        data = [
            ['Behavior Score', f"{behavior_score}/100", f"Rating: {status}"],
            ['Tab Switches', str(tabs), tab_rating],
            ['Hesitations', str(hesitations), hesitation_rating],
        ]
        
        table = Table(data, colWidths=[2.5*inch, 2*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_ai_insights(self):
        """Create AI insights section"""
        elements = []
        
        mindset = self.session_data.get('detected_mindset', 'N/A')
        recommendations = self.session_data.get('recommendations', [])
        
        if mindset == 'N/A' and not recommendations:
            return elements
        
        elements.append(Paragraph("AI-Powered Insights", self.section_style))
        
        # Mindset
        if mindset != 'N/A':
            mindset_text = f"<b>Detected Learning Mindset:</b> {mindset}"
            elements.append(Paragraph(mindset_text, self.body_style))
            elements.append(Spacer(1, 0.1*inch))
        
        # Recommendations
        if recommendations:
            elements.append(Paragraph("<b>Recommendations for Improvement:</b>", self.body_style))
            elements.append(Spacer(1, 0.05*inch))
            for rec in recommendations[:5]:  # Up to 5 recommendations
                # Add a bullet point with wrapping
                elements.append(Paragraph(f"• {rec}", self.body_style))
                elements.append(Spacer(1, 0.1*inch)) # Extra space between recommendations
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_footer(self):
        """Create report footer"""
        elements = []
        
        # Disclaimer
        disclaimer = (
            "<i>This is an automatically generated report from the Adaptive AI Quiz Platform. "
            "The scores and insights are based on the student's performance during the quiz session. "
            f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}.</i>"
        )
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#94a3b8'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(disclaimer, footer_style))
        
        # Session ID for verification
        session_id = self.session_data.get('session_id', 'N/A')
        verification = f"Session ID: {session_id}"
        elements.append(Paragraph(verification, footer_style))
        
        return elements
    
    def _get_grade(self, score):
        """Convert score to letter grade"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def generate(self):
        """Generate the complete PDF report"""
        # Create document
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        elements = []
        
        # Add all sections
        elements.extend(self._create_header())
        elements.extend(self._create_student_info_section())
        elements.extend(self._create_performance_summary())
        elements.extend(self._create_topic_performance_chart())
        elements.extend(self._create_proctoring_summary())
        elements.extend(self._create_ai_insights())
        elements.extend(self._create_footer())
        
        # Build PDF
        doc.build(elements)
        
        # Return buffer
        self.buffer.seek(0)
        return self.buffer


def generate_quiz_report_pdf(session_data):
    """
    Convenience function to generate a quiz report PDF
    
    Args:
        session_data: Dictionary containing quiz session data
        
    Returns:
        BytesIO buffer containing the PDF
    """
    generator = QuizReportGenerator(session_data)
    return generator.generate()
