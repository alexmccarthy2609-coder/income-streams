"""Render marketing images: the OfficeKit cover and SiteWatch screenshots (with demo data).

    python marketing/make_images.py     # needs: pip install playwright, plus sitewatch requirements
"""
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
OUT = HERE / "images"
SITEWATCH = HERE.parent / "sitewatch"
CHROMIUM = os.getenv("CHROMIUM_PATH")  # optional: use a system Chromium instead of Playwright's
PORT = 8099


def seed_demo_db(path: str) -> str:
    os.environ["SITEWATCH_DB"] = path
    sys.path.insert(0, str(SITEWATCH))
    from app import db
    db.init()
    user, _ = db.get_or_create_user("agency@example.com")
    db.set_plan(user["id"], "pro")
    now = datetime.now(timezone.utc)
    demo = [
        ("https://brightsmile-dental.com", 1, 200, 182, 74, None),
        ("https://harbourcafe.co.uk", 1, 200, 241, 9, None),
        ("https://northfield-plumbing.com", 0, None, None, 52, "ConnectTimeout"),
        ("https://lunayoga.studio", 1, 200, 96, 61, None),
        ("https://shop.oakandpine.co", 1, 301, 134, 88, None),
        ("https://kensington-law.com", 1, 200, 310, 33, None),
    ]
    for url, up, code, ms, ssl_days, err in demo:
        db.add_site(user["id"], url)
    for site, (url, up, code, ms, ssl_days, err) in zip(db.sites_for(user["id"]), demo):
        db.save_result(site["id"], is_up=up, status_code=code, response_ms=ms, error=err,
                       last_checked=(now - timedelta(minutes=2)).isoformat(timespec="seconds"),
                       down_since=None if up else (now - timedelta(minutes=14)).isoformat(timespec="seconds"),
                       ssl_expires=(now + timedelta(days=ssl_days)).isoformat(timespec="seconds"))
    return user["token"]


def main():
    OUT.mkdir(exist_ok=True)
    tmp = tempfile.mkdtemp()
    token = seed_demo_db(f"{tmp}/demo.db")
    env = {**os.environ, "CHECK_INTERVAL_SECONDS": "0", "STRIPE_PAYMENT_LINK": "https://buy.stripe.com/demo"}
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
                              cwd=SITEWATCH, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(2)
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()

            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto((HERE / "officekit-cover.html").resolve().as_uri())
            page.screenshot(path=OUT / "officekit-cover.png")

            for scheme in ("light", "dark"):
                page = browser.new_page(viewport={"width": 1100, "height": 760},
                                        color_scheme=scheme, device_scale_factor=2)
                page.goto(f"http://localhost:{PORT}/d/{token}")
                page.screenshot(path=OUT / f"sitewatch-dashboard-{scheme}.png", full_page=True)
            page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2)
            page.goto(f"http://localhost:{PORT}/")
            page.screenshot(path=OUT / "sitewatch-landing.png", full_page=True)
            browser.close()
    finally:
        server.terminate()
    for f in sorted(OUT.iterdir()):
        print(f"Wrote {f}")


if __name__ == "__main__":
    main()
