"""Admin list users + reset password."""

import pytest
from fastapi.testclient import TestClient

from helpers import url
from app.main import app
from app import daily_admin as da
from app import users

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    da.clear_play_gate_cache()
    yield


def _admin_token(password: str = "adminpass") -> str:
    st = da.admin_status(None)
    if not st["hasPassword"]:
        return da.setup_password(password)["token"]
    return da.login(password)["token"]


def test_list_users_empty():
    token = _admin_token()
    r = client.get(url("/api/v1/admin/users"), headers={"X-Admin-Token": token})
    assert r.status_code == 200
    body = r.json()
    assert body == {"users": []}


def test_list_users_after_register():
    created = users.register_user("家庭用户甲", "pass1234")
    token = _admin_token()
    r = client.get(url("/api/v1/admin/users"), headers={"X-Admin-Token": token})
    assert r.status_code == 200
    body = r.json()
    assert "users" in body
    assert len(body["users"]) == 1
    u = body["users"][0]
    assert u["userId"] == created["userId"]
    assert u["username"] == "家庭用户甲"
    assert u.get("createdAt")
    assert "passwordHash" not in u
    assert "passwordSalt" not in u
    assert "password" not in u


def test_list_users_requires_admin():
    users.register_user("someone", "pass1234")
    r = client.get(url("/api/v1/admin/users"))
    assert r.status_code == 401


def test_admin_reset_password_login_with_new():
    created = users.register_user("重置对象", "oldpass1")
    token = _admin_token()
    ah = {"X-Admin-Token": token}
    r = client.post(
        url("/api/v1/admin/users/%s/password" % created["userId"]),
        headers=ah,
        json={"password": "newpass99"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["userId"] == created["userId"]
    assert body["username"] == "重置对象"
    assert "passwordHash" not in body

    me = users.authenticate("重置对象", "newpass99")
    assert me["userId"] == created["userId"]
    with pytest.raises(ValueError, match="口令"):
        users.authenticate("重置对象", "oldpass1")


def test_admin_reset_password_requires_admin():
    created = users.register_user("noadmin", "pass1234")
    r = client.post(
        url("/api/v1/admin/users/%s/password" % created["userId"]),
        json={"password": "newpass99"},
    )
    assert r.status_code == 401
    # old password still works
    me = users.authenticate("noadmin", "pass1234")
    assert me["userId"] == created["userId"]


def test_admin_reset_password_unknown_user():
    token = _admin_token()
    r = client.post(
        url("/api/v1/admin/users/00000000-0000-4000-8000-000000000000/password"),
        headers={"X-Admin-Token": token},
        json={"password": "newpass99"},
    )
    assert r.status_code == 400
    assert "用户" in r.json()["detail"]


def test_admin_reset_password_too_short():
    created = users.register_user("shortpw", "pass1234")
    token = _admin_token()
    r = client.post(
        url("/api/v1/admin/users/%s/password" % created["userId"]),
        headers={"X-Admin-Token": token},
        json={"password": "123"},
    )
    assert r.status_code == 400


def test_admin_page_has_users_tab():
    page = client.get(url("/admin")).text
    assert "用户" in page
    assert "重置口令" in page
    assert "/api/v1/admin/users" in page


def test_list_users_unit_no_secrets():
    users.register_user("秘密检查", "pass1234")
    listed = users.list_users()
    assert len(listed) == 1
    assert "passwordHash" not in listed[0]
    assert "passwordSalt" not in listed[0]
