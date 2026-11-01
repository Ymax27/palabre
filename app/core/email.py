import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("palabre.mail")


async def send_mail(to_email: str, subject: str, body: str) -> None:
    if settings.debug:
        logger.warning("Mail pour %s : %s\n%s", to_email, subject, body)
        return

    def _send() -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from
        message["To"] = to_email
        message.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)

    await asyncio.to_thread(_send)


async def send_magic_link(to_email: str, url: str) -> None:
    await send_mail(
        to_email,
        "Ton lien Palabre",
        f"Connecte-toi : {url}\nCe lien expire dans 15 minutes.",
    )
