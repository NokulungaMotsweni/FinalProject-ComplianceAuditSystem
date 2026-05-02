from django.shortcuts import render, redirect
from messages_app.models import Message
from .models import AuditResult
from audit_app.choices import DetectionMethod
from audit_app.services.rule_engine import RuleBasedDetector


def run_audit(request):
    messages = Message.objects.all()

    for message in messages:
        score, reason = RuleBasedDetector.analyse(message.message_text)

        obj, created = AuditResult.objects.update_or_create(
            message=message,
            method=DetectionMethod.RULE_BASED,
            defaults={
                "risk_score": score,
                "reason": reason
            }
        )

        obj.apply_risk_logic()
        obj.save()

    return redirect("results")
def results_list(request):
    results = (AuditResult.objects.select_related("message").
               filter(flagged=True).
               order_by("-created_at"))

    return render(request, "results.html", {"results": results})
