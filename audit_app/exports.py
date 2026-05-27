from django.shortcuts import render, redirect, get_object_or_404
from .models import AuditResult, AuditSession
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Rect, String
import io


@login_required
def export_session_pdf(request, session_id):
    session = get_object_or_404(AuditSession, id=session_id)

    results = (
        AuditResult.objects
        .filter(session=session, flagged=True)
        .select_related("message")
        .order_by("-risk_score")
    )

    # Counts
    total     = results.count()
    critical  = results.filter(risk_level="critical").count()
    high      = results.filter(risk_level="high").count()
    medium    = results.filter(risk_level="medium").count()

    # Top senders
    top_senders = (
        AuditResult.objects
        .filter(session=session, flagged=True)
        .values("message__sender_name")
        .annotate(flag_count=Count("id"))
        .order_by("-flag_count")[:5]
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    elements = []

    navy   = colors.HexColor('#0B2E3E')
    teal   = colors.HexColor('#028090')
    light  = colors.HexColor('#E8F4F7')
    red    = colors.HexColor('#e53e3e')
    amber  = colors.HexColor('#d97706')
    blue   = colors.HexColor('#0284c7')
    gray   = colors.HexColor('#64748B')

    title_style = ParagraphStyle('T', parent=styles['Heading1'],
                                  fontSize=18, textColor=navy, spaceAfter=4)
    sub_style   = ParagraphStyle('S', parent=styles['Normal'],
                                  fontSize=9, textColor=gray, spaceAfter=12)
    label_style = ParagraphStyle('L', parent=styles['Normal'],
                                  fontSize=8, textColor=gray)
    value_style = ParagraphStyle('V', parent=styles['Normal'],
                                  fontSize=14, textColor=navy, fontName='Helvetica-Bold')
    normal8     = ParagraphStyle('N8', parent=styles['Normal'], fontSize=8)
    heading_style = ParagraphStyle('H', parent=styles['Normal'],
                                    fontSize=10, textColor=navy,
                                    fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=12)

    # ── Title ──
    elements.append(Paragraph("Compliance Audit Report", title_style))
    elements.append(Paragraph(
        f"Session: {session.created_at.strftime('%d %b %Y %H:%M')}  |  "
        f"Reviewed by: {session.created_by}",
        sub_style
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=teal, spaceAfter=12))

    # ── Summary Stats ──
    elements.append(Paragraph("Summary", heading_style))

    stat_data = [
        [
            Paragraph('TOTAL FLAGGED', label_style),
            Paragraph('CRITICAL', label_style),
            Paragraph('HIGH', label_style),
            Paragraph('MEDIUM', label_style),
        ],
        [
            Paragraph(str(total),    value_style),
            Paragraph(str(critical), ParagraphStyle('VC', parent=value_style, textColor=red)),
            Paragraph(str(high),     ParagraphStyle('VH', parent=value_style, textColor=amber)),
            Paragraph(str(medium),   ParagraphStyle('VM', parent=value_style, textColor=blue)),
        ]
    ]

    stat_table = Table(stat_data, colWidths=[4.3*cm, 4.3*cm, 4.3*cm, 4.3*cm])
    stat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light),
        ('GRID',       (0,0), (-1,-1), 0, colors.white),
        ('PADDING',    (0,0), (-1,-1), 8),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(stat_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Pie Chart + Top Senders side by side ──
    elements.append(Paragraph("Risk Distribution & Top Senders", heading_style))

    # Pie chart
    drawing = Drawing(200, 180)
    pie = Pie()
    pie.x = 30
    pie.y = 40
    pie.width = 130
    pie.height = 130
    pie.data = [critical or 1, high or 1, medium or 1]
    pie.labels = ['', '', '']
    pie.slices[0].fillColor = red
    pie.slices[1].fillColor = amber
    pie.slices[2].fillColor = blue
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1
    drawing.add(pie)

    # Legend below pie
    legend_data = [
        (red, f'Critical: {critical}'),
        (amber, f'High: {high}'),
        (blue, f'Medium: {medium}'),
    ]
    x_pos = 20
    for col, label in legend_data:
        r = Rect(x_pos, 5, 8, 8, fillColor=col, strokeColor=None)
        s = String(x_pos + 11, 6, label, fontSize=7)
        drawing.add(r)
        drawing.add(s)
        x_pos += 55

    # Top senders table
    sender_data = [['Sender', 'Flags']]
    for s in top_senders:
        sender_data.append([
            Paragraph(s['message__sender_name'] or '', normal8),
            str(s['flag_count'])
        ])

    sender_table = Table(sender_data, colWidths=[7*cm, 2*cm])
    sender_table.setStyle(TableStyle([
        ('BACKGROUND',     (0,0), (-1,0), navy),
        ('TEXTCOLOR',      (0,0), (-1,0), colors.white),
        ('FONTNAME',       (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',       (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light]),
        ('GRID',           (0,0), (-1,-1), 0.4, colors.HexColor('#D0E8F0')),
        ('PADDING',        (0,0), (-1,-1), 4),
        ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
    ]))

    # Side by side
    combined = Table(
        [[drawing, sender_table]],
        colWidths=[9*cm, 9*cm]
    )
    combined.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(combined)
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=light, spaceAfter=12))

    # ── Flagged Messages Table ──
    elements.append(Paragraph("Flagged Messages", heading_style))

    data = [['Sender', 'Channel', 'Risk', 'Score', 'Method', 'Reason', 'Notes', 'Status']]

    for r in results:
        data.append([
            Paragraph(r.message.sender_name or '', normal8),
            Paragraph(r.message.channel or '', normal8),
            r.risk_level.upper() if r.risk_level else '',
            str(round(r.risk_score, 2)),
            r.method or '',
            Paragraph(r.reason or '', normal8),
            Paragraph(r.review_notes or '', normal8),
            r.review_status or 'pending',
        ])

    table = Table(data, repeatRows=1, colWidths=[
        2.5*cm, 2.2*cm, 1.5*cm, 1.3*cm, 1.8*cm, 3.5*cm, 3*cm, 1.7*cm
    ])
    table.setStyle(TableStyle([
        ('BACKGROUND',     (0,0), (-1,0), navy),
        ('TEXTCOLOR',      (0,0), (-1,0), colors.white),
        ('FONTNAME',       (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',       (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light]),
        ('GRID',           (0,0), (-1,-1), 0.4, colors.HexColor('#D0E8F0')),
        ('VALIGN',         (0,0), (-1,-1), 'TOP'),
        ('PADDING',        (0,0), (-1,-1), 4),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"audit_report_{session.created_at.strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response