from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger("orqelis.email")


def send_email(to_address: str, subject: str, body: str) -> None:
    backend = (settings.email_backend or "log").lower()
    if backend == "smtp" and settings.smtp_host:
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        return
    log.info("EMAIL to=%s subject=%s\n%s", to_address, subject, body)
    print(f"\n[orqelis email] to={to_address} subject={subject}\n{body}\n")
