"""One-off setup: creates the "Invoicer Pro" product and its monthly price in your Stripe account.

1. Put your Stripe secret key in .env:   STRIPE_SECRET_KEY=sk_test_...
2. Run:                                  python setup_stripe.py
3. Copy the STRIPE_PRICE_ID line it prints into .env.
"""

import os
import sys

import stripe
from dotenv import load_dotenv

from billing import PRO_PRICE_PENCE

load_dotenv()
key = os.environ.get("STRIPE_SECRET_KEY", "")
if not key.startswith(("sk_test_", "sk_live_")):
    sys.exit("Add STRIPE_SECRET_KEY=sk_test_... to your .env file first (Stripe dashboard → Developers → API keys).")
if key.startswith("sk_live_"):
    if input("This is a LIVE key (real money). Continue? [y/N] ").strip().lower() != "y":
        sys.exit("Stopped.")

stripe.api_key = key
product = stripe.Product.create(name="Invoicer Pro", description="Unlimited invoices")
price = stripe.Price.create(
    product=product.id,
    unit_amount=PRO_PRICE_PENCE,  # in pence: 600 = £6.00
    currency="gbp",
    recurring={"interval": "month"},
)
print("Done! Add this line to your .env file:\n")
print(f"STRIPE_PRICE_ID={price.id}")
