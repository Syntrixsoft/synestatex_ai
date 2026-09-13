from django.contrib import admin

from .models import Otp


@admin.register(Otp)
class OtpAdmin(admin.ModelAdmin):
    list_display = (
        "purpose",
        "channel",
        "sent_to",
        "status",
        "attempts",
        "expires_at",
        "verified_at",
        "created_at",
    )
    list_filter = ("purpose", "channel", "status")
    search_fields = ("sent_to",)
    readonly_fields = ("code_hash", "created_at", "verified_at")
