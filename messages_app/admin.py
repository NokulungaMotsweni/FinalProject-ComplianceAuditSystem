from django.contrib import admin
from .models import Message, UploadBatch

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("message_id", "sender_name", "channel", "timestamp", "category")
    search_fields = ("message_id", "sender_name", "channel", "message_text")
    list_filter = ("channel", "category")

    ordering = ("-timestamp",)

    date_hierarchy = "timestamp"

    list_select_related = ("batch",)


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ("filename", "status", "total_records", "failed_records", "uploaded_at")

    search_fields = ("filename",)

    list_filter = (
        "status",
        "uploaded_at",
    )

    ordering = ("-uploaded_at",)