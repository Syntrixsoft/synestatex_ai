from django.conf import settings

from communication.base import BaseChannelService
from core import choices
from logs.service import CommunicationLogService


class SmsService(BaseChannelService):
    """SMS channel. MSG91 will be wired here; currently prints to console."""

    channel = choices.CommunicationChannelChoices.SMS

    @classmethod
    def send(cls, recipient, message="", subject="", **kwargs):
        if not message:
            raise ValueError("SMS message is required")

        sender_id = getattr(settings, "MSG91_SENDER_ID", "")
        template_id = getattr(settings, "MSG91_TEMPLATE_ID", "")
        payload = {
            "template_id": template_id,
            "subject": subject,
            **kwargs,
        }

        try:
            cls._send_via_msg91(recipient, message, **kwargs)
            CommunicationLogService.log(
                channel=cls.channel,
                recipient=recipient,
                provider="msg91",
                sender=sender_id,
                body=message,
                template=template_id,
                payload=payload,
            )
            return True
        except Exception as exc:
            CommunicationLogService.log(
                channel=cls.channel,
                status=choices.CommunicationLogStatusChoices.FAILED,
                recipient=recipient,
                provider="msg91",
                sender=sender_id,
                body=message,
                template=template_id,
                error_message=str(exc),
                payload=payload,
            )
            raise

    @classmethod
    def _send_via_msg91(cls, recipient, message, **kwargs):
        auth_key = getattr(settings, "MSG91_AUTH_KEY", "")
        sender_id = getattr(settings, "MSG91_SENDER_ID", "")
        template_id = getattr(settings, "MSG91_TEMPLATE_ID", "")
        print(
            "[SMS:MSG91] to={} sender={} template={} auth_key_set={} message={}".format(
                recipient,
                sender_id,
                template_id,
                bool(auth_key),
                message,
            )
        )
        return True
