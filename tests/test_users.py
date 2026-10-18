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
