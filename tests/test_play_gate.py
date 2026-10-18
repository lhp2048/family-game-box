import time

import pytest

from app import daily_admin as da


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    da.clear_play_gate_cache()
    yield
    da.clear_play_gate_cache()


def test_cannot_enable_without_passphrase():
    with pytest.raises(ValueError):
        da.put_play_gate(True, None)


def test_unlock_and_invalidate_on_change():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    assert da.play_cookie_ok(cookie, now=now) is True
    assert da.play_cookie_ok("bad", now=now) is False
    with pytest.raises(ValueError, match="口令不对"):
        da.issue_play_cookie("nope", now=now)
    da.put_play_gate(True, "family2")
    assert da.play_cookie_ok(cookie, now=now) is False


def test_disable_keeps_generation():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    first = da._load()["playGeneration"]
    da.put_play_gate(False, None)
    assert da._load()["playGeneration"] == first
    da.put_play_gate(True, None)
    assert da._load()["playGeneration"] == first + 1
    assert da.play_cookie_ok(cookie, now=now) is False


import uuid

from fastapi.testclient import TestClient

from helpers import login_as, url
from app.main import app

client = TestClient(app)
TERMINAL = str(uuid.uuid4())


def _play_on():
    client.cookies.clear()
    da.setup_password("secret123")
    token = da.login("secret123")["token"]
    client.put(
        url("/api/v1/admin/play-gate"),
        json={"enabled": True, "passphrase": "family"},
        headers={"X-Admin-Token": token},
    )
    client.post(url("/api/v1/terminals/register"), json={"terminalId": TERMINAL, "nickname": "小明"})
    return token


def test_gate_off_allows_score():
    client.post(url("/api/v1/terminals/register"), json={"terminalId": TERMINAL, "nickname": "小明"})
    login_as(client, "gate_off_player")
    response = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers={"X-Terminal-Id": TERMINAL},
    )
    assert response.status_code == 200


def test_gated_score_post_storage_failure_returns_503(monkeypatch):
    from app.storage import StorageError

    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)

    def fail_load(*_args, **_kwargs):
        raise StorageError("暂时存不上")

    monkeypatch.setattr("app.daily_admin.load_json", fail_load)
    client.post(url("/api/v1/terminals/register"), json={"terminalId": TERMINAL, "nickname": "小明"})
    response = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers={"X-Terminal-Id": TERMINAL},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "暂时存不上"


def test_gate_on_blocks_score_and_today_until_unlock():
    _play_on()
    headers = {"X-Terminal-Id": TERMINAL}
    blocked = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers=headers,
    )
    assert blocked.status_code == 401
    assert client.get(url("/api/v1/daily/today")).status_code == 401
    assert client.get(url("/api/v1/leaderboard/recent")).status_code == 200
    page = client.get(url("/daily"), follow_redirects=False)
    assert page.status_code == 307
    assert "/play-gate?next=" in page.headers["location"]
    bad = client.post(url("/api/v1/play-gate/unlock"), json={"passphrase": "nope"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "口令不对"
    ok = client.post(url("/api/v1/play-gate/unlock"), json={"passphrase": "family"})
    assert ok.status_code == 200
    login_as(client, "gate_on_player", passphrase="family")
    unlocked = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers=headers,
    )
    assert unlocked.status_code == 200


def test_safe_next_rejects_external():
    from app.play_gate import safe_next
    from app.root_path import with_root

    assert safe_next("//evil.example") == with_root("/")
    assert safe_next("/daily") == "/daily"


def test_safe_next_rejects_backslash_controls_and_protocol_relative():
    from pathlib import Path

    from app.play_gate import safe_next
    from app.root_path import with_root

    home = with_root("/")
    assert safe_next("/\\") == home
    assert safe_next("/%5C") == home
    assert safe_next("/foo\nbar") == home
    assert safe_next("/foo\x00bar") == home
    assert safe_next("/%2F/evil.example") == home
    assert safe_next("/daily") == "/daily"

    html = Path(__file__).resolve().parents[1].joinpath("web/play-gate.html").read_text(encoding="utf-8")
    assert "decodeURIComponent" in html
    assert 'indexOf("\\\\")' in html or 'indexOf("\\")' in html
    assert "charCodeAt" in html
    assert 'startsWith("//")' in html


def test_admin_token_allows_daily_today_without_play_cookie():
    from pathlib import Path

    html = Path(__file__).resolve().parents[1].joinpath("web/admin.html").read_text(encoding="utf-8")
    assert 'api("/api/v1/daily/today", { admin: true })' in html
    assert 'err.message !== "需要口令"' in html
    token = _play_on()
    response = client.get(
        url("/api/v1/daily/today"),
        headers={"X-Admin-Token": token},
    )
    assert response.status_code == 200


def test_uploaded_games_gated_like_games():
    client.cookies.clear()
    _play_on()
    page = client.get(url("/uploaded-games/pack-demo/index.html"), follow_redirects=False)
    assert page.status_code == 307
    assert "/play-gate?next=" in page.headers["location"]


def test_issue_play_cookie_strips_passphrase():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("  family  ", now=now)
    assert da.play_cookie_ok(cookie, now=now) is True


def test_play_cookie_ok_non_ascii_signature():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    bad = cookie.rsplit(".", 1)[0] + ".签名"
    assert da.play_cookie_ok(bad, now=now) is False


def test_play_gate_cache_avoids_repeat_reads(monkeypatch):
    da.put_play_gate(True, "family")
    da.put_play_gate(False, None)
    calls = {"n": 0}
    real = da.load_json

    def wrapped(name, default):
        calls["n"] += 1
        return real(name, default)

    monkeypatch.setattr(da, "load_json", wrapped)
    from app.play_gate import allowed

    assert allowed("GET", "/games/stroop/index.html", None, None) is True
    first = calls["n"]
    assert first >= 1
    assert allowed("GET", "/games/simon/index.html", None, None) is True
    assert allowed("GET", "/games/simon/audio/x.mp3", None, None) is True
    assert calls["n"] == first
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    after_issue = calls["n"]
    assert da.play_cookie_ok(cookie, now=now) is True
    filled = calls["n"]
    assert da.play_cookie_ok(cookie, now=now) is True
    assert da.play_cookie_ok(cookie, now=now) is True
    assert calls["n"] == filled
    da.put_play_gate(True, None)
    assert allowed("GET", "/games/stroop/index.html", None, None) is False
    assert calls["n"] > after_issue


def test_health_not_blocked_when_turso_unconfigured(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    response = client.get(url("/api/v1/health"))
    assert response.status_code == 200
    body = response.json()
    assert body["storage"] == "turso"
    assert body["ready"] is False
    assert body["status"] == "not_ready"
