import os
import subprocess
import sys

from conftest import signup


def test_landing_page_for_visitors(make_client):
    c = make_client()
    r = c.get("/")
    assert r.status_code == 200
    assert "Professional invoices in 60 seconds" in r.text
    assert 'href="/signup"' in r.text and "£6" in r.text


def test_logged_in_users_skip_landing(make_client):
    c = make_client()
    signup(c)
    assert c.get("/", follow_redirects=False).headers["location"] == "/invoices"


def test_legal_pages_and_health(make_client):
    c = make_client()
    assert "Privacy policy" in c.get("/privacy").text
    assert "Terms of service" in c.get("/terms").text
    assert c.get("/healthz").json() == {"ok": True}


def test_security_headers(make_client):
    r = make_client().get("/")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_postgres_address_is_converted():
    import db
    for given in ["postgres://u:p@host:5432/x", "postgresql://u:p@host:5432/x"]:
        os.environ["DATABASE_URL"], before = given, os.environ["DATABASE_URL"]
        try:
            assert db.database_url() == "postgresql+psycopg://u:p@host:5432/x"
        finally:
            os.environ["DATABASE_URL"] = before


def test_online_app_refuses_to_start_without_secret_key(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"}
    env.update(RENDER="true", DATABASE_URL=f"sqlite:///{tmp_path}/x.db")
    r = subprocess.run([sys.executable, "-c", "import main"], env=env, capture_output=True, text=True,
                       cwd=os.path.dirname(os.path.dirname(__file__)))
    assert r.returncode != 0 and "SECRET_KEY must be set" in r.stderr

    env["SECRET_KEY"] = "a-real-secret"
    r = subprocess.run([sys.executable, "-c", "import main; print(main.PRODUCTION)"], env=env,
                       capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    assert r.stdout.strip() == "True"
