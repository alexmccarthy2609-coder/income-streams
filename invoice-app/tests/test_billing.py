import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

import billing
from conftest import signup
from db import User, engine
from test_app import make_invoice

WEBHOOK_SECRET = "whsec_test123"


@pytest.fixture
def stripe_on(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_pro")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)


def get_user(email="alex@example.com") -> User:
    with Session(engine) as s:
        user = s.query(User).filter_by(email=email).one()
        s.expunge(user)
        return user


def update_user(email="alex@example.com", **fields):
    with Session(engine) as s:
        user = s.query(User).filter_by(email=email).one()
        for k, v in fields.items():
            setattr(user, k, v)
        s.commit()


def send_webhook(client, event, secret=WEBHOOK_SECRET):
    """Sends a webhook signed exactly the way Stripe signs them."""
    payload = json.dumps(event)
    t = int(time.time())
    sig = hmac.new(secret.encode(), f"{t}.{payload}".encode(), hashlib.sha256).hexdigest()
    return client.post("/stripe/webhook", content=payload,
                       headers={"stripe-signature": f"t={t},v1={sig}", "content-type": "application/json"})


def test_free_plan_limit(make_client):
    c = make_client()
    signup(c)
    for n in range(3):
        make_invoice(c, f"N{n}", 10)
    assert "3 of 3 invoices used" in c.get("/invoices").text

    r = c.get("/invoices/new", follow_redirects=False)
    assert r.headers["location"] == "/billing?limit=1"
    make_invoice(c, "N4", 10)  # blocked
    assert "N4" not in c.get("/invoices").text
    assert "used all 3 free invoices" in c.get("/billing?limit=1").text

    # Deleting an invoice doesn't give a free slot back...
    c.post("/invoices/1/delete")
    assert c.get("/invoices/new", follow_redirects=False).status_code == 303
    # ...but editing existing invoices is always allowed.
    assert c.get("/invoices/2/edit").status_code == 200


def test_limit_resets_each_month(make_client):
    c = make_client()
    signup(c)
    update_user(usage_month="2020-01", usage_count=3)
    assert c.get("/invoices/new").status_code == 200
    make_invoice(c, "A", 10)
    assert get_user().usage_count == 1 and get_user().usage_month == billing.this_month()


def test_pro_is_unlimited(make_client):
    c = make_client()
    signup(c)
    update_user(plan="pro", usage_month=billing.this_month(), usage_count=50)
    assert c.get("/invoices/new").status_code == 200
    assert "Free plan:" not in c.get("/invoices").text


def test_billing_page_without_stripe_keys(make_client):
    c = make_client()
    signup(c)
    page = c.get("/billing").text
    assert "Payments aren" in page and "disabled" in page
    assert c.post("/billing/checkout", follow_redirects=False).headers["location"] == "/billing"


def test_checkout_redirects_to_stripe(make_client, stripe_on, monkeypatch):
    seen = {}

    def fake_create(**params):
        seen.update(params)
        return SimpleNamespace(url="https://checkout.stripe.com/c/pay/test")
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", fake_create)

    c = make_client()
    signup(c)
    r = c.post("/billing/checkout", follow_redirects=False)
    assert r.headers["location"] == "https://checkout.stripe.com/c/pay/test"
    assert seen["mode"] == "subscription"
    assert seen["line_items"] == [{"price": "price_pro", "quantity": 1}]
    assert seen["client_reference_id"] == "1"
    assert seen["customer_email"] == "alex@example.com"
    assert seen["success_url"].endswith("/billing?session_id={CHECKOUT_SESSION_ID}")


def test_return_from_checkout_activates_pro(make_client, stripe_on, monkeypatch):
    sessions = {
        "cs_mine": SimpleNamespace(client_reference_id="1", status="complete", customer="cus_1", subscription="sub_1"),
        "cs_other": SimpleNamespace(client_reference_id="99", status="complete", customer="cus_9", subscription="sub_9"),
    }
    monkeypatch.setattr(billing.stripe.checkout.Session, "retrieve", lambda sid: sessions[sid])
    c = make_client()
    signup(c)

    c.get("/billing?session_id=cs_other")  # someone else's payment: ignored
    assert get_user().plan == "free"

    assert "Welcome to Pro" in c.get("/billing?session_id=cs_mine").text
    user = get_user()
    assert (user.plan, user.stripe_customer_id, user.stripe_subscription_id) == ("pro", "cus_1", "sub_1")
    assert "Manage subscription" in c.get("/billing").text


def test_webhooks_upgrade_and_downgrade(make_client, stripe_on):
    c = make_client()
    signup(c)
    r = send_webhook(c, {"type": "checkout.session.completed", "data": {"object": {
        "mode": "subscription", "client_reference_id": "1", "customer": "cus_1", "subscription": "sub_1"}}})
    assert r.status_code == 200 and get_user().plan == "pro"

    # Renewal payment failing: still Pro while Stripe retries, with a warning.
    send_webhook(c, {"type": "customer.subscription.updated", "data": {"object": {
        "id": "sub_1", "customer": "cus_1", "status": "past_due"}}})
    assert get_user().plan == "pro"
    assert "payment didn" in c.get("/billing").text

    # A cancellation message about some OLD subscription is ignored.
    send_webhook(c, {"type": "customer.subscription.deleted", "data": {"object": {
        "id": "sub_old", "customer": "cus_1", "status": "canceled"}}})
    assert get_user().plan == "pro"

    # Cancelling the current subscription returns them to Free.
    send_webhook(c, {"type": "customer.subscription.deleted", "data": {"object": {
        "id": "sub_1", "customer": "cus_1", "status": "canceled"}}})
    assert get_user().plan == "free"


def test_webhook_rejects_fake_messages(make_client, stripe_on):
    c = make_client()
    signup(c)
    event = {"type": "checkout.session.completed", "data": {"object": {
        "mode": "subscription", "client_reference_id": "1", "customer": "cus_x", "subscription": "sub_x"}}}
    assert send_webhook(c, event, secret="whsec_wrong").status_code == 400
    assert c.post("/stripe/webhook", content=json.dumps(event)).status_code == 400
    assert get_user().plan == "free"
