import asyncio
import logging
import socket
import ssl
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from . import alerts, config, db
from .urls import InvalidURL, assert_public

log = logging.getLogger("sitewatch.checker")


def ssl_expiry(host: str, port: int = 443) -> datetime | None:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as s:
                not_after = s.getpeercert()["notAfter"]
    except Exception:
        return None
    return datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=timezone.utc)


async def check_url(client: httpx.AsyncClient, url: str) -> dict:
    """Up = any response below 500. Redirects aren't followed (a redirect still means it's up)."""
    try:
        await asyncio.to_thread(assert_public, url)
    except InvalidURL as e:
        return {"is_up": 0, "status_code": None, "response_ms": None, "error": str(e)}
    start = time.monotonic()
    try:
        r = await client.get(url)
        ms = int((time.monotonic() - start) * 1000)
        up = r.status_code < 500
        return {"is_up": int(up), "status_code": r.status_code, "response_ms": ms,
                "error": None if up else f"HTTP {r.status_code}"}
    except httpx.HTTPError as e:
        return {"is_up": 0, "status_code": None, "response_ms": None,
                "error": type(e).__name__}


def process_result(site, result: dict, expires: datetime | None) -> None:
    """Save a check result and send alerts when status changes."""
    ts = db.now()
    fields = {**result, "last_checked": ts}
    was_up = site["is_up"]
    url, email = site["url"], site["email"]

    if result["is_up"]:
        fields["down_since"] = None
        if was_up == 0:
            alerts.send_email(email, f"✅ {url} is back up",
                              f"{url} is responding again (HTTP {result['status_code']}).\n"
                              f"It was down since {site['down_since']}.")
    else:
        fields["down_since"] = site["down_since"] or ts
        if was_up in (1, None):
            alerts.send_email(email, f"🔴 {url} is DOWN",
                              f"{url} failed its check at {ts}: {result['error']}.\n"
                              f"We'll email you again when it recovers.\n\n"
                              f"Dashboard: {config.BASE_URL}")

    if expires:
        fields["ssl_expires"] = expires.isoformat(timespec="seconds")
        days = (expires - datetime.now(timezone.utc)).days
        if days <= config.SSL_WARN_DAYS and not site["ssl_alerted"]:
            alerts.send_email(email, f"⚠️ SSL certificate for {url} expires in {days} days",
                              f"The SSL certificate for {url} expires on {expires:%Y-%m-%d}. "
                              f"Renew it before then or visitors will see a security warning.")
            fields["ssl_alerted"] = 1
        elif days > config.SSL_WARN_DAYS:
            fields["ssl_alerted"] = 0

    db.save_result(site["id"], **fields)


async def run_once() -> int:
    sites = db.all_sites_with_owner()
    sem = asyncio.Semaphore(20)
    async with httpx.AsyncClient(timeout=15, follow_redirects=False,
                                 headers={"User-Agent": "SiteWatch/1.0"}) as client:
        async def one(site):
            async with sem:
                result = await check_url(client, site["url"])
                p = urlparse(site["url"])
                expires = None
                if p.scheme == "https" and result["status_code"] is not None:
                    expires = await asyncio.to_thread(ssl_expiry, p.hostname, p.port or 443)
                process_result(site, result, expires)
        await asyncio.gather(*(one(s) for s in sites))
    return len(sites)


async def loop_forever():
    while True:
        try:
            n = await run_once()
            log.info("Checked %d sites", n)
        except Exception:
            log.exception("Check run failed")
        await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)
