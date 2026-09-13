from core import choices
from logs.models import CommunicationLog


class CommunicationLogService:
    @classmethod
    def log(
        cls,
        channel,
        status=choices.CommunicationLogStatusChoices.SUCCESS,
        recipient="",
        provider="",
        sender="",
        subject="",
        body="",
        template="",
        reference_id="",
        payload=None,
        error_message="",
    ):
        if isinstance(recipient, (list, tuple, set)):
            recipient = ", ".join([item for item in recipient if item])

        return CommunicationLog.objects.create(
            channel=channel,
            status=status,
            recipient=recipient,
            provider=provider,
            sender=sender,
            subject=subject,
            body=body,
            template=template,
            reference_id=reference_id,
            payload=payload or {},
            error_message=error_message,
        )
