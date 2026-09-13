from django.contrib import admin

from .models import CommunicationLog


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = (
        "channel",
        "status",
        "provider",
        "recipient",
        "subject",
        "created_at",
    )
    list_filter = ("channel", "status", "provider", "created_at")
    search_fields = (
        "recipient",
        "sender",
        "subject",
        "body",
        "template",
        "reference_id",
        "error_message",
    )
    readonly_fields = ("created_at",)
