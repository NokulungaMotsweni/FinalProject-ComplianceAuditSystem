from logging import critical

from django.shortcuts import render

from audit_app.choices import RiskLevel
from audit_app.models import AuditResult
from messages_app.models import Message, UploadBatch


def dashboard(request):
    total_messages = Message.objects.count()
    total_uploads = UploadBatch.objects.count()
    flagged_alerts = AuditResult.objects.filter(flagged=True).count()
    critical_risk = AuditResult.objects.filter(
        risk_level=RiskLevel.CRITICAL
    ).count()

    recent_uploads = UploadBatch.objects.order_by("-uploaded_at")[:5]

    context = {
        "total_messages": total_messages,
        "total_uploads": total_uploads,
        "flagged_alerts": flagged_alerts,
        "critical_risk": critical_risk,
        "recent_uploads": recent_uploads,
    }

    return render(request, "dashboard.html", context)
