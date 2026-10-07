"""The web app. Run it with:  uvicorn main:app --reload
Then open http://127.0.0.1:8000 in your browser."""

import os
import re

from dotenv import load_dotenv

load_dotenv()  # read settings like STRIPE_SECRET_KEY from the .env file, if there is one

from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette.middleware.sessions import SessionMiddleware

import billing
from auth import NotLoggedIn, current_user, hash_password, verify_password
from db import Client, Invoice, InvoiceItem, User, create_tables, get_db
from pdf import build_invoice_pdf

CURRENCIES = {"GBP": "£", "USD": "$", "EUR": "€"}

# The secret key signs the login cookie so it can't be faked.
# On a real server, set the SECRET_KEY environment variable to a long random value.
# "Production" means running online: on Render (which sets RENDER) or with an https BASE_URL.
PRODUCTION = bool(os.environ.get("RENDER")) or os.environ.get("BASE_URL", "").startswith("https://")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if PRODUCTION:
        raise RuntimeError("SECRET_KEY must be set when the app runs online.")
    SECRET_KEY = "dev-only-insecure-key-change-me"

APP_NAME = os.environ.get("APP_NAME", "Invoicer")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Invoice Generator", lifespan=lifespan)
# Login cookie: lasts 30 days, can't be read by JavaScript, and online it's only sent over https.
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60 * 60 * 24 * 30,
                   same_site="lax", https_only=PRODUCTION)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Standard browser protections: no embedding our pages in other sites, etc."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["currencies"] = CURRENCIES
templates.env.globals["billing"] = billing
templates.env.globals["app_name"] = APP_NAME
templates.env.globals["contact_email"] = CONTACT_EMAIL
templates.env.filters["money"] = lambda v, cur: f"{CURRENCIES.get(cur, '')}{v:,.2f}"
# Like money, but drops ".00" — used on the chart where space is tight.
templates.env.filters["money_short"] = lambda v, cur: f"{CURRENCIES.get(cur, '')}{v:,.0f}" if v == int(v) else f"{CURRENCIES.get(cur, '')}{v:,.2f}"


@app.exception_handler(NotLoggedIn)
def redirect_to_login(request: Request, exc: NotLoggedIn):
    return RedirectResponse("/login", status_code=303)


def render(request: Request, template: str, **context):
    return templates.TemplateResponse(request, template, context)


def base_url(request: Request) -> str:
    """The app's public address, e.g. https://myinvoiceapp.com (used in links Stripe sends people back to)."""
    return (os.environ.get("BASE_URL") or os.environ.get("RENDER_EXTERNAL_URL")
            or str(request.base_url)).rstrip("/")


def go(url: str) -> RedirectResponse:
    # 303 tells the browser "now load this page" after a form submission.
    return RedirectResponse(url, status_code=303)


