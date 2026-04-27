from django.db import models


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETE = "complete", "Complete"
    FAILED = "failed", "Failed"

# Ground-truth labels used only for testing / evaluation datasets
class MessageCategory(models.TextChoices):
    NORMAL = "normal", "Normal"
    RISK_INDICATOR = "risk_indicator", "Risk Indicator"
