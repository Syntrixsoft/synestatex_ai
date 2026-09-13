class BaseChannelService:
    channel = None

    @classmethod
    def send(cls, recipient, **kwargs):
        raise NotImplementedError
