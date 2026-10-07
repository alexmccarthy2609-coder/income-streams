import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    token TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    stripe_customer TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    is_up INTEGER,
    status_code INTEGER,
    response_ms INTEGER,
    error TEXT,
    last_checked TEXT,
    down_since TEXT,
    ssl_expires TEXT,
    ssl_alerted INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, url)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(SCHEMA)


def get_or_create_user(email: str) -> tuple[sqlite3.Row, bool]:
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            return row, False
        c.execute("INSERT INTO users (email, token, created_at) VALUES (?, ?, ?)",
                  (email, secrets.token_urlsafe(24), now()))
        return c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone(), True


def user_by_token(token: str):
    with conn() as c:
        return c.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()


def set_plan(user_id: int, plan: str, stripe_customer: str | None = None):
    with conn() as c:
        c.execute("UPDATE users SET plan = ?, stripe_customer = COALESCE(?, stripe_customer) "
                  "WHERE id = ?", (plan, stripe_customer, user_id))


def downgrade_customer(stripe_customer: str):
    with conn() as c:
        c.execute("UPDATE users SET plan = 'free' WHERE stripe_customer = ?", (stripe_customer,))


def sites_for(user_id: int):
    with conn() as c:
        return c.execute("SELECT * FROM sites WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()


def add_site(user_id: int, url: str):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO sites (user_id, url) VALUES (?, ?)", (user_id, url))


def delete_site(user_id: int, site_id: int):
    with conn() as c:
        c.execute("DELETE FROM sites WHERE id = ? AND user_id = ?", (site_id, user_id))


def all_sites_with_owner():
    """Sites to check. A downgraded user's sites beyond their plan limit are skipped."""
    with conn() as c:
        rows = c.execute("""SELECT s.*, u.email, u.plan FROM sites s
                            JOIN users u ON u.id = s.user_id ORDER BY s.user_id, s.id""").fetchall()
    counts: dict[int, int] = {}
    active = []
    for r in rows:
        counts[r["user_id"]] = counts.get(r["user_id"], 0) + 1
        if counts[r["user_id"]] <= config.PLAN_LIMITS.get(r["plan"], 0):
            active.append(r)
    return active


def save_result(site_id: int, **fields):
    cols = ", ".join(f"{k} = ?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE sites SET {cols} WHERE id = ?", (*fields.values(), site_id))
