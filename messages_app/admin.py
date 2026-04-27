from django.contrib import admin
from .models import Message, UploadBatch

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("message_id", "sender_name", "channel", "timestamp", "category")
    search_fields = ("message_id", "sender_name", "message_text")
    list_filter = ("channel", "category")

@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ("filename", "uploaded_at", "total_records")