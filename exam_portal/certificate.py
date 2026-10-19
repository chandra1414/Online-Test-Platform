import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations()
            super().showPage()
        super().save()

    def draw_page_decorations(self):
        self.saveState()
        # Outer decorative frame
        width, height = landscape(letter)
        
        # Border
        self.setStrokeColor(colors.HexColor('#1E3A8A')) # Dark Navy
        self.setLineWidth(5)
        self.rect(20, 20, width - 40, height - 40)
        
        # Inner thin gold border
        self.setStrokeColor(colors.HexColor('#D97706')) # Amber / Gold
        self.setLineWidth(1.5)
        self.rect(26, 26, width - 52, height - 52)

        # Corner decorative accents
        self.setFillColor(colors.HexColor('#1E3A8A'))
        self.circle(35, 35, 5, fill=1, stroke=0)
        self.circle(width - 35, 35, 5, fill=1, stroke=0)
        self.circle(35, height - 35, 5, fill=1, stroke=0)
        self.circle(width - 35, height - 35, 5, fill=1, stroke=0)

        self.restoreState()


def generate_certificate_pdf(attempt, rank=1):
    """
    Generates a Certificate of Excellence / Achievement PDF using ReportLab in landscape orientation.
    Returns bytes buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1, # Center
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'CertSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#6B7280'),
        alignment=1,
        spaceAfter=15
    )

    presented_to_style = ParagraphStyle(
        'CertPresented',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#4B5563'),
        alignment=1,
        spaceAfter=8
    )

    name_style = ParagraphStyle(
        'CertName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=colors.HexColor('#111827'),
        alignment=1,
        spaceAfter=12
    )

    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=18,
        textColor=colors.HexColor('#374151'),
        alignment=1,
        spaceAfter=15
    )

    meta_style = ParagraphStyle(
        'CertMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1F2937'),
        alignment=1
    )

    cert_id_style = ParagraphStyle(
        'CertID',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#9CA3AF'),
        alignment=1
    )

    story = []
    story.append(Spacer(1, 10))
    story.append(Paragraph("CODEGEN ASSESSMENT & CODING PLATFORM", ParagraphStyle(
        'OrgHeader', fontName='Helvetica-Bold', fontSize=10, leading=12,
        textColor=colors.HexColor('#2563EB'), alignment=1, spaceAfter=8
    )))
    story.append(Paragraph("CERTIFICATE OF MERIT & EXCELLENCE", title_style))
    story.append(Paragraph("DASARA CODING COMPETITION 2026", subtitle_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph("This certificate is proudly awarded to", presented_to_style))
    
    student_name = attempt.student.user.get_full_name() or attempt.student.user.username
    story.append(Paragraph(f"<u>{student_name.upper()}</u>", name_style))
    
    story.append(Paragraph(
        f"Roll No: <b>{attempt.student.roll_number}</b> &nbsp;|&nbsp; College: <b>{attempt.student.college}</b>",
        meta_style
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        f"for outstanding technical proficiency in the examination <b>'{attempt.test.title}'</b>, "
        f"scoring <b>{attempt.score} / {attempt.total_possible} marks ({attempt.percentage}%)</b> "
        f"and achieving an impressive <b>Rank #{rank}</b> on the official platform leaderboard.",
        body_style
    ))

    story.append(Spacer(1, 20))

    # Signature and Verification Table
    date_str = attempt.completed_at.strftime('%B %d, %Y') if attempt.completed_at else 'N/A'
    
    sig_data = [
        [
            Paragraph(f"<b>Date of Examination:</b><br/>{date_str}", ParagraphStyle('T1', fontSize=10, alignment=0)),
            Paragraph("<b>Verified Platform Seal</b><br/>✓ Officially Validated", ParagraphStyle('T2', fontSize=10, alignment=1, textColor=colors.HexColor('#059669'))),
            Paragraph("<b>Academic Controller</b><br/>Director of Examinations", ParagraphStyle('T3', fontSize=10, alignment=2))
        ]
    ]
    t = Table(sig_data, colWidths=[200, 200, 200])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t)

    story.append(Spacer(1, 15))
    story.append(Paragraph(f"Certificate Verification UUID: {str(attempt.id)}", cert_id_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
