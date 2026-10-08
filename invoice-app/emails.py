"""Sending emails (password reset links) through Resend, https://resend.com.

Settings (environment variables / .env):
  RESEND_API_KEY  starts with re_  (Resend dashboard → API Keys)
  EMAIL_FROM      e.g. "Invoicer <hello@yourdomain.com>" (a domain you've verified in Resend)
Without them the app still works; it just can't send emails.
"""

import os

import httpx


def email_ready() -> bool:
    return os.environ.get("RESEND_API_KEY", "").startswith("re_") and bool(os.environ.get("EMAIL_FROM"))


def send_email(to: str, subject: str, text: str) -> None:
    """Send a plain-text email. Raises an error if Resend refuses it."""
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
        json={"from": os.environ["EMAIL_FROM"], "to": [to], "subject": subject, "text": text},
        timeout=10,
    )
    response.raise_for_status()
