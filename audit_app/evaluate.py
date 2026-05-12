from audit_app.models import AuditResult
from audit_app.choices import DetectionMethod

def evaluate(method):
    tp = fp = fn = tn = 0

    results = AuditResult.objects.filter(method=method)

    for r in results:
        actual = r.message.category == "risk_indicator"
        predicted = r.flagged
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

    total = tp + fp + fn + tn

    precision_raw = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall_raw = tp / (tp + fn) if (tp + fn) > 0 else 0

    accuracy = round((tp + tn) / total * 100, 2) if total > 0 else 0
    precision = round(precision_raw * 100, 2)
    recall = round(recall_raw * 100, 2)
    f1 = round(2 * (precision_raw * recall_raw) / (precision_raw + recall_raw) * 100, 2) if (precision_raw + recall_raw) > 0 else 0

    return {
        "method": method,
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }

def run_full_evaluation():
    return [
        evaluate(DetectionMethod.RULE_BASED),
        evaluate(DetectionMethod.TF_IDF),
        evaluate(DetectionMethod.HYBRID),
    ]