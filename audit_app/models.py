from django.db import models
from django.conf import settings
from .choices import (RiskLevel, DetectionMethod, ReviewStatus)

class AuditSession(models.Model):
    batch = models.ForeignKey(
        "messages_app.UploadBatch",
        on_delete=models.CASCADE,
        related_name="audit_sessions",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    duration_seconds = models.FloatField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Audit Session {self.id} — {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AuditResult(models.Model):

    message = models.ForeignKey(
        "messages_app.Message",
        on_delete=models.CASCADE,
        related_name='audit_results',
    )

    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name="results",
        null=True,
        blank=True
    )

    def apply_risk_logic(self):
        score = self.risk_score or 0

        if score >= 80:
            self.risk_level = RiskLevel.CRITICAL
        elif score >= 60:
            self.risk_level = RiskLevel.HIGH
        elif score >= 30:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW

        self.flagged = score >= 30


    def save(self, *args, **kwargs):
        self.apply_risk_logic()
        super().save(*args, **kwargs)

    flagged = models.BooleanField(default=False, db_index=True)

    risk_score = models.FloatField(default=0.0)

    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
        db_index=True
    )

    reason = models.TextField(
        blank=True,
        default=""
    )

    method = models.CharField(
        max_length=20,
        choices=DetectionMethod.choices,
        default=DetectionMethod.RULE_BASED
    )

    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        db_index=True
    )


    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_audits"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    review_notes = models.TextField(
        blank=True,
        default=""
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.message.message_id} | "
            f"{self.get_method_display()} | "
            f"{self.get_risk_level_display()}"
        )