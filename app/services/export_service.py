"""
app/services/export_service.py — Generate CSV, PDF, and JSON reports from scan data.
Extracted from route handlers into a dedicated service.
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger('xssniper')


def to_csv(scan: dict) -> bytes:
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(['Field', 'Value'])
    w.writerow(['Scan ID',         scan['id']])
    w.writerow(['Date',            scan['date']])
    w.writerow(['URL',             scan['url']])
    w.writerow(['Status',          scan['status']])
    w.writerow(['Vulnerabilities', scan['vulnerabilities']])
    w.writerow(['Duration',        scan['duration']])
    w.writerow([])
    w.writerow(['--- Scan Log ---'])
    for line in (scan.get('log_output') or '').split('\n'):
        if line.strip():
            w.writerow([line])
    return buf.getvalue().encode('utf-8')


def to_json(scan: dict) -> bytes:
    payload = {
        'scan_id':         scan['id'],
        'date':            scan['date'],
        'url':             scan['url'],
        'status':          scan['status'],
        'vulnerabilities': scan['vulnerabilities'],
        'duration':        scan['duration'],
        'log_output':      scan['log_output'],
    }
    return json.dumps(payload, indent=2).encode('utf-8')


def to_pdf(scan: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
    except ImportError:
        raise RuntimeError("PDF export requires 'reportlab'. Run: pip install reportlab")

    green   = colors.HexColor('#00cc66')
    grey    = colors.HexColor('#2a3340')
    ltgrey  = colors.HexColor('#8892a4')
    red_clr = colors.HexColor('#ff3b5c')

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Title'],
        fontSize=22, textColor=green, spaceAfter=4, fontName='Helvetica-Bold',
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        fontSize=10, textColor=ltgrey, spaceAfter=16,
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontSize=13, textColor=green, fontName='Helvetica-Bold',
        spaceBefore=14, spaceAfter=6,
    )
    mono_style = ParagraphStyle(
        'Mono', parent=styles['Code'],
        fontSize=7.5, textColor=colors.HexColor('#8fbc8f'),
        leading=11, fontName='Courier',
        backColor=colors.HexColor('#060d14'),
        leftIndent=6, rightIndent=6,
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=ltgrey, alignment=TA_CENTER,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    vuln_color = red_clr if (scan.get('vulnerabilities') or 0) > 0 else green

    meta_rows = [
        ['Scan ID',         str(scan['id'])],
        ['Date',            str(scan['date'])],
        ['Target URL',      str(scan['url'])],
        ['Status',          str(scan['status'])],
        ['Vulnerabilities', str(scan['vulnerabilities'])],
        ['Duration',        f"{scan['duration']:.2f}s" if scan.get('duration') else 'N/A'],
    ]
    tbl = Table(meta_rows, colWidths=[4*cm, 13*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, -1), grey),
        ('TEXTCOLOR',     (0, 0), (0, -1), green),
        ('TEXTCOLOR',     (1, 0), (1, -1), colors.HexColor('#c8d0dc')),
        ('FONTNAME',      (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS',(0, 0), (-1, -1), [colors.HexColor('#0f1621'), colors.HexColor('#0a0e14')]),
        ('GRID',          (0, 0), (-1, -1), 0.5, grey),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
    ]))

    story = [
        Paragraph('XSSniper', title_style),
        Paragraph('ML-Enhanced XSS Vulnerability Scanner — Scan Report', sub_style),
        HRFlowable(width='100%', thickness=1, color=green, spaceAfter=12),
        tbl,
        Spacer(1, 14),
        Paragraph('Scan Log Output', h2_style),
        HRFlowable(width='100%', thickness=0.5, color=grey, spaceAfter=6),
    ]

    log_text = scan.get('log_output') or 'No log output available.'
    for line in log_text.split('\n'):
        if line.strip():
            safe = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe, mono_style))

    story += [
        Spacer(1, 20),
        HRFlowable(width='100%', thickness=0.5, color=grey, spaceAfter=6),
        Paragraph(
            f"Generated by XSSniper — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            footer_style,
        ),
    ]

    doc.build(story)
    buf.seek(0)
    return buf.read()
