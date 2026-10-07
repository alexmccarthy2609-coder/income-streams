import logging
import smtplib
from email.message import EmailMessage

from . import config

log = logging.getLogger("sitewatch.alerts")


def send_email(to: str, subject: str, body: str) -> None:
    if not config.SMTP_HOST:
        log.info("SMTP not configured; would email %s: %s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_FROM, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
            s.starttls()
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
    except Exception:
        log.exception("Failed to send email to %s", to)
