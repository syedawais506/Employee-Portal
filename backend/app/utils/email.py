import smtplib
from email.headerregistry import Address
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _from_header() -> str | Address:
    if not settings.smtp_from_name:
        return settings.smtp_from_email
    local_part, _, domain = settings.smtp_from_email.partition("@")
    return Address(display_name=settings.smtp_from_name, username=local_part, domain=domain)


def send_email(*, to: str, subject: str, html_body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = _from_header()
    message["To"] = to
    message.set_content("This email requires an HTML-capable client.")
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("email_send_failed", to=to, subject=subject)
