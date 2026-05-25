from logging import critical
import csv
from django.shortcuts import render, redirect
from django.views import defaults

from audit_app.choices import RiskLevel
from audit_app.models import AuditResult
from messages_app.models import Message, UploadBatch
from messages_app.choices import UploadStatus
from django.contrib import messages
from django.utils import timezone
from datetime import datetime


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

def upload_dataset(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        batch = UploadBatch.objects.create(
            filename=file.name,
            status=UploadStatus.PROCESSING,
        )

        decoded = file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(decoded)

        success = 0
        failed = 0
        error_log = ""

        for row in reader:
            try:
                Message.objects.update_or_create(
                    message_id=row["message_id"],
                    defaults={
                        "timestamp": timezone.make_aware(
                            datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                        ),
                        "sender_id": row["sender_id"],
                        "sender_name": row["sender_name"],
                        "channel": row["channel"],
                        "message_text": row["message"],
                        "category": row["category"],
                        "batch": batch,
                    }
                )
                success += 1

            except Exception as e:
                failed += 1
                batch.error_log = (batch.error_log or "") + (
                    f"{row.get('message_id')} - {str(e)}\n"
                )

        batch.total_records = success
        batch.failed_records = failed
        batch.error_log = error_log
        batch.status = UploadStatus.COMPLETE if failed == 0 else UploadStatus.FAILED
        batch.save()

        if failed == 0:
            messages.success(
                request,
                f"Upload successful: {success} records processed. Run the audit to analyse your dataset."
            )
            return redirect("results")
        else:
            messages.warning(
                request,
                f"Upload completed with errors: {success} succeeded, {failed} failed."
            )
            return redirect("upload_dataset")
        
    return render(request, "upload.html")