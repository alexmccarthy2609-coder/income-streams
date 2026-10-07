from conftest import signup

INVOICE = {
    "business_name": "McCarthy Plumbing",
    "business_details": "12 High Street\nLondon",
    "client_name": "Jane's Cafe",
    "client_details": "4 Market Road",
    "invoice_number": "INV-001",
    "invoice_date": "2026-10-07",
    "due_date": "2026-10-21",
    "currency": "GBP",
    "tax_rate": "20",
    "notes": "Thanks!",
    "description": ["Boiler service", "Valve", ""],
    "quantity": ["1", "2", "1"],
    "unit_price": ["85", "22.5", "0"],
}


def test_pages_need_login(make_client):
    c = make_client()
    for url in ["/invoices", "/invoices/new", "/clients", "/settings"]:
        r = c.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"


def test_signup_login_logout(make_client):
    c = make_client()
    r = signup(c)
    assert r.headers["location"] == "/settings?welcome=1"
    assert c.get("/invoices").status_code == 200

    c.post("/logout")
    assert c.get("/invoices", follow_redirects=False).status_code == 303

    bad = c.post("/login", data={"email": "alex@example.com", "password": "wrong-pass"})
    assert "Wrong email or password" in bad.text
    good = c.post("/login", data={"email": "ALEX@example.com", "password": "password123"}, follow_redirects=False)
    assert good.headers["location"] == "/invoices"


def test_signup_validation(make_client):
    c = make_client()
    signup(c)
    assert "already exists" in signup(make_client()).text
    assert "at least 8" in signup(make_client(), "x@y.com", "short").text
    assert "valid email" in signup(make_client(), "not-an-email").text


def test_settings_prefill_new_invoice(make_client):
    c = make_client()
    signup(c)
    c.post("/settings", data={"business_name": "Acme Ltd", "default_currency": "USD",
                              "default_tax_rate": "10", "payment_terms_days": "30",
                              "default_notes": "Pay by bank transfer"})
    page = c.get("/invoices/new").text
    assert 'value="Acme Ltd"' in page
    assert 'value="USD" data-symbol="$" selected' in page
    assert "Pay by bank transfer" in page
    assert 'value="INV-001"' in page


def test_create_view_edit_delete_invoice(make_client):
    c = make_client()
    signup(c)
    r = c.post("/invoices/new", data=INVOICE, follow_redirects=False)
    assert r.headers["location"] == "/invoices?created=1"

    listing = c.get("/invoices").text
    assert "INV-001" in listing and "Jane&#39;s Cafe" in listing
    assert "£156.00" in listing  # (85 + 2 x 22.50) = 130, plus 20% VAT

    pdf = c.get("/invoices/1/pdf")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")

    # The client was saved automatically, and business details remembered.
    assert "Jane&#39;s Cafe" in c.get("/clients").text
    assert 'value="McCarthy Plumbing"' in c.get("/settings").text
    assert 'value="INV-002"' in c.get("/invoices/new").text

    edited = {**INVOICE, "description": ["Boiler service"], "quantity": ["2"], "unit_price": ["85"]}
    c.post("/invoices/1/edit", data=edited)
    assert "£204.00" in c.get("/invoices").text  # 2 x 85 = 170 + 20% = 204
    assert "Valve" not in c.get("/invoices/1/edit").text

    c.post("/invoices/1/delete")
    assert "No invoices yet" in c.get("/invoices").text


def test_users_cannot_see_each_others_data(make_client):
    alice, bob = make_client(), make_client()
    signup(alice, "alice@example.com")
    signup(bob, "bob@example.com")
    alice.post("/invoices/new", data=INVOICE)

    assert "INV-001" not in bob.get("/invoices").text
    assert "Jane" not in bob.get("/clients").text
    for url in ["/invoices/1/pdf", "/invoices/1/edit", "/clients/1/edit"]:
        assert bob.get(url).status_code == 404
    assert bob.post("/invoices/1/delete").status_code == 404
    assert bob.post("/clients/1/delete").status_code == 404
    assert alice.get("/invoices/1/pdf").status_code == 200


def test_clients_crud(make_client):
    c = make_client()
    signup(c)
    c.post("/clients/new", data={"name": "Bob's Bakery", "details": "1 Bread St"})
    assert "Bob&#39;s Bakery" in c.get("/clients").text
    c.post("/clients/1/edit", data={"name": "Bob's Bakes", "details": ""})
    assert "Bob&#39;s Bakes" in c.get("/clients").text
    assert "Bob&#39;s Bakes" in c.get("/invoices/new").text  # shows in the client picker
    c.post("/clients/1/delete")
    assert "No clients yet" in c.get("/clients").text


def make_invoice(c, number, total, due="2099-01-01", currency="GBP"):
    c.post("/invoices/new", data={**INVOICE, "invoice_number": number, "due_date": due, "currency": currency,
                                  "tax_rate": "0", "description": ["Work"], "quantity": ["1"],
                                  "unit_price": [str(total)]})


def test_mark_paid_and_dashboard_totals(make_client):
    c = make_client()
    signup(c)
    make_invoice(c, "A", 100)                     # unpaid, not due yet
    make_invoice(c, "B", 50, due="2020-01-01")    # overdue
    make_invoice(c, "C", 25)                      # will be paid

    r = c.post("/invoices/3/paid", data={"back": "/invoices?status=unpaid"}, follow_redirects=False)
    assert r.headers["location"] == "/invoices?status=unpaid"

    page = c.get("/invoices").text
    tiles = page.split('class="tiles"')[1].split('class="card"')[0]
    assert "£150.00" in tiles   # owed: 100 + 50
    assert "£50.00" in tiles    # overdue
    assert "£25.00" in tiles    # paid this month
    assert "1 past due date" in tiles

    assert "Mark invoices as paid" not in page and 'class="bars"' in page

    def numbers(status):
        html = c.get(f"/invoices?status={status}").text.split("<tbody>")[1]
        return sorted(n for n in "ABC" if f">{n}</a>" in html)
    assert numbers("all") == ["A", "B", "C"]
    assert numbers("unpaid") == ["A", "B"]
    assert numbers("overdue") == ["B"]
    assert numbers("paid") == ["C"]

    c.post("/invoices/3/unpaid")
    assert "No paid invoices" in c.get("/invoices?status=paid").text


def test_editing_keeps_paid_status(make_client):
    c = make_client()
    signup(c)
    make_invoice(c, "A", 100)
    c.post("/invoices/1/paid")
    c.post("/invoices/1/edit", data={**INVOICE, "invoice_number": "A"})
    assert "No paid invoices" not in c.get("/invoices?status=paid").text


def test_paid_routes_are_private_and_safe(make_client):
    alice, bob = make_client(), make_client()
    signup(alice, "alice@example.com")
    signup(bob, "bob@example.com")
    make_invoice(alice, "A", 100)
    assert bob.post("/invoices/1/paid").status_code == 404
    # The "back" address can only point to our own invoice list.
    r = alice.post("/invoices/1/paid", data={"back": "https://evil.example.com"}, follow_redirects=False)
    assert r.headers["location"] == "/invoices"


def test_old_database_is_upgraded(tmp_path):
    """A database made by step 2 (no paid_date column) gets the column added on startup."""
    import sqlite3
    import db

    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, status VARCHAR(20))")
    con.commit()
    con.close()

    original = db.engine
    db.engine = db.create_engine(f"sqlite:///{path}")
    try:
        db.create_tables()
    finally:
        db.engine = original
    con = sqlite3.connect(path)
    cols = [row[1] for row in con.execute("PRAGMA table_info(invoices)")]
    assert "paid_date" in cols
