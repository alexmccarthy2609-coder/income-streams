import os

DB_PATH = os.getenv("SITEWATCH_DB", "sitewatch.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
SSL_WARN_DAYS = int(os.getenv("SSL_WARN_DAYS", "14"))

PLAN_LIMITS = {"free": 3, "pro": 50}
PRO_PRICE = os.getenv("PRO_PRICE", "£7/month")

# Stripe: create a Payment Link for a recurring product in the Stripe dashboard,
# and a webhook endpoint pointing at {BASE_URL}/stripe/webhook.
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PORTAL_LINK = os.getenv("STRIPE_PORTAL_LINK", "")  # customer billing portal, for cancellations

# Email alerts (any SMTP provider: Resend, Postmark, Brevo, Gmail app password...)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "SiteWatch <alerts@example.com>")
