import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256

from django.conf import settings
from django.utils import timezone

from communication.service import CommunicationService
from core import choices
from verification.messages import get_otp_purpose_content
from verification.models import Otp


class OtpError(Exception):
    code = "otp_error"


class OtpResendTooSoon(OtpError):
    code = "resend_too_soon"

    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__("Please wait {} seconds before requesting a new OTP".format(retry_after))


@dataclass
class OtpVerifyResult:
    success: bool
    error: str | None = None
    otp: Otp | None = None


class OtpService:
    @classmethod
    def generate(
        cls,
        purpose,
        sent_to,
        channel=choices.OtpChannelChoices.EMAIL,
    ):
        sent_to = cls._normalize_sent_to(channel, sent_to)
        cls._enforce_resend_window(purpose, sent_to)

        Otp.objects.filter(
            purpose=purpose,
            sent_to=sent_to,
            status=choices.OtpStatusChoices.PENDING,
        ).update(status=choices.OtpStatusChoices.INVALIDATED)

        length = getattr(settings, "OTP_LENGTH", 6)
        expiry_seconds = getattr(settings, "OTP_EXPIRY_SECONDS", 300)
        max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
        plain_code = f"{secrets.randbelow(10 ** length):0{length}d}"

        otp = Otp.objects.create(
            purpose=purpose,
            channel=channel,
            sent_to=sent_to,
            code_hash=cls._hash_code(purpose, sent_to, plain_code),
            max_attempts=max_attempts,
            expires_at=timezone.now() + timedelta(seconds=expiry_seconds),
        )
        return otp, plain_code

    @classmethod
    def verify(cls, purpose, sent_to, code, channel=None):
        sent_to = cls._normalize_sent_to(channel, sent_to)
        otp = (
            Otp.objects.filter(
                purpose=purpose,
                sent_to=sent_to,
                status=choices.OtpStatusChoices.PENDING,
            )
            .order_by("-created_at")
            .first()
        )
        if otp is None:
            return OtpVerifyResult(success=False, error="not_found")

        if otp.expires_at <= timezone.now():
            otp.status = choices.OtpStatusChoices.EXPIRED
            otp.save(update_fields=["status"])
            return OtpVerifyResult(success=False, error="expired", otp=otp)

        otp.attempts += 1
        expected = cls._hash_code(purpose, sent_to, str(code).strip())
        if not hmac.compare_digest(otp.code_hash, expected):
            if otp.attempts >= otp.max_attempts:
                otp.status = choices.OtpStatusChoices.FAILED
            otp.save(update_fields=["attempts", "status"])
            error = "max_attempts" if otp.status == choices.OtpStatusChoices.FAILED else "invalid"
            return OtpVerifyResult(success=False, error=error, otp=otp)

        otp.status = choices.OtpStatusChoices.VERIFIED
        otp.verified_at = timezone.now()
        otp.save(update_fields=["attempts", "status", "verified_at"])
        return OtpVerifyResult(success=True, otp=otp)

    @classmethod
    def send(cls, purpose, sent_to, channel=choices.OtpChannelChoices.EMAIL):
        otp, plain_code = cls.generate(
            purpose=purpose,
            sent_to=sent_to,
            channel=channel,
        )
        cls._dispatch(otp, plain_code)
        return otp

    @classmethod
    def _dispatch(cls, otp, plain_code):
        expiry_minutes = max(1, getattr(settings, "OTP_EXPIRY_SECONDS", 300) // 60)
        content = get_otp_purpose_content(otp.purpose, plain_code, expiry_minutes)

        if otp.channel == choices.OtpChannelChoices.EMAIL:
            CommunicationService.send(
                channel=otp.channel,
                recipient=otp.sent_to,
                subject=content["email_subject"],
                template="communication/emails/otp.html",
                context={
                    "otp_code": plain_code,
                    "purpose": content["purpose"],
                    "purpose_label": content["purpose_label"],
                    "heading": content["email_heading"],
                    "message": content["email_message"],
                    "sent_to": otp.sent_to,
                    "expiry_minutes": expiry_minutes,
                },
            )
            return

        if otp.channel == choices.OtpChannelChoices.SMS:
            CommunicationService.send(
                channel=otp.channel,
                recipient=otp.sent_to,
                message=content["sms_message"],
                purpose=otp.purpose,
                otp_code=plain_code,
            )
            return

        raise OtpError("Unsupported OTP channel")

    @classmethod
    def _enforce_resend_window(cls, purpose, sent_to):
        resend_seconds = getattr(settings, "OTP_RESEND_SECONDS", 60)
        latest = (
            Otp.objects.filter(purpose=purpose, sent_to=sent_to)
            .order_by("-created_at")
            .first()
        )
        if latest is None:
            return
        elapsed = (timezone.now() - latest.created_at).total_seconds()
        if elapsed < resend_seconds:
            raise OtpResendTooSoon(int(resend_seconds - elapsed))

    @staticmethod
    def _normalize_sent_to(channel, sent_to):
        sent_to = (sent_to or "").strip()
        if channel == choices.OtpChannelChoices.EMAIL:
            return sent_to.lower()
        return sent_to

    @staticmethod
    def _hash_code(purpose, sent_to, code):
        message = "{}:{}:{}".format(purpose, sent_to, code)
        return hmac.new(
            settings.SECRET_KEY.encode(),
            message.encode(),
            sha256,
        ).hexdigest()
