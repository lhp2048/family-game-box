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
from helpers import login_as, url
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


def test_score_requires_user_even_when_gate_off():
    client.cookies.clear()
    tid = "11111111-1111-4111-8111-111111111111"
    client.post(url("/api/v1/terminals/register"), json={"terminalId": tid, "nickname": "旧号"})
    r = client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 1, "total": 1, "timeMs": 1000},
        },
        headers={"X-Terminal-Id": tid},
    )
    assert r.status_code in (401, 403)

    reg = client.post(
        url("/api/v1/auth/register"),
        json={"username": "scorer1", "password": "pass1234"},
    )
    assert reg.status_code == 200
    assert client.cookies.get("fgb_user")
    ok = client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 1, "total": 1, "timeMs": 1000},
        },
        headers={"X-Terminal-Id": tid},
    )
    assert ok.status_code == 200


def test_games_page_redirects_to_login_without_user():
    client.cookies.clear()
    page = client.get(url("/games/stroop/index.html"), follow_redirects=False)
    assert page.status_code == 307
    loc = page.headers["location"]
    assert "/login?next=" in loc


def test_claim_terminal_once(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    import uuid
    from app.terminals import register_terminal
    from app import scores, daily_runs

    tid = str(uuid.uuid4())
    register_terminal(tid, "旧号")
    scores.submit_score(
        tid,
        "stroop",
        "challenge",
        "normal",
        {"correct": 5, "total": 10, "timeMs": 5000},
    )
    daily_runs.start_run(tid)

    u1 = users.register_user("claimer1", "pass1234")
    u2 = users.register_user("claimer2", "pass1234")

    result = users.claim_terminal(u1["userId"], tid)
    assert result["ok"] is True
    assert result["terminalId"] == tid
    assert result["userId"] == u1["userId"]

    entries = [e for e in scores._load_entries() if e.get("terminalId") == tid]
    assert entries
    assert all(e.get("userId") == u1["userId"] for e in entries)
    assert all(e.get("nickname") == "claimer1" for e in entries)

    daily_data = daily_runs._load()
    daily_matched = [
        r
        for r in (daily_data.get("runs") or {}).values()
        if isinstance(r, dict) and r.get("terminalId") == tid
    ]
    assert daily_matched
    assert all(r.get("userId") == u1["userId"] for r in daily_matched)
    assert all(r.get("nickname") == "claimer1" for r in daily_matched)

    with pytest.raises(ValueError, match="已认领|认领"):
        users.claim_terminal(u2["userId"], tid)


def test_claim_terminal_api():
    import uuid
    from app.terminals import register_terminal
    from app import scores

    client.cookies.clear()
    tid = str(uuid.uuid4())
    register_terminal(tid, "遗留终端")
    scores.submit_score(
        tid,
        "stroop",
        "challenge",
        "normal",
        {"correct": 3, "total": 5, "timeMs": 4000},
    )

    anon = client.post(url("/api/v1/auth/claim-terminal"), json={"terminalId": tid})
    assert anon.status_code in (401, 403)

    login_as(client, "claimapi1")
    ok = client.post(url("/api/v1/auth/claim-terminal"), json={"terminalId": tid})
    assert ok.status_code == 200
    body = ok.json()
    assert body["ok"] is True
    assert body["terminalId"] == tid
    assert body["userId"]

    entries = [e for e in scores._load_entries() if e.get("terminalId") == tid]
    assert entries
    assert all(e.get("userId") == body["userId"] for e in entries)
    assert all(e.get("nickname") == "claimapi1" for e in entries)

    client.cookies.clear()
    login_as(client, "claimapi2")
    again = client.post(url("/api/v1/auth/claim-terminal"), json={"terminalId": tid})
    assert again.status_code == 400
    assert "认领" in again.json()["detail"]
