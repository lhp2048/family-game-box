import time
import pytest
from app import users


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    yield


def test_register_and_authenticate():
    created = users.register_user("小明", "pass1234")
    assert created["username"] == "小明"
    assert "userId" in created
    me = users.authenticate("小明", "pass1234")
    assert me["userId"] == created["userId"]
    with pytest.raises(ValueError, match="口令"):
        users.authenticate("小明", "wrong")
    with pytest.raises(ValueError, match="已占用|已存在"):
        users.register_user("小明", "other")


def test_session_cookie_roundtrip():
    u = users.register_user("ada", "secret99")
    now = int(time.time())
    cookie = users.issue_user_cookie(u["userId"], now=now)
    assert users.user_cookie_ok(cookie, now=now)
    assert users.user_id_from_cookie(cookie, now=now) == u["userId"]
    assert users.user_cookie_ok("garbage", now=now) is False


from fastapi.testclient import TestClient
from helpers import url
from app.main import app
from app import daily_admin as da

client = TestClient(app)


def test_register_requires_family_when_gate_on(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    da.clear_play_gate_cache()
    da.setup_password("adminpass")
    token = da.login("adminpass")["token"]
    client.put(
        url("/api/v1/admin/play-gate"),
        json={"enabled": True, "passphrase": "family"},
        headers={"X-Admin-Token": token},
    )
    bad = client.post(
        url("/api/v1/auth/register"),
        json={"username": "bob", "password": "pass1234", "passphrase": "nope"},
    )
    assert bad.status_code == 400
    ok = client.post(
        url("/api/v1/auth/register"),
        json={"username": "bob", "password": "pass1234", "passphrase": "family"},
    )
    assert ok.status_code == 200
    assert ok.json()["username"] == "bob"
    assert client.cookies.get("fgb_user")
    me = client.get(url("/api/v1/auth/me"))
    assert me.json()["loggedIn"] is True


def test_auth_login_wrong_password_chinese():
    client.cookies.clear()
    reg = client.post(
        url("/api/v1/auth/register"),
        json={"username": "alice", "password": "pass1234"},
    )
    assert reg.status_code == 200
    client.cookies.clear()
    bad = client.post(
        url("/api/v1/auth/login"),
        json={"username": "alice", "password": "wrongpass"},
    )
    assert bad.status_code == 400
    assert "口令" in bad.json()["detail"]


def test_auth_logout_clears_cookie():
    client.cookies.clear()
    reg = client.post(
        url("/api/v1/auth/register"),
        json={"username": "cara", "password": "pass1234"},
    )
    assert reg.status_code == 200
    assert client.cookies.get("fgb_user")
    out = client.post(url("/api/v1/auth/logout"))
    assert out.status_code == 200
    assert not client.cookies.get("fgb_user")
    me = client.get(url("/api/v1/auth/me"))
    assert me.json()["loggedIn"] is False
