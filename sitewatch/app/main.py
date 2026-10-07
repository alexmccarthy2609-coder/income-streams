import asyncio
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import alerts, billing, checker, config, db
from .urls import InvalidURL, assert_public, normalise

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    task = asyncio.create_task(checker.loop_forever()) if config.CHECK_INTERVAL_SECONDS > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="SiteWatch", lifespan=lifespan)


def dashboard_url(token: str) -> str:
    return f"{config.BASE_URL}/d/{token}"


def require_user(token: str):
    user = db.user_by_token(token)
    if not user:
        raise HTTPException(404, "Dashboard not found")
    return user


@app.get("/", response_class=HTMLResponse)
def landing(request: Request, sent: bool = False):
    return templates.TemplateResponse(request, "landing.html", {
        "limits": config.PLAN_LIMITS, "price": config.PRO_PRICE, "sent": sent})


@app.post("/signup")
def signup(email: str = Form(...)):
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Invalid email")
    user, _ = db.get_or_create_user(email)
    # The dashboard link is the login, so it is only ever sent by email.
    alerts.send_email(email, "Your SiteWatch dashboard",
                      f"Open your dashboard (bookmark this link):\n{dashboard_url(user['token'])}")
    return RedirectResponse("/?sent=1", status_code=303)


@app.get("/d/{token}", response_class=HTMLResponse)
def dashboard(request: Request, token: str, error: str | None = None, upgraded: bool = False):
    user = require_user(token)
    sites = db.sites_for(user["id"])
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user, "sites": sites, "limit": config.PLAN_LIMITS[user["plan"]],
        "error": error, "upgraded": upgraded, "price": config.PRO_PRICE,
        "can_upgrade": bool(config.STRIPE_PAYMENT_LINK),
        "portal": config.STRIPE_PORTAL_LINK})


@app.post("/d/{token}/sites")
def add_site(token: str, url: str = Form(...)):
    user = require_user(token)
    if len(db.sites_for(user["id"])) >= config.PLAN_LIMITS[user["plan"]]:
        return RedirectResponse(f"/d/{token}?error=Plan+limit+reached", status_code=303)
    try:
        url = normalise(url)
        assert_public(url)
    except InvalidURL as e:
        return RedirectResponse(f"/d/{token}?{urlencode({'error': str(e)})}", status_code=303)
    db.add_site(user["id"], url)
    return RedirectResponse(f"/d/{token}", status_code=303)


@app.post("/d/{token}/sites/{site_id}/delete")
def delete_site(token: str, site_id: int):
    user = require_user(token)
    db.delete_site(user["id"], site_id)
    return RedirectResponse(f"/d/{token}", status_code=303)


@app.get("/d/{token}/upgrade")
def upgrade(token: str):
    user = require_user(token)
    if not config.STRIPE_PAYMENT_LINK:
        raise HTTPException(503, "Payments not configured yet")
    query = urlencode({"client_reference_id": user["id"], "prefilled_email": user["email"]})
    return RedirectResponse(f"{config.STRIPE_PAYMENT_LINK}?{query}", status_code=303)


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    try:
        event = billing.verify(payload, request.headers.get("stripe-signature", ""),
                               config.STRIPE_WEBHOOK_SECRET)
    except (billing.BadSignature, ValueError):
        raise HTTPException(400, "Invalid signature")
    return JSONResponse({"result": billing.handle_event(event)})


@app.get("/healthz")
def health():
    return {"ok": True}
