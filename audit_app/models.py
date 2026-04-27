from django.db import models
from django.conf import settings
from .choices import (RiskLevel, DetectionMethod, ReviewStatus)

# Create your models here.

class AuditResult(models.Model):

    message = models.ForeignKey(
        "messages_app.Message",
        on_delete=models.CASCADE,
        related_name='audit_results',
    )

    def save(self, *args, **kwargs):
        score = self.risk_score or 0

        if self.risk_score >= 80:
            self.risk_level = RiskLevel.CRITICAL
        elif self.risk_score >= 60:
            self.risk_level = RiskLevel.HIGH
        elif self.risk_score >= 30:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW

        self.flagged = score >= 30

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
        constraints = [
            models.UniqueConstraint(
                fields=["message", "method"],
                name="unique_audit_message_result"
            )
        ]

    def __str__(self):
        return (
            f"{self.message.message_id} | "
            f"{self.get_method_display()} | "
            f"{self.get_risk_level_display()}"
        )