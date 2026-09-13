from django.conf import settings

from communication.base import BaseChannelService
from core import choices


class SmsService(BaseChannelService):
    """SMS channel. MSG91 will be wired here; currently prints to console."""

    channel = choices.CommunicationChannelChoices.SMS

    @classmethod
    def send(cls, recipient, message="", subject="", **kwargs):
        if not message:
            raise ValueError("SMS message is required")
        return cls._send_via_msg91(recipient, message, **kwargs)

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
