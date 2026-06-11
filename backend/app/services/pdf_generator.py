import io
import os
import tempfile
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_acknowledgement_pdf(complaint_data: dict, verification_url: str) -> io.BytesIO:
    # 1. Create bytes buffer
    buffer = io.BytesIO()
    
    # 2. Setup document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # 3. Custom styles for professional portal look
    title_style = ParagraphStyle(
        'PortalTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1e3a8a"),  # Indigo 900
        alignment=1  # Centered
    )
    
    subtitle_style = ParagraphStyle(
        'PortalSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#ea580c"),  # Orange 600
        alignment=1  # Centered
    )
    
    header_style = ParagraphStyle(
        'ReceiptHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),  # Slate 900
        alignment=1  # Centered
    )
    
    label_style = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#475569")  # Slate 600
    )
    
    value_style = ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#0f172a")  # Slate 900
    )

    alert_style = ParagraphStyle(
        'AlertText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#ea580c"),
        alignment=1
    )
    
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b"),
        alignment=1
    )
    
    # 4. Header elements
    story.append(Paragraph("CYBER SATHI AI (CyberSathi-AI)", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Inspired by National Cyber Crime Reporting Portal", subtitle_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("ACKNOWLEDGEMENT RECEIPT", header_style))
    story.append(Spacer(1, 15))
    
    # 5. Generate QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(verification_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1e3a8a", back_color="white")
    
    # Save QR code to a temp file
    temp_dir = tempfile.gettempdir()
    qr_path = os.path.join(temp_dir, f"qr_{complaint_data['ack_number']}.png")
    qr_img.save(qr_path)
    
    # 6. Grid layout for details and QR code
    details_data = [
        [Paragraph("Acknowledgement Number:", label_style), Paragraph(complaint_data['ack_number'], value_style)],
        [Paragraph("Complaint Category:", label_style), Paragraph(complaint_data['category'], value_style)],
        [Paragraph("Subcategory:", label_style), Paragraph(complaint_data['subcategory'], value_style)],
        [Paragraph("Submission Date:", label_style), Paragraph(complaint_data['submission_date'], value_style)],
        [Paragraph("Current Status:", label_style), Paragraph(complaint_data['status'], value_style)],
        [Paragraph("Citizen Name:", label_style), Paragraph(complaint_data.get('victim_name') or "Anonymous", value_style)],
        [Paragraph("Mobile Number:", label_style), Paragraph(complaint_data.get('victim_mobile') or "Not Provided", value_style)],
        [Paragraph("Verification Link:", label_style), Paragraph(f"<link href='{verification_url}'>{verification_url}</link>", value_style)],
    ]
    
    details_table = Table(details_data, colWidths=[2.2*inch, 3.8*inch])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    
    # Create layout with Details on Left and QR Code on Right
    qr_flowable = Image(qr_path, width=1.3*inch, height=1.3*inch)
    
    layout_data = [
        [details_table, qr_flowable]
    ]
    
    layout_table = Table(layout_data, colWidths=[6.0*inch, 1.4*inch])
    layout_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (1, 0), (1, 0), 10),
    ]))
    
    story.append(layout_table)
    story.append(Spacer(1, 20))
    
    # 7. Description Box
    desc_title_style = ParagraphStyle(
        'DescTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a8a")
    )
    story.append(Paragraph("Complaint Description & Incidents", desc_title_style))
    story.append(Spacer(1, 6))
    
    desc_box_data = [[Paragraph(complaint_data.get('description') or "No description provided.", value_style)]]
    desc_table = Table(desc_box_data, colWidths=[7.4*inch])
    desc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(desc_table)
    story.append(Spacer(1, 20))
    
    # 8. Important Notice
    notice_text = (
        "IMPORTANT NOTICE: This is an automatically generated acknowledgement receipt of your online complaint. "
        "The details are forwarded to respective Law Enforcement Agencies for necessary investigation. "
        "Please retain the Acknowledgement Number for any future communications."
    )
    story.append(Paragraph(notice_text, alert_style))
    story.append(Spacer(1, 30))
    
    # 9. Signatures
    sig_data = [
        ["", "Authorized Signature / QR Verified"],
        ["", "CyberSathi Cell (CyberSathi-AI)"]
    ]
    sig_table = Table(sig_data, colWidths=[4.9*inch, 2.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 30))
    
    # 10. Footer info
    story.append(Paragraph("Note: This document does not require a physical signature if QR code matches portal verification record.", footer_style))
    
    # Build PDF
    doc.build(story)
    
    # Clean up QR code temp file
    try:
        if os.path.exists(qr_path):
            os.remove(qr_path)
    except Exception:
        pass
        
    buffer.seek(0)
    return buffer
