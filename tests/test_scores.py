import uuid

from fastapi.testclient import TestClient

from helpers import login_as, url
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
    tid = str(uuid.uuid4())
    headers = {"X-Terminal-Id": tid}
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": tid, "nickname": "测试玩家"},
    )
    login_as(client, "score_player")
    payload = {
        "gameId": "stroop",
        "mode": "challenge",
        "tier": "normal",
        "metrics": {"correct": 28, "total": 30, "timeMs": 58000, "maxStreak": 8},
    }
    r = client.post(url("/api/v1/scores"), json=payload, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["isPersonalBest"] is True
    assert body["entry"]["userId"]
    assert body["entry"]["nickname"] == "score_player"

    board = client.get(
        url("/api/v1/leaderboard"),
        params={"gameId": "stroop", "mode": "challenge", "tier": "normal"},
    )
    assert board.status_code == 200
    items = board.json()["items"]
    mine = [it for it in items if it.get("terminalId") == tid]
    assert mine and mine[0]["nickname"] == "score_player"

    bests = client.get(url("/api/v1/scores/me/bests"), headers=headers)
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
    tid = str(uuid.uuid4())
    headers = {"X-Terminal-Id": tid}
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": tid, "nickname": "测试玩家"},
    )
    login_as(client, "score_player")
    client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 10, "total": 10, "timeMs": 30000},
        },
        headers=headers,
    )
    r = client.get(url("/api/v1/leaderboard/global"), params={"limit": 10})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    mine = [it for it in items if it.get("terminalId") == tid]
    assert mine and mine[0]["nickname"] == "score_player"
    assert "display" in mine[0]
    assert "playedAt" in mine[0]
    assert "gameId" not in mine[0]


def test_recent_leaderboard():
    tid = str(uuid.uuid4())
    headers = {"X-Terminal-Id": tid}
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": tid, "nickname": "测试玩家"},
    )
    login_as(client, "score_player")
    client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 12, "total": 12, "timeMs": 28000},
        },
        headers=headers,
    )
    r = client.get(url("/api/v1/leaderboard/recent"), params={"limit": 20})
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "recent"
    items = data["items"]
    assert len(items) >= 1
    first = next(it for it in items if it.get("terminalId") == tid)
    assert first["nickname"] == "score_player"
    assert first["gameId"] == "stroop"
    assert first["gameTitle"] == "Stroop 色字"
    assert first["modeLabel"] == "挑战"
    assert "display" in first
    assert "playedAt" in first


def test_leaderboard_nickname_follows_rename(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    tid = str(uuid.uuid4())
    from app import scores
    from app.terminals import register_terminal

    register_terminal(tid, "旧名")
    scores.submit_score(
        tid,
        "stroop",
        "challenge",
        "normal",
        {"correct": 20, "total": 20, "timeMs": 40000},
    )
    board = scores.get_leaderboard("stroop", "challenge", "normal")
    assert board["items"][0]["nickname"] == "旧名"

    register_terminal(tid, "新名")
    board2 = scores.get_leaderboard("stroop", "challenge", "normal")
    assert board2["items"][0]["nickname"] == "新名"
    recent = scores.get_recent_leaderboard(limit=5)
    assert recent["items"][0]["nickname"] == "新名"


def test_yuwen_board_accuracy_then_time(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    from app import scores
    from app.terminals import register_terminal

    high, faster, slower = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    register_terminal(high, "高正确率")
    register_terminal(faster, "同率更快")
    register_terminal(slower, "同率更慢")
    scores.submit_score(
        slower, "yuwen", "challenge", "zuyin", {"correct": 8, "total": 10, "timeMs": 40000}
    )
    scores.submit_score(
        faster, "yuwen", "challenge", "zuyin", {"correct": 4, "total": 5, "timeMs": 5000}
    )
    scores.submit_score(
        high, "yuwen", "challenge", "zuyin", {"correct": 9, "total": 10, "timeMs": 120000}
    )
    names = [item["nickname"] for item in scores.get_leaderboard("yuwen", "challenge", "zuyin")["items"]]
    assert names == ["高正确率", "同率更快", "同率更慢"]

    not_best = scores.submit_score(
        faster, "yuwen", "challenge", "zuyin", {"correct": 8, "total": 10, "timeMs": 30000}
    )
    assert not_best["isPersonalBest"] is False
    improved = scores.submit_score(
        faster, "yuwen", "challenge", "zuyin", {"correct": 9, "total": 10, "timeMs": 90000}
    )
    assert improved["isPersonalBest"] is True


def test_score_stores_user_id():
    client.cookies.clear()
    # brief: register as cara (login_as falls back if username already exists in shared store)
    login_as(client, "cara")
    tid = "22222222-2222-4222-8222-222222222222"
    client.post(url("/api/v1/terminals/register"), json={"terminalId": tid, "nickname": "cara"})
    r = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal",
              "metrics": {"correct": 1, "total": 1, "timeMs": 900}},
        headers={"X-Terminal-Id": tid},
    )
    assert r.status_code == 200
    assert r.json()["entry"]["userId"]
    assert r.json()["entry"]["nickname"] == "cara"  # or username field per chosen schema
