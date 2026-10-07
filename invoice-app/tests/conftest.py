import os
import tempfile

import pytest

# Use a throwaway database file for tests, so your real invoices.db is never touched.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from db import Base, engine  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture
def make_client():
    """Creates a fresh browser-like client. Each one has its own login cookie."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    clients = []

    def _make():
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


def signup(client, email="alex@example.com", password="password123"):
    return client.post("/signup", data={"email": email, "password": password}, follow_redirects=False)


@pytest.fixture(autouse=True)
def no_real_stripe(monkeypatch):
    """Tests never use real Stripe keys, even if your .env has them."""
    for name in ["STRIPE_SECRET_KEY", "STRIPE_PRICE_ID", "STRIPE_WEBHOOK_SECRET", "BASE_URL"]:
        monkeypatch.delenv(name, raising=False)
