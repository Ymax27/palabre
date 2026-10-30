import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("palabre.auth")


async def send_magic_link(to_email: str, url: str) -> None:
    if settings.debug:
        logger.warning("Lien magique pour %s : %s", to_email, url)
        return

    def _send() -> None:
        message = EmailMessage()
        message["Subject"] = "Ton lien Palabre"
        message["From"] = settings.smtp_from
        message["To"] = to_email
        message.set_content(f"Connecte-toi : {url}\nCe lien expire dans 15 minutes.")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)

    await asyncio.to_thread(_send)
