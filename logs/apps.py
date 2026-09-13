"""
Communication logs application.

Stores outbound communication activity (email, SMS, WhatsApp, etc.) in a single
generic model. Provider-specific fields (MSG91 template id, WhatsApp payload,
email CC/BCC, etc.) are kept in ``CommunicationLog.payload``.

Currently uses the default database. In the future, a dedicated logs database
and ``DATABASE_ROUTERS`` will route log models to a separate PostgreSQL instance.
"""

from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logs"
