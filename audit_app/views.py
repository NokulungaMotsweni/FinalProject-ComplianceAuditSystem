from django.shortcuts import render, redirect
from messages_app.models import Message
from .models import AuditResult
from audit_app.choices import DetectionMethod
from audit_app.services.rule_engine import RuleBasedDetector
from .services.tfidf_service import TFIDFDetector
from audit_app.services.hybrid import hybrid_score
import time


def run_audit(request):
    start_time = time.time()

    messages = list(Message.objects.all())

    rule_results = {}

    # -----------------
    # RULE-BASED
    # -----------------
    for message in messages:
        score, reason = RuleBasedDetector.analyse(message.message_text)

        rule_results[message.id] = (score, reason)

        obj, _ = AuditResult.objects.get_or_create(
            message=message,
            method=DetectionMethod.RULE_BASED,
        )

        obj.risk_score = score
        obj.apply_risk_logic()
        obj.reason = reason
        obj.save()


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

        obj, _ = AuditResult.objects.get_or_create(
            message=message,
            method=DetectionMethod.TF_IDF,
        )

        obj.risk_score = scaled_score
        obj.reason = reason
        obj.apply_risk_logic()
        obj.save()


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

        obj, _ = AuditResult.objects.get_or_create(
            message=message,
            method=DetectionMethod.HYBRID,
        )

        obj.risk_score = hybrid
        obj.reason = reason
        obj.apply_risk_logic()
        obj.save()

    end_time = time.time()
    duration = end_time - start_time

    print(f"AUDIT TIME: {duration:.2f} seconds")

    return redirect("results")

def results_list(request):
    results = (AuditResult.objects.select_related("message").
               filter(flagged=True).
               order_by("-created_at"))

    return render(request, "results.html", {"results": results})
