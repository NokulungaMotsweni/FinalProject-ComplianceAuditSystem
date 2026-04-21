from django.db import models
from django.conf import settings

# Message model that stores one organisational communication record
# Imported from a Slack-like dataset
class Message(models.Model):
    # Ground truth labels from the dataset — never used by the detector
    # Used for synthetic evaluation datasets
    CATEGORY_CHOICES = [
        ("normal", "Normal"),
        ("risk_indicator", "Risk Indicator"),
    ]

    # Unique identifier extracted from uploaded dataset
    # Prevents duplicate imports of the same message
    message_id = models.CharField(max_length=50, unique=True)

    # Time the original message was sent
    timestamp = models.DateTimeField()

    # The channel the message was sent in
    channel = models.CharField(max_length=100)

    # Sender's unique ID extracted from the dataset
    # Indexed to improve filtering and retrieval by sender
    sender_id = models.CharField(max_length=50, db_index=True)

    sender_name = models.CharField(max_length=100)

    # Job title / organisational role of sender
    sender_role = models.CharField(max_length=100, blank=True, null=True)

    # The actual message text / content - this is what the detector analyses
    message_text = models.TextField()

    # This is optional labels - nullable for datasets with no labels
    # Used only for evaluation, never used by the detection engine
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True,
        null=True,
        db_index=True
    )

    # When the message was imported into this system
    created_at = models.DateTimeField(auto_now_add=True)

    batch = models.ForeignKey(
        'UploadBatch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages'
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.message_id} - {self.sender_name}: {self.message_text[:50]}"

class UploadBatch(models.Model):
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    total_records = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.filename} ({self.uploaded_at:%Y-%m-%d %H:%M})"
