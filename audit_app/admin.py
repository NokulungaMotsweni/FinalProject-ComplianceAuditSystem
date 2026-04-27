from django.contrib import admin
from .models import AuditResult

@admin.register(AuditResult)
class AuditResultAdmin(admin.ModelAdmin):
    list_display = ("message", "flagged", "risk_score", "risk_level", "method", "review_status")
    list_filter = ("flagged", "risk_level", "method", "review_status")