# ---------------------------------------------------------------- Accounts

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Logged in: go to your invoices. Visitors: see the landing page."""
    if request.session.get("user_id"):
        return go("/invoices")
    return render(request, "landing.html", user=None)


@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return render(request, "privacy.html", user=None)


@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return render(request, "terms.html", user=None)


@app.get("/healthz")
def healthcheck(db: Session = Depends(get_db)):
    """Render checks this address to know the app is up and can reach its database."""
    db.execute(select(1))
    return {"ok": True}


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return render(request, "signup.html", error=None, email="")


@app.post("/signup")
def signup(request: Request, email: str = Form(...), password: str = Form(...),
           db: Session = Depends(get_db)):
    email = email.strip().lower()
    error = None
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif db.scalar(select(User).where(User.email == email)):
        error = "An account with that email already exists. Try logging in."
    if error:
        return render(request, "signup.html", error=error, email=email)

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    request.session["user_id"] = user.id
    return go("/settings?welcome=1")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "login.html", error=None, email="")


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        return render(request, "login.html", error="Wrong email or password.", email=email)
    request.session["user_id"] = user.id
    return go("/invoices")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return go("/login")


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, welcome: bool = False, user: User = Depends(current_user)):
    return render(request, "settings.html", user=user, welcome=welcome, saved=False)


@app.post("/settings")
def save_settings(
    request: Request,
    business_name: str = Form(""),
    business_details: str = Form(""),
    default_currency: str = Form("GBP"),
    default_tax_rate: float = Form(0),
    payment_terms_days: int = Form(14),
    default_notes: str = Form(""),
    next: str = Form(""),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    user.business_name = business_name.strip()
    user.business_details = business_details.strip()
    user.default_currency = default_currency if default_currency in CURRENCIES else "GBP"
    user.default_tax_rate = max(default_tax_rate, 0)
    user.payment_terms_days = max(payment_terms_days, 0)
    user.default_notes = default_notes.strip()
    db.commit()
    if next == "/invoices/new":  # first-time setup: go straight to the first invoice
        return go(next)
    return render(request, "settings.html", user=user, welcome=False, saved=True)


# ---------------------------------------------------------------- Clients

def get_client(db: Session, user: User, client_id: int) -> Client:
    """Fetch a client, making sure it belongs to the logged-in user."""
    client = db.get(Client, client_id)
    if client is None or client.user_id != user.id:
        raise HTTPException(404, "Client not found")
    return client


@app.get("/clients", response_class=HTMLResponse)
def clients_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    clients = db.scalars(select(Client).where(Client.user_id == user.id).order_by(Client.name)).all()
    return render(request, "clients.html", user=user, clients=clients)


@app.get("/clients/new", response_class=HTMLResponse)
def new_client_page(request: Request, user: User = Depends(current_user)):
    return render(request, "client_form.html", user=user, client=None)


@app.post("/clients/new")
def create_client(name: str = Form(...), details: str = Form(""),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(Client(user_id=user.id, name=name.strip(), details=details.strip()))
    db.commit()
    return go("/clients")


@app.get("/clients/{client_id}/edit", response_class=HTMLResponse)
def edit_client_page(request: Request, client_id: int,
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    return render(request, "client_form.html", user=user, client=get_client(db, user, client_id))


@app.post("/clients/{client_id}/edit")
def update_client(client_id: int, name: str = Form(...), details: str = Form(""),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    client = get_client(db, user, client_id)
    client.name, client.details = name.strip(), details.strip()
    db.commit()
    return go("/clients")


@app.post("/clients/{client_id}/delete")
def delete_client(client_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(get_client(db, user, client_id))
    db.commit()
    return go("/clients")


# ---------------------------------------------------------------- Invoices

def get_invoice(db: Session, user: User, invoice_id: int) -> Invoice:
    """Fetch an invoice, making sure it belongs to the logged-in user."""
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.user_id != user.id:
        raise HTTPException(404, "Invoice not found")
    return invoice


def next_invoice_number(db: Session, user: User) -> str:
    count = db.scalar(select(func.count()).where(Invoice.user_id == user.id))
    return f"INV-{count + 1:03d}"


def invoice_form(request: Request, user: User, db: Session, invoice: Invoice | None):
    clients = db.scalars(select(Client).where(Client.user_id == user.id).order_by(Client.name)).all()
    today = date.today()
    return render(
        request, "invoice_form.html",
        user=user, invoice=invoice, clients=clients,
        next_number=next_invoice_number(db, user),
        today=today.isoformat(),
        due=(today + timedelta(days=user.payment_terms_days)).isoformat(),
    )


def totals_by_currency(invoices) -> dict[str, float]:
    """Adds up invoice totals, kept separate per currency (you can't add £ to $)."""
    totals: dict[str, float] = {}
    for inv in invoices:
        totals[inv.currency] = round(totals.get(inv.currency, 0) + inv.total, 2)
    return totals


def month_start(d: date, months_back: int = 0) -> date:
    """First day of the month, optionally going back some months."""
    index = d.year * 12 + d.month - 1 - months_back
    return date(index // 12, index % 12 + 1, 1)


def monthly_paid(invoices, currency: str, months: int = 6) -> list[dict]:
    """Money received in each of the last few months, in one currency, for the chart."""
    today = date.today()
    result = []
    for back in range(months - 1, -1, -1):
        start = month_start(today, back)
        amount = sum(
            inv.total for inv in invoices
            if inv.currency == currency and inv.paid_date and month_start(inv.paid_date) == start
        )
        result.append({"label": start.strftime("%b"), "full_label": start.strftime("%B %Y"),
                       "amount": round(amount, 2)})
    top = max((m["amount"] for m in result), default=0)
    for m in result:
        m["percent"] = round(m["amount"] / top * 100, 1) if top else 0
        m["is_top"] = top > 0 and m["amount"] == top
    return result


STATUS_TABS = {
    "all": lambda inv: True,
    "unpaid": lambda inv: inv.status != "paid",
    "overdue": lambda inv: inv.is_overdue,
    "paid": lambda inv: inv.status == "paid",
}


@app.get("/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, status: str = "all",
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    all_invoices = db.scalars(
        select(Invoice).where(Invoice.user_id == user.id)
        .options(selectinload(Invoice.items))
        .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
    ).all()
    if status not in STATUS_TABS:
        status = "all"
    this_month = month_start(date.today())
    unpaid = [i for i in all_invoices if i.status != "paid"]
    stats = {
        "outstanding": totals_by_currency(unpaid),
        "outstanding_count": len(unpaid),
        "overdue": totals_by_currency(i for i in unpaid if i.is_overdue),
        "overdue_count": sum(1 for i in unpaid if i.is_overdue),
        "paid_this_month": totals_by_currency(
            i for i in all_invoices if i.paid_date and i.paid_date >= this_month),
    }
    return render(
        request, "invoices.html", user=user, stats=stats, status=status,
        invoices=[i for i in all_invoices if STATUS_TABS[status](i)],
        counts={name: sum(1 for i in all_invoices if test(i)) for name, test in STATUS_TABS.items()},
        chart=monthly_paid(all_invoices, user.default_currency),
        has_paid=any(i.status == "paid" for i in all_invoices),
    )


def back_to_list(back: str) -> RedirectResponse:
    # Only allow going back to our own invoice list (never an outside website).
    return go(back if re.fullmatch(r"/invoices(\?status=\w+)?", back) else "/invoices")


@app.post("/invoices/{invoice_id}/paid")
def mark_paid(invoice_id: int, back: str = Form("/invoices"),
              user: User = Depends(current_user), db: Session = Depends(get_db)):
    invoice = get_invoice(db, user, invoice_id)
    invoice.status, invoice.paid_date = "paid", date.today()
    db.commit()
    return back_to_list(back)


@app.post("/invoices/{invoice_id}/unpaid")
def mark_unpaid(invoice_id: int, back: str = Form("/invoices"),
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    invoice = get_invoice(db, user, invoice_id)
    invoice.status, invoice.paid_date = "unpaid", None
    db.commit()
    return back_to_list(back)


@app.get("/invoices/new", response_class=HTMLResponse)
def new_invoice_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not billing.can_create_invoice(user):
        return go("/billing?limit=1")
    return invoice_form(request, user, db, None)


@app.get("/invoices/{invoice_id}/edit", response_class=HTMLResponse)
def edit_invoice_page(request: Request, invoice_id: int,
                      user: User = Depends(current_user), db: Session = Depends(get_db)):
    return invoice_form(request, user, db, get_invoice(db, user, invoice_id))


@app.post("/invoices/new")
@app.post("/invoices/{invoice_id}/edit")
def save_invoice(
    invoice_id: int | None = None,
    business_name: str = Form(...),
    business_details: str = Form(""),
    client_name: str = Form(...),
    client_details: str = Form(""),
    invoice_number: str = Form(...),
    invoice_date: date = Form(...),
    due_date: date = Form(...),
    currency: str = Form("GBP"),
    tax_rate: float = Form(0),
    notes: str = Form(""),
    description: list[str] = Form(...),
    quantity: list[float] = Form(...),
    unit_price: list[float] = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Create a new invoice, or update an existing one, then show its PDF."""
    if invoice_id is None:
        if not billing.can_create_invoice(user):
            return go("/billing?limit=1")
        billing.record_invoice_created(user)
        invoice = Invoice(user_id=user.id)
    else:
        invoice = get_invoice(db, user, invoice_id)

    # Find the client by name, or save them as a new client automatically.
    client_name, client_details = client_name.strip(), client_details.strip()
    client = db.scalar(select(Client).where(Client.user_id == user.id, Client.name == client_name))
    if client is None:
        client = Client(user_id=user.id, name=client_name, details=client_details)
        db.add(client)
    elif client_details and not client.details:
        client.details = client_details

    # First invoice? Remember the business details for next time.
    if not user.business_name:
        user.business_name, user.business_details = business_name.strip(), business_details.strip()

    invoice.number = invoice_number.strip()
    invoice.invoice_date, invoice.due_date = invoice_date, due_date
    invoice.currency = currency if currency in CURRENCIES else "GBP"
    invoice.tax_rate = max(tax_rate, 0)
    invoice.notes = notes.strip()
    invoice.business_name, invoice.business_details = business_name.strip(), business_details.strip()
    invoice.client_name, invoice.client_details = client_name, client_details
    invoice.items = [
        InvoiceItem(position=n, description=d.strip(), quantity=q, unit_price=p)
        for n, (d, q, p) in enumerate(zip(description, quantity, unit_price))
        if d.strip()  # skip empty rows
    ]
    db.add(invoice)
    db.flush()  # gives the new client and invoice their ids
    invoice.client_id = client.id
    db.commit()
    return go(f"/invoices?created={invoice.id}")


@app.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    inv = get_invoice(db, user, invoice_id)
    pdf_bytes = build_invoice_pdf({
        "business_name": inv.business_name,
        "business_details": inv.business_details,
        "client_name": inv.client_name,
        "client_details": inv.client_details,
        "invoice_number": inv.number,
        "invoice_date": inv.invoice_date.strftime("%d %b %Y"),
        "due_date": inv.due_date.strftime("%d %b %Y"),
        "currency_symbol": CURRENCIES.get(inv.currency, ""),
        "tax_rate": inv.tax_rate,
        "notes": inv.notes,
        "items": [
            {"description": i.description, "quantity": i.quantity,
             "unit_price": i.unit_price, "amount": i.amount}
            for i in inv.items
        ],
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total": inv.total,
    })
    safe_number = "".join(c for c in inv.number if c.isalnum() or c in "-_") or "invoice"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice-{safe_number}.pdf"'},
    )


@app.post("/invoices/{invoice_id}/delete")
def delete_invoice(invoice_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(get_invoice(db, user, invoice_id))
    db.commit()
    return go("/invoices")


# ---------------------------------------------------------------- Billing (Stripe)

@app.get("/billing", response_class=HTMLResponse)
def billing_page(request: Request, session_id: str | None = None, limit: bool = False,
                 cancelled: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    message = None
    if session_id and billing.stripe_ready():
        # Back from Stripe's payment page: confirm the payment and switch on Pro straight away.
        # (The webhook below does the same thing; whichever arrives first wins.)
        try:
            session = billing.fetch_checkout_session(session_id)
        except Exception:
            session = None
        if session and session["client_reference_id"] == str(user.id) and session["status"] == "complete":
            billing.apply_subscription(user, "active", session["customer"], session["subscription"])
            db.commit()
            message = ("ok", "Payment received. Welcome to Pro! 🎉")
    if limit:
        message = ("error", f"You've used all {billing.FREE_INVOICES_PER_MONTH} free invoices this month. "
                            "Upgrade to Pro for unlimited invoices.")
    if cancelled:
        message = ("info", "Checkout cancelled. You haven't been charged.")
    return render(request, "billing.html", user=user, message=message)


@app.post("/billing/checkout")
def start_checkout(request: Request, user: User = Depends(current_user)):
    if not billing.stripe_ready():
        return go("/billing")
    if billing.is_pro(user):
        return go("/billing")
    return go(billing.create_checkout_url(user, base_url(request)))


@app.post("/billing/portal")
def open_portal(request: Request, user: User = Depends(current_user)):
    if not billing.stripe_ready() or not user.stripe_customer_id:
        return go("/billing")
    return go(billing.create_portal_url(user, base_url(request)))


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe calls this automatically when a subscription starts, renews, fails or is cancelled."""
    payload = await request.body()
    try:
        event = billing.parse_webhook(payload, request.headers.get("stripe-signature"))
    except Exception:
        raise HTTPException(400, "Invalid signature")

    obj = event["data"]["object"]
    if event["type"] == "checkout.session.completed" and obj.get("mode") == "subscription":
        user = db.get(User, int(obj["client_reference_id"])) if str(obj.get("client_reference_id", "")).isdigit() else None
        if user:
            billing.apply_subscription(user, "active", obj.get("customer"), obj.get("subscription"))
    elif event["type"] in ("customer.subscription.created", "customer.subscription.updated",
                           "customer.subscription.deleted"):
        user = db.scalar(select(User).where(User.stripe_customer_id == obj.get("customer")))
        status = "canceled" if event["type"] == "customer.subscription.deleted" else obj["status"]
        # Ignore news about an old subscription (e.g. one they replaced), unless it's an active one.
        is_current = user and user.stripe_subscription_id in (None, obj.get("id"))
        if user and (is_current or status in billing.PRO_STATUSES):
            billing.apply_subscription(user, status, obj.get("customer"), obj.get("id"))
    db.commit()
    return {"received": True}
