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
import time


def select_batch(request):
    from messages_app.models import UploadBatch
    from messages_app.choices import UploadStatus

    batches = UploadBatch.objects.filter(
        status=UploadStatus.COMPLETE
    ).order_by("-uploaded_at")

    return render(request, "select_batch.html", {"batches": batches})

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

def evaluation_view(request):
    results = run_full_evaluation()
    return render(request, "evaluation.html", {"results": results})
