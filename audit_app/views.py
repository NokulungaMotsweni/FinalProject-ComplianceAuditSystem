from django.shortcuts import render, redirect, get_object_or_404
from messages_app.models import Message
from .evaluate import run_full_evaluation
from .models import AuditResult, AuditSession
from audit_app.choices import DetectionMethod, ReviewStatus
from audit_app.services.rule_engine import RuleBasedDetector
from .services.tfidf_service import TFIDFDetector
from audit_app.services.hybrid import hybrid_score
from django.db.models import Count, Case, When, IntegerField
from django.utils import timezone
from django.contrib import messages
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
import time
import csv

@login_required
def select_batch(request):
    from messages_app.models import UploadBatch
    from messages_app.choices import UploadStatus

    batches = UploadBatch.objects.filter(
        status=UploadStatus.COMPLETE
    ).order_by("-uploaded_at")

    return render(request, "select_batch.html", {"batches": batches})

@login_required
def run_audit(request):
    start_time = time.time()

    batch = None
    # Get batch_id from POST — if none, fall back to all messages
    batch_id = request.POST.get("batch_id")

    if batch_id:
        messages = list(Message.objects.filter(batch_id=batch_id))
    else:
        messages = list(Message.objects.all())

    # Always clear old results before running
    AuditResult.objects.filter(message__in=messages).delete()

    # Create a new session for this run
    session = AuditSession.objects.create(
        batch=batch,
        created_by=request.user if request.user.is_authenticated else None
    )

    rule_results = {}

    # -----------------
    # RULE-BASED
    # -----------------
    for message in messages:
        score, reason = RuleBasedDetector.analyse(message.message_text)

        rule_results[message.id] = (score, reason)

        AuditResult.objects.create(
            message=message,
            method=DetectionMethod.RULE_BASED,
            session=session,
            risk_score=score,
            reason=reason,
        )

    # ---------------
    # TF-IDF
    # ---------------
    tfidf_scores = TFIDFDetector.analyse(messages)

    tfidf_results = {}


    for message, score in zip(messages, tfidf_scores):

        # scale score
        scaled_score = round(float(score * 100), 2)

        tfidf_results[message.id] = scaled_score

        reason = ""
        if scaled_score >= 60:
           reason = "High TF-IDF anomaly score"
        elif scaled_score >= 30:
           reason = "Moderate TF-IDF anomaly score"

        AuditResult.objects.create(
            message=message,
            method=DetectionMethod.TF_IDF,
            session=session,
            risk_score=scaled_score,
            reason=reason,
        )


    # -----------------
    # HYBRID
    # -----------------
    for message, tfidf_raw in zip(messages, tfidf_scores):

        rule_score, rule_reason = rule_results.get(message.id, (0, ""))

        tfidf_score = tfidf_results.get(message.id, 0)

        hybrid = hybrid_score(rule_score, tfidf_score)

        if rule_score > 0:
            reason = rule_reason
        elif tfidf_score >= 30:
            reason = "TF-IDF anomaly signal"
        else:
            reason = ""

        AuditResult.objects.create(
            message=message,
            method=DetectionMethod.HYBRID,
            session=session,
            risk_score=hybrid,
            reason=reason,
        )

    end_time = time.time()
    duration = end_time - start_time

    print(f"AUDIT TIME: {duration:.2f} seconds")

    return redirect("results")

@login_required
def results_list(request):
    sessions = AuditSession.objects.all().order_by("-created_at")

    session_id = request.GET.get("session")
    if session_id:
        session = get_object_or_404(AuditSession, id=session_id)
    else:
        session = sessions.first()

    # Get filter parameters
    filter_risk    = request.GET.get("risk_level", "")
    filter_sender  = request.GET.get("sender", "")
    filter_channel = request.GET.get("channel", "")
    filter_method  = request.GET.get("method", "")

    if session:
        results = (
            AuditResult.objects
            .select_related("message")
            .filter(flagged=True, session=session)
            .order_by("-created_at")
        )

        # Apply filters
        if filter_risk:
            results = results.filter(risk_level=filter_risk)
        if filter_sender:
            results = results.filter(message__sender_name=filter_sender)
        if filter_channel:
            results = results.filter(message__channel=filter_channel)
        if filter_method:
            results = results.filter(method=filter_method)

        top_senders = (
            AuditResult.objects
            .select_related("message")
            .filter(flagged=True, session=session)
            .values("message__sender_name")
            .annotate(flag_count=Count("id"))
            .order_by("-flag_count")[:5]
        )

        # Get unique values for filter dropdowns
        all_senders = (
            AuditResult.objects
            .filter(flagged=True, session=session)
            .values_list("message__sender_name", flat=True)
            .distinct()
            .order_by("message__sender_name")
        )

        all_channels = (
            AuditResult.objects
            .filter(flagged=True, session=session)
            .values_list("message__channel", flat=True)
            .distinct()
            .order_by("message__channel")
        )

    else:
        results = AuditResult.objects.none()
        top_senders = []
        all_senders = []
        all_channels = []

    context = {
        "results": results,
        "sessions": sessions,
        "current_session": session,
        "total_results": results.count(),
        "medium_count": results.filter(risk_level="medium").count(),
        "critical_count": results.filter(risk_level="critical").count(),
        "high_count": results.filter(risk_level="high").count(),
        "top_senders": top_senders,
        "all_senders": all_senders,
        "all_channels": all_channels,
        "filter_risk": filter_risk,
        "filter_sender": filter_sender,
        "filter_channel": filter_channel,
        "filter_method": filter_method,
    }

    return render(request, "results.html", context)

