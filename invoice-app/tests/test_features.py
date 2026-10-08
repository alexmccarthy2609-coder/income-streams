import csv
import io

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import billing
from conftest import signup
from db import Client, Invoice, User, engine
from test_app import INVOICE
from test_billing import update_user

GENERATOR_FORM = {**INVOICE, "vat_number": "GB 123 4567 89", "supply_date": "2026-10-01", "currency": "EUR"}


def count(model) -> int:
    with Session(engine) as s:
        return s.scalar(select(func.count()).select_from(model))


def test_free_generator_makes_pdf_without_saving(make_client):
    c = make_client()
    page = c.get("/free-invoice-generator")
    assert page.status_code == 200 and "No sign-up" in page.text
    r = c.post("/free-invoice-generator", data=GENERATOR_FORM)
    assert r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert count(Invoice) == 0 and count(User) == 0


def test_seo_pages(make_client):
    c = make_client()
    assert "How to write an invoice in the UK" in c.get("/guides/how-to-write-an-invoice-uk").text
    robots = c.get("/robots.txt").text
    assert "Disallow: /invoices" in robots and "sitemap.xml" in robots
    sitemap = c.get("/sitemap.xml").text
    assert "/free-invoice-generator</loc>" in sitemap and "/guides/how-to-write-an-invoice-uk</loc>" in sitemap


def test_vat_number_and_supply_date(make_client):
    c = make_client()
    signup(c)
    c.post("/settings", data={"business_name": "Acme", "vat_number": "GB 999 9999 99"})
    assert 'value="GB 999 9999 99"' in c.get("/invoices/new").text

    c.post("/invoices/new", data={**INVOICE, "vat_number": "GB 999 9999 99", "supply_date": "2026-10-01"})
    edit = c.get("/invoices/1/edit").text
    assert 'value="2026-10-01"' in edit and 'value="GB 999 9999 99"' in edit
    assert c.get("/invoices/1/pdf").content.startswith(b"%PDF")

    # Supply date is optional: an empty box is fine.
    c.post("/invoices/1/edit", data={**INVOICE, "supply_date": ""})
    assert 'name="supply_date"\n                 value=""' in c.get("/invoices/1/edit").text


def test_csv_export_only_has_your_invoices(make_client):
    alice, bob = make_client(), make_client()
    signup(alice, "alice@example.com")
    signup(bob, "bob@example.com")
    alice.post("/invoices/new", data=INVOICE)
    bob.post("/invoices/new", data={**INVOICE, "invoice_number": "BOB-1"})
    rows = list(csv.reader(io.StringIO(alice.get("/settings/export.csv").text)))
    assert rows[0][0] == "Invoice number" and len(rows) == 2
    assert rows[1][0] == "INV-001" and rows[1][9] == "156.00"


def test_delete_account(make_client):
    c, other = make_client(), make_client()
    signup(c)
    signup(other, "other@example.com")
    c.post("/invoices/new", data=INVOICE)
    other.post("/invoices/new", data=INVOICE)

    assert "Type DELETE" in c.post("/settings/delete-account", data={"password": "password123", "confirm": "no"}).text
    assert "password isn" in c.post("/settings/delete-account", data={"password": "wrong-pass", "confirm": "DELETE"}).text

    r = c.post("/settings/delete-account", data={"password": "password123", "confirm": "delete"}, follow_redirects=False)
    assert r.headers["location"] == "/?deleted=1"
    assert count(User) == 1 and count(Invoice) == 1 and count(Client) == 1  # only the other user's data left
    assert c.get("/invoices", follow_redirects=False).headers["location"] == "/login"


def test_delete_account_cancels_pro_subscription(make_client, monkeypatch):
    cancelled = []
    monkeypatch.setattr(billing, "cancel_subscription_now", lambda user: cancelled.append(user.stripe_subscription_id))
    c = make_client()
    signup(c)
    update_user(plan="pro", stripe_customer_id="cus_1", stripe_subscription_id="sub_1")
    c.post("/settings/delete-account", data={"password": "password123", "confirm": "DELETE"})
    assert cancelled == ["sub_1"] and count(User) == 0


def test_delete_account_stops_if_cancel_fails(make_client, monkeypatch):
    def fail(user):
        raise RuntimeError("stripe down")
    monkeypatch.setattr(billing, "cancel_subscription_now", fail)
    c = make_client()
    signup(c)
    update_user(plan="pro", stripe_customer_id="cus_1", stripe_subscription_id="sub_1")
    r = c.post("/settings/delete-account", data={"password": "password123", "confirm": "DELETE"})
    assert "couldn" in r.text and count(User) == 1


def test_too_many_wrong_passwords_blocks_login(make_client):
    c = make_client()
    signup(c)
    c.post("/logout")
    for _ in range(10):
        assert "Wrong email or password" in c.post("/login", data={"email": "alex@example.com", "password": "nope-nope"}).text
    r = c.post("/login", data={"email": "alex@example.com", "password": "password123"})
    assert "Too many wrong attempts" in r.text
