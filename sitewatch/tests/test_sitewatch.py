import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import billing, checker, config, db, main, urls


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(config, "CHECK_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(main, "assert_public", lambda url: None)
    sent = []
    monkeypatch.setattr(checker.alerts, "send_email", lambda *a: sent.append(a))
    db.init()
    return sent


@pytest.fixture
def sent(setup):
    return setup


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def signup(client, email="a@b.com"):
    r = client.post("/signup", data={"email": email}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/?sent=1"
    user, _ = db.get_or_create_user(email)
    return user


def test_signup_emails_link_and_dashboard_works(client, sent):
    user = signup(client)
    assert user["token"] in sent[-1][2]
    assert client.get(f"/d/{user['token']}").status_code == 200
    assert client.get("/d/wrong-token").status_code == 404


def test_add_site_respects_free_limit(client):
    t = signup(client)["token"]
    for i in range(5):
        client.post(f"/d/{t}/sites", data={"url": f"site{i}.com"})
    sites = db.sites_for(db.user_by_token(t)["id"])
    assert [s["url"] for s in sites] == ["https://site0.com", "https://site1.com", "https://site2.com"]


def test_url_validation():
    assert urls.normalise("example.com/x#y") == "https://example.com/x"
    for bad in ("ftp://x.com", "https://user:pw@x.com"):
        with pytest.raises(urls.InvalidURL):
            urls.normalise(bad)
    for private in ("http://127.0.0.1", "http://10.0.0.5", "http://169.254.169.254"):
        with pytest.raises(urls.InvalidURL):
            urls.assert_public(private)


def sign(payload: bytes, secret: str, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_stripe_webhook_upgrade_and_downgrade(client, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    user = signup(client)
    ev = json.dumps({"type": "checkout.session.completed", "data": {"object": {
        "client_reference_id": str(user["id"]), "customer": "cus_1"}}}).encode()
    r = client.post("/stripe/webhook", content=ev, headers={"stripe-signature": sign(ev, "whsec_test")})
    assert r.json() == {"result": "upgraded"}
    assert db.user_by_token(user["token"])["plan"] == "pro"

    ev = json.dumps({"type": "customer.subscription.deleted",
                     "data": {"object": {"customer": "cus_1"}}}).encode()
    client.post("/stripe/webhook", content=ev, headers={"stripe-signature": sign(ev, "whsec_test")})
    assert db.user_by_token(user["token"])["plan"] == "free"


def test_stripe_webhook_rejects_bad_signatures(client, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    ev = b'{"type":"checkout.session.completed"}'
    for header in ("", sign(ev, "wrong"), sign(ev, "whsec_test", ts=int(time.time()) - 3600)):
        assert client.post("/stripe/webhook", content=ev,
                           headers={"stripe-signature": header}).status_code == 400


def test_alerts_only_on_status_change(client, sent):
    user = signup(client)
    db.add_site(user["id"], "https://x.com")
    sent.clear()
    down = {"is_up": 0, "status_code": 503, "response_ms": 5, "error": "HTTP 503"}
    up = {"is_up": 1, "status_code": 200, "response_ms": 5, "error": None}

    for result in (up, down, down, up, up):
        checker.process_result(db.all_sites_with_owner()[0], result, None)
    subjects = [s[1] for s in sent]
    assert subjects == ["🔴 https://x.com is DOWN", "✅ https://x.com is back up"]


def test_ssl_warning_sent_once(client, sent):
    user = signup(client)
    db.add_site(user["id"], "https://x.com")
    sent.clear()
    up = {"is_up": 1, "status_code": 200, "response_ms": 5, "error": None}
    soon = datetime.now(timezone.utc) + timedelta(days=5)
    for _ in range(3):
        checker.process_result(db.all_sites_with_owner()[0], up, soon)
    assert len([s for s in sent if "SSL" in s[1]]) == 1


def test_downgraded_users_extra_sites_not_checked(client):
    user = signup(client)
    db.set_plan(user["id"], "pro")
    for i in range(5):
        db.add_site(user["id"], f"https://s{i}.com")
    db.set_plan(user["id"], "free")
    assert len(db.all_sites_with_owner()) == config.PLAN_LIMITS["free"]
