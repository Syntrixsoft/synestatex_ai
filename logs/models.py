from django.db import models

from core import choices


class CommunicationLog(models.Model):
    """
    Generic log for all outbound communication (email, SMS, WhatsApp, etc.).

    Channel-specific details (template vars, CC/BCC, MSG91 template id, etc.)
    live in ``payload`` so each provider/service can store what it needs.
    """

    channel = models.CharField(
        max_length=20,
        choices=choices.CommunicationChannelChoices.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=10,
        choices=choices.CommunicationLogStatusChoices.choices,
        default=choices.CommunicationLogStatusChoices.SUCCESS,
        db_index=True,
    )
    provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="Delivery service, e.g. smtp, console, msg91, meta_whatsapp.",
    )
    recipient = models.CharField(max_length=255, blank=True, db_index=True)
    sender = models.CharField(
        max_length=255,
        blank=True,
        help_text="From address, sender id, or WhatsApp business number.",
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    template = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email template path or provider template id/name.",
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Provider message id or internal reference.",
    )
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "status", "created_at"]),
            models.Index(fields=["provider", "created_at"]),
        ]

    def __str__(self):
        return "{} {} {}".format(self.channel, self.status, self.recipient or "-")
