from django.db import models

from core import choices


class Otp(models.Model):
    purpose = models.CharField(
        max_length=20, choices=choices.OtpPurposeChoices.choices, db_index=True
    )
    channel = models.CharField(
        max_length=10, choices=choices.OtpChannelChoices.choices
    )
    sent_to = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Email or phone number the OTP was sent to",
    )
    code_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=15,
        choices=choices.OtpStatusChoices.choices,
        default=choices.OtpStatusChoices.PENDING,
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["purpose", "sent_to", "status"]),
        ]

    def __str__(self):
        return "{} {} {}".format(self.purpose, self.channel, self.sent_to)
