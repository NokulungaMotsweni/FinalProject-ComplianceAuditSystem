from django.db import models


# Detection methods used by the compliance engine
class DetectionMethod(models.TextChoices):
    RULE_BASED = "rule_based", "Rule Based"
    TFIDF = "tfidf", "TF-IDF"
    HYBRID = "hybrid", "Hybrid"


# Human reviewer workflow states
class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    REVIEWED = "reviewed", "Reviewed"
    DISMISSED = "dismissed", "Dismissed"

# Optional severity band for prioritisation
class RiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"