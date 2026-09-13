from communication.email import EmailService
from communication.sms import SmsService
from core import choices


class CommunicationError(Exception):
    pass


class CommunicationService:
    CHANNELS = {
        choices.CommunicationChannelChoices.EMAIL: EmailService,
        choices.CommunicationChannelChoices.SMS: SmsService,
    }

    @classmethod
    def send(cls, channel, recipient, **kwargs):
        service = cls.CHANNELS.get(channel)
        if service is None:
            raise CommunicationError("Unsupported communication channel: {}".format(channel))
        return service.send(recipient=recipient, **kwargs)

    @classmethod
    def register(cls, channel, service):
        cls.CHANNELS[channel] = service
