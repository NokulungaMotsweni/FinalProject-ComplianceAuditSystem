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
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn}

for method in [DetectionMethod.RULE_BASED, DetectionMethod.TF_IDF, DetectionMethod.HYBRID]:
    print(f"{method}: {evaluate(method)}")