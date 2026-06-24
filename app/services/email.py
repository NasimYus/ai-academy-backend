"""Email delivery (F.3) with pluggable backends.

- `console` (default): records messages to an in-memory outbox and logs them —
  used in dev and tests (no SMTP needed; codes/tokens still surface in debug).
- `smtp`: sends via aiosmtplib using the configured SMTP server.

Sending is synchronous within the request for now; moving it onto a background
queue is F.2 (arq/Celery).
"""

import logging
from dataclasses import dataclass, field

import aiosmtplib

from app.core.config import settings
from app.services import tasks

logger = logging.getLogger("app.email")


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str


@dataclass
class _Outbox:
    messages: list[EmailMessage] = field(default_factory=list)

    def clear(self) -> None:
        self.messages.clear()


# Inspectable in tests / dev when backend == "console".
outbox = _Outbox()


async def send_email(to: str | None, subject: str, body: str) -> None:
    """Queue an email for delivery. No-op when there is no recipient address.

    Delivery runs through the background-task queue (F.2): inline in dev/tests,
    fire-and-forget under the asyncio backend so requests don't block on SMTP."""
    if not to:
        return
    await tasks.enqueue(_deliver(EmailMessage(to=to, subject=subject, body=body)))


async def _deliver(message: EmailMessage) -> None:
    if settings.email_backend == "smtp":
        await _send_smtp(message)
    else:
        outbox.messages.append(message)
        logger.info("EMAIL → %s | %s", message.to, message.subject)


async def _send_smtp(message: EmailMessage) -> None:
    from email.message import EmailMessage as MimeMessage

    mime = MimeMessage()
    mime["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime.set_content(message.body)

    await aiosmtplib.send(
        mime,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=settings.smtp_use_tls,
    )
