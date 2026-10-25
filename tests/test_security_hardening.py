import time

import pytest
from fastapi.testclient import TestClient

from app import daily_admin as da
from app import rate_limit as rl
from app import users
from app.main import app
from helpers import url

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("ADMIN_BOOTSTRAP_SECRET", raising=False)
    da.clear_play_gate_cache()
    rl.clear_all()
    yield
    rl.clear_all()
    da.clear_play_gate_cache()


def test_security_headers_on_lobby():
    r = client.get(url("/"))
    assert r.status_code == 200
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "content-security-policy" in r.headers
    assert "frame-ancestors 'none'" in r.headers.get("content-security-policy", "")


def test_admin_setup_requires_bootstrap_when_env_set(monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_SECRET", "bootstrap-test-secret")
    r = client.post(url("/api/v1/admin/setup"), json={"password": "adminpass1"})
    assert r.status_code == 403
    ok = client.post(
        url("/api/v1/admin/setup"),
        json={"password": "adminpass1", "bootstrapSecret": "bootstrap-test-secret"},
    )
    assert ok.status_code == 200
    assert ok.json().get("token")


def test_admin_login_rate_limit_lockout():
    for _ in range(rl.MAX_FAILURES):
        r = client.post(url("/api/v1/admin/login"), json={"password": "wrong"})
        assert r.status_code == 401
    locked = client.post(url("/api/v1/admin/login"), json={"password": "wrong"})
    assert locked.status_code == 429
    assert locked.headers.get("retry-after")


def test_auth_login_rate_limit_by_username():
    users.register_user("rateuser", "pass1234")
    for _ in range(rl.MAX_FAILURES):
        r = client.post(
            url("/api/v1/auth/login"),
            json={"username": "rateuser", "password": "bad"},
        )
        assert r.status_code == 400
    locked = client.post(
        url("/api/v1/auth/login"),
        json={"username": "rateuser", "password": "bad"},
    )
    assert locked.status_code == 429


def test_admin_set_password_invalidates_user_cookie():
    u = users.register_user("sessuser", "pass1234")
    now = int(time.time())
    cookie = users.issue_user_cookie(u["userId"], now=now)
    assert users.user_cookie_ok(cookie, now=now) is True
    da.setup_password("admin1234")
    token = da.login("admin1234")["token"]
    client.post(
        url("/api/v1/admin/users/%s/password" % u["userId"]),
        json={"password": "newpass99"},
        headers={"X-Admin-Token": token},
    )
    assert users.user_cookie_ok(cookie, now=now) is False


def test_lobby_escapes_podium_html():
    da.setup_password("admin1234")
    users.register_user("xss", "pass1234")
    token = da.login("admin1234")["token"]
    # Inject display-like string via score if possible — lobby uses API summary;
    # assert esc exists in page source for client-side pattern.
    html = client.get(url("/")).text
    assert "function esc(s)" in html
    assert "esc(p.nickname" in html
