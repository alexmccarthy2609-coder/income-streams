import re

import pytest

import emails
import main
from conftest import signup


@pytest.fixture
def outbox(monkeypatch):
    """Turns email on, but captures messages instead of sending them."""
    sent = []
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "Invoicer <hello@example.com>")
    monkeypatch.setattr(emails, "send_email", lambda to, subject, text: sent.append((to, subject, text)))
    return sent


def reset_link(text):
    return re.search(r"https?://\S+/reset/\S+", text).group(0).split("/reset/")[1]


def test_without_email_set_up_people_are_told_to_contact_us(make_client):
    c = make_client()
    assert "isn't switched on yet" in c.get("/forgot").text
    assert "Forgot your password?" in c.get("/login").text


def test_reset_password_flow(make_client, outbox):
    c = make_client()
    signup(c)
    c.post("/logout")

    r = c.post("/forgot", data={"email": "ALEX@example.com"})
    assert "we've sent a link" in r.text
    assert len(outbox) == 1 and outbox[0][0] == "alex@example.com"
    token = reset_link(outbox[0][2])

    assert "Choose a new password" in c.get(f"/reset/{token}").text
    assert "at least 8" in c.post(f"/reset/{token}", data={"password": "short"}).text
    r = c.post(f"/reset/{token}", data={"password": "new-password-1"}, follow_redirects=False)
    assert r.headers["location"] == "/invoices"

    # Old password no longer works, new one does, and the link can't be used twice.
    c.post("/logout")
    assert "Wrong email" in c.post("/login", data={"email": "alex@example.com", "password": "password123"}).text
    ok = c.post("/login", data={"email": "alex@example.com", "password": "new-password-1"}, follow_redirects=False)
    assert ok.headers["location"] == "/invoices"
    assert "expired or has already been used" in c.get(f"/reset/{token}").text


def test_unknown_email_gets_same_message_and_no_email(make_client, outbox):
    c = make_client()
    r = c.post("/forgot", data={"email": "nobody@example.com"})
    assert "we've sent a link" in r.text and outbox == []


def test_reset_requests_are_limited(make_client, outbox):
    c = make_client()
    signup(c)
    for _ in range(5):
        c.post("/forgot", data={"email": "alex@example.com"})
    assert len(outbox) == 3


def test_fake_and_expired_links_are_rejected(make_client, outbox, monkeypatch):
    c = make_client()
    signup(c)
    assert "expired" in c.get("/reset/not-a-real-token").text
    c.post("/forgot", data={"email": "alex@example.com"})
    token = reset_link(outbox[0][2])
    monkeypatch.setattr(main, "RESET_MAX_AGE", -1)
    assert "expired" in c.get(f"/reset/{token}").text


def test_send_email_calls_resend(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json))
        return FakeResponse()

    monkeypatch.setenv("RESEND_API_KEY", "re_abc")
    monkeypatch.setenv("EMAIL_FROM", "Invoicer <hello@example.com>")
    monkeypatch.setattr(emails.httpx, "post", fake_post)
    emails.send_email("a@b.com", "Hi", "Body")
    url, headers, body = calls[0]
    assert url == "https://api.resend.com/emails" and headers["Authorization"] == "Bearer re_abc"
    assert body == {"from": "Invoicer <hello@example.com>", "to": ["a@b.com"], "subject": "Hi", "text": "Body"}
