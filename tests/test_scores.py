import uuid

from fastapi.testclient import TestClient

from helpers import url
from app.main import app

client = TestClient(app)
TERMINAL = str(uuid.uuid4())


def _headers():
    return {"X-Terminal-Id": TERMINAL}


def test_register_and_me():
    r = client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": TERMINAL, "nickname": "测试玩家"},
    )
    assert r.status_code == 200
    assert r.json()["registered"] is True
    assert r.json()["nickname"] == "测试玩家"

    me = client.get(url("/api/v1/terminals/me"), headers=_headers())
    assert me.status_code == 200
    assert me.json()["registered"] is True


def test_submit_score_and_leaderboard():
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": TERMINAL, "nickname": "测试玩家"},
    )
    payload = {
        "gameId": "stroop",
        "mode": "challenge",
        "tier": "normal",
        "metrics": {"correct": 28, "total": 30, "timeMs": 58000, "maxStreak": 8},
    }
    r = client.post(url("/api/v1/scores"), json=payload, headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["isPersonalBest"] is True

    board = client.get(
        url("/api/v1/leaderboard"),
        params={"gameId": "stroop", "mode": "challenge", "tier": "normal"},
    )
    assert board.status_code == 200
    items = board.json()["items"]
    assert len(items) >= 1
    assert items[0]["nickname"] == "测试玩家"

    bests = client.get(url("/api/v1/scores/me/bests"), headers=_headers())
    assert bests.status_code == 200
    assert "stroop" in bests.json()["bests"]


def test_rank_meta():
    r = client.get(url("/api/v1/rank/meta"))
    assert r.status_code == 200
    data = r.json()
    assert any(g["id"] == "24points" for g in data["games"])
    assert "intro" in data["tiers"]["24points"]
    standard = ["intro", "simple", "normal", "hard", "master", "god"]
    for gid in ("stroop", "cancel", "simon", "spot-diff", "maze", "sudoku"):
        assert data["tiers"][gid] == standard


def test_global_leaderboard():
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": TERMINAL, "nickname": "测试玩家"},
    )
    client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 10, "total": 10, "timeMs": 30000},
        },
        headers=_headers(),
    )
    r = client.get(url("/api/v1/leaderboard/global"), params={"limit": 10})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert items[0]["nickname"] == "测试玩家"
    assert "display" in items[0]
    assert "playedAt" in items[0]
    assert "gameId" not in items[0]


def test_recent_leaderboard():
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": TERMINAL, "nickname": "测试玩家"},
    )
    client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 12, "total": 12, "timeMs": 28000},
        },
        headers=_headers(),
    )
    r = client.get(url("/api/v1/leaderboard/recent"), params={"limit": 20})
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "recent"
    items = data["items"]
    assert len(items) >= 1
    first = items[0]
    assert first["nickname"] == "测试玩家"
    assert first["gameId"] == "stroop"
    assert first["gameTitle"] == "Stroop 色字"
    assert first["modeLabel"] == "挑战"
    assert "display" in first
    assert "playedAt" in first
