from messages_app.models import Message
from audit_app.models import AuditResult
from audit_app.services.rule_engine import RuleBasedDetector
from audit_app.choices import DetectionMethod


def run_audit():
    messages = Message.objects.all()

    for message in messages:
        score, reason = RuleBasedDetector.analyse(message.message_text)

        AuditResult.objects.update_or_create(
            message=message,
            method=DetectionMethod.RULE_BASED,
            defaults={
                "risk_score": score,
                "reason": reason
            }
        )