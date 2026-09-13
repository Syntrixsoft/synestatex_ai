from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import get_template, render_to_string
from django.utils.html import strip_tags

from communication.base import BaseChannelService
from core import choices
from logs.service import CommunicationLogService


class EmailService(BaseChannelService):
    channel = choices.CommunicationChannelChoices.EMAIL

    @classmethod
    def send(
        cls,
        recipient,
        template,
        context=None,
        subject="",
        text_template="",
        cc=None,
        bcc=None,
        reply_to=None,
        from_email="",
        attachments=None,
        headers=None,
        **kwargs,
    ):
        to_list = cls._as_list(recipient)
        if not to_list:
            raise ValueError("Email recipient is required")
        if not template:
            raise ValueError("Email HTML template is required")

        context = dict(context or {})
        context.setdefault("site_url", getattr(settings, "SITE_URL", ""))
        context.setdefault("subject", subject)

        html_body = render_to_string(template, context)
        text_body = cls._render_text(template, text_template, html_body, context)
        subject = subject or getattr(settings, "EMAIL_DEFAULT_SUBJECT", "Notification")
        from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")
        reply_to = cls._as_list(reply_to) or cls._as_list(
            getattr(settings, "EMAIL_REPLY_TO", "")
        )
        provider = "console" if not getattr(settings, "EMAIL_HOST", "") else "smtp"

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=to_list,
            cc=cls._as_list(cc),
            bcc=cls._as_list(bcc),
            reply_to=reply_to or None,
            headers=headers or {},
        )
        email.attach_alternative(html_body, "text/html")
        cls._attach_files(email, attachments)

        try:
            if provider == "console":
                cls._print_to_console(email, html_body)
            else:
                email.send(fail_silently=False)

            CommunicationLogService.log(
                channel=cls.channel,
                recipient=to_list,
                provider=provider,
                sender=from_email,
                subject=subject,
                body=text_body,
                template=template,
                payload={
                    "cc": cls._as_list(cc),
                    "bcc": cls._as_list(bcc),
                    "reply_to": reply_to,
                    "context_keys": list(context.keys()),
                },
            )
            return True
        except Exception as exc:
            CommunicationLogService.log(
                channel=cls.channel,
                status=choices.CommunicationLogStatusChoices.FAILED,
                recipient=to_list,
                provider=provider,
                sender=from_email,
                subject=subject,
                body=text_body,
                template=template,
                error_message=str(exc),
                payload={"reply_to": reply_to},
            )
            raise

    @classmethod
    def _render_text(cls, template, text_template, html_body, context):
        text_template = text_template or cls._matching_text_template(template)
        if text_template:
            return render_to_string(text_template, context).strip()
        return strip_tags(html_body).strip()

    @staticmethod
    def _matching_text_template(template):
        if not template.endswith(".html"):
            return ""
        candidate = template[:-5] + ".txt"
        try:
            get_template(candidate)
            return candidate
        except TemplateDoesNotExist:
            return ""

    @classmethod
    def _attach_files(cls, email, attachments):
        for item in attachments or []:
            if isinstance(item, (str, Path)):
                email.attach_file(str(item))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                filename = item[0]
                content = item[1]
                mimetype = item[2] if len(item) > 2 else None
                email.attach(filename, content, mimetype)
            else:
                email.attach(item)

    @staticmethod
    def _as_list(value):
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            return [item for item in value if item]
        return [value]

    @staticmethod
    def _print_to_console(email, html_body):
        print("----- EMAIL -----")
        print("From:", email.from_email)
        print("To:", ", ".join(email.to))
        if email.cc:
            print("Cc:", ", ".join(email.cc))
        if email.bcc:
            print("Bcc:", ", ".join(email.bcc))
        if email.reply_to:
            print("Reply-To:", ", ".join(email.reply_to))
        print("Subject:", email.subject)
        print("Text:")
        print(email.body)
        print("HTML:")
        print(html_body)
        if email.attachments:
            print("Attachments:", len(email.attachments))
        print("-----------------")
