"""Plans, the free-plan limit, and everything that talks to Stripe.

Stripe hosts the payment page, so card details never touch this app. We only
store the customer and subscription ids Stripe gives back.

Settings come from environment variables (put them in a .env file, see .env.example):
  STRIPE_SECRET_KEY      starts with sk_test_ (testing) or sk_live_ (real money)
  STRIPE_PRICE_ID        the Pro plan price, created by running: python setup_stripe.py
  STRIPE_WEBHOOK_SECRET  starts with whsec_, lets us check messages really come from Stripe
"""

import json
import os
from datetime import date

import stripe

from db import User

FREE_INVOICES_PER_MONTH = 3
PRO_PRICE_PENCE = 600
PRO_PRICE_LABEL = "£6/month"

# Stripe subscription statuses that mean "this person gets Pro".
# past_due = a renewal payment failed and Stripe is retrying; we keep Pro during that grace period.
PRO_STATUSES = {"active", "trialing", "past_due"}


# ---------------------------------------------------------------- Plan limits

def this_month() -> str:
    return date.today().strftime("%Y-%m")


def is_pro(user: User) -> bool:
    return user.plan == "pro"


def invoices_used(user: User) -> int:
    """New invoices this month. Deleting an invoice doesn't give a free slot back."""
    return user.usage_count if user.usage_month == this_month() else 0


def can_create_invoice(user: User) -> bool:
    return is_pro(user) or invoices_used(user) < FREE_INVOICES_PER_MONTH


def record_invoice_created(user: User) -> None:
    if user.usage_month != this_month():
        user.usage_month, user.usage_count = this_month(), 0
    user.usage_count += 1


def apply_subscription(user: User, status: str, customer_id: str | None, subscription_id: str | None) -> None:
    """Update a user's plan from what Stripe tells us about their subscription."""
    if customer_id:
        user.stripe_customer_id = customer_id
    if subscription_id:
        user.stripe_subscription_id = subscription_id
    user.subscription_status = status
    user.plan = "pro" if status in PRO_STATUSES else "free"


# ---------------------------------------------------------------- Stripe calls

def stripe_ready() -> bool:
    # Placeholder values like "none" count as "not set up yet".
    return (os.environ.get("STRIPE_SECRET_KEY", "").startswith(("sk_test_", "sk_live_"))
            and os.environ.get("STRIPE_PRICE_ID", "").startswith("price_"))


def _use_key() -> None:
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


def create_checkout_url(user: User, base_url: str) -> str:
    """Start a Stripe Checkout payment page for the Pro plan. Returns its address."""
    _use_key()
    params = {
        "mode": "subscription",
        "line_items": [{"price": os.environ["STRIPE_PRICE_ID"], "quantity": 1}],
        "client_reference_id": str(user.id),  # so we know which user paid
        "success_url": f"{base_url}/billing?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base_url}/billing?cancelled=1",
        "allow_promotion_codes": True,
    }
    if user.stripe_customer_id:
        params["customer"] = user.stripe_customer_id
    else:
        params["customer_email"] = user.email
    return stripe.checkout.Session.create(**params).url


def create_portal_url(user: User, base_url: str) -> str:
    """Stripe's ready-made page where customers change card, see receipts or cancel."""
    _use_key()
    return stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id, return_url=f"{base_url}/billing"
    ).url


def fetch_checkout_session(session_id: str) -> dict:
    """Look up a finished checkout, used when the customer returns from the payment page."""
    _use_key()
    s = stripe.checkout.Session.retrieve(session_id)
    return {
        "client_reference_id": s.client_reference_id,
        "status": s.status,
        "customer": s.customer if isinstance(s.customer, str) else getattr(s.customer, "id", None),
        "subscription": s.subscription if isinstance(s.subscription, str) else getattr(s.subscription, "id", None),
    }


def cancel_subscription_now(user: User) -> None:
    """Cancel immediately (used when someone deletes their account). Raises an error if Stripe refuses."""
    _use_key()
    stripe.Subscription.cancel(user.stripe_subscription_id)


def parse_webhook(payload: bytes, signature: str | None) -> dict:
    """Check a webhook really came from Stripe (raises an error if not), then return the event."""
    stripe.Webhook.construct_event(payload, signature, os.environ.get("STRIPE_WEBHOOK_SECRET", ""))
    return json.loads(payload)
