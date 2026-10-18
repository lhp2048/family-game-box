import time

import pytest

from app import daily_admin as da


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)


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

from helpers import url
from app.main import app

client = TestClient(app)
TERMINAL = str(uuid.uuid4())


def _play_on():
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
    response = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers={"X-Terminal-Id": TERMINAL},
    )
    assert response.status_code == 200


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
