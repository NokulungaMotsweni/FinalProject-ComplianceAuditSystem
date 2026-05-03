from django.shortcuts import render, redirect
from messages_app.models import Message
from .models import AuditResult
from audit_app.choices import DetectionMethod
from audit_app.services.rule_engine import RuleBasedDetector
from .services.tfidf_service import TFIDFDetector
import numpy as np
import time


def run_audit(request):
    start_time = time.time()

    messages = list(Message.objects.all())

    # -----------------
    # RULE-BASED
    # -----------------
    for message in messages:
        score, reason = RuleBasedDetector.analyse(message.message_text)

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



    for message, score in zip(messages, tfidf_scores):

        # scale score
        scaled_score = round(float(score * 100), 2)

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

    end_time = time.time()
    duration = end_time - start_time

    print(f"AUDIT TIME: {duration:.2f} seconds")

    return redirect("results")

def results_list(request):
    results = (AuditResult.objects.select_related("message").
               filter(flagged=True).
               order_by("-created_at"))

    return render(request, "results.html", {"results": results})
