"""Stripe webhook handling without the Stripe SDK: verify the signature, then upgrade/downgrade."""
import hashlib
import hmac
import json
import time

from . import config, db

TOLERANCE_SECONDS = 300


class BadSignature(Exception):
    pass


def verify(payload: bytes, sig_header: str, secret: str) -> dict:
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    # Stripe may send several v1 signatures during secret rotation.
    sigs = [p.split("=", 1)[1] for p in sig_header.split(",") if p.startswith("v1=")]
    ts = parts.get("t")
    if not ts or not sigs or not secret:
        raise BadSignature("missing signature")
    if abs(time.time() - int(ts)) > TOLERANCE_SECONDS:
        raise BadSignature("timestamp outside tolerance")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in sigs):
        raise BadSignature("signature mismatch")
    return json.loads(payload)


def handle_event(event: dict) -> str:
    obj = event.get("data", {}).get("object", {})
    etype = event.get("type")
    if etype == "checkout.session.completed":
        ref = obj.get("client_reference_id")
        if ref and ref.isdigit():
            db.set_plan(int(ref), "pro", obj.get("customer"))
            return "upgraded"
    elif etype == "customer.subscription.deleted":
        if obj.get("customer"):
            db.downgrade_customer(obj["customer"])
            return "downgraded"
    return "ignored"