@login_required
def review_queue(request):
    # Get session filter
    session_id = request.GET.get("session")
    show = request.GET.get("show", "pending")

    sessions = AuditSession.objects.all().order_by("-created_at")

    if session_id:
        session = get_object_or_404(AuditSession, id=session_id)
    else:
        session = sessions.first()

    # Get all flagged results, preferring hybrid where it exists
    all_flagged = (
        AuditResult.objects
        .filter(flagged=True, session=session)
        .select_related("message")
        .annotate(
            method_priority=Case(
                When(method=DetectionMethod.HYBRID, then=0),
                default=1,
                output_field=IntegerField()
            )
        )
        .order_by("message_id", "method_priority", "-risk_score")
    )

    # Apply pending/reviewed filter
    if show == "reviewed":
        all_flagged = all_flagged.exclude(review_status="pending")
    else:
        all_flagged = all_flagged.filter(review_status="pending")

    # Deduplicate by message — keep one result per message
    seen = set()
    queue = []
    for result in all_flagged:
        if result.message_id not in seen:
            seen.add(result.message_id)
            queue.append(result)

    # Sort final queue by risk score
    queue.sort(key=lambda r: r.risk_score, reverse=True)

    selected = None
    all_method_results = []

    selected_id = request.GET.get("selected")
    if selected_id:
        selected = AuditResult.objects.filter(
            id=selected_id
        ).select_related("message").first()

        if selected:
            all_method_results = (
                AuditResult.objects
                .filter(message=selected.message, session=session)
                .order_by("method")
            )

    total_flagged = AuditResult.objects.filter(
        session=session,
        flagged=True
    ).values("message_id").distinct().count()

    pending_count = AuditResult.objects.filter(
        session=session,
        flagged=True,
        review_status=ReviewStatus.PENDING
    ).values("message_id").distinct().count()

    reviewed_count = total_flagged - pending_count

    context = {
        "queue": queue,
        "selected": selected,
        "all_method_results": all_method_results,
        "sessions": sessions,
        "current_session": session,
        "show": show,
        "pending_count": pending_count,
        "total_flagged": total_flagged,
        "reviewed_count": reviewed_count,
    }

    return render(request, "review_queue.html", context)

@login_required
def review_action(request, result_id):
    if request.method == "POST":
        result = AuditResult.objects.get(id=result_id)
        decision = request.POST.get("decision")
        notes = request.POST.get("notes", "")

        result.review_status = decision
        result.review_notes = notes
        result.reviewed_by = request.user
        result.reviewed_at = timezone.now()

        if request.user.is_authenticated:
            result.reviewed_by = request.user
        else:
            result.reviewed_at = None

        result.save()

        if decision == "reviewed":
            messages.success(request, f"Message from {result.message.sender_name} marked as confirmed risk.")
        elif decision == "dismissed":
            messages.info(request, f"Message from {result.message.sender_name} dismissed.")

        AuditResult.objects.filter(
            message=result.message,
            session=result.session
        ).exclude(id=result_id).update(
            review_status=decision,
            reviewed_at=timezone.now()
        )
    return redirect(f"/review/?selected={result_id}")

@login_required
def close_session(request, session_id):
    if request.method == "POST":
        session = get_object_or_404(AuditSession, id=session_id)

        # Double check no pending results remain
        pending = AuditResult.objects.filter(
            session=session,
            flagged=True,
            review_status=ReviewStatus.PENDING).exists()

        if not pending:
            session.is_closed = True
            session.closed_at = timezone.now()
            if request.user.is_authenticated:
                session.closed_by = request.user
            session.save()
            messages.success(request, "Session closed successfully.")
        else:
            messages.warning(request, "Cannot close session — pending reviews remain.")

    return redirect(f"/review/?session={session.id}")

@login_required
def evaluation_view(request):
    results = run_full_evaluation()
    return render(request, "evaluation.html", {"results": results})

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