import uuid

import pytest
from fastapi.testclient import TestClient

from helpers import login_as, url
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    return TestClient(app)


def _headers(tid):
    return {"X-Terminal-Id": tid}


def test_register_and_me(client):
    tid = str(uuid.uuid4())
    r = client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": tid, "nickname": "测试玩家"},
    )
    assert r.status_code == 200
    assert r.json()["registered"] is True
    assert r.json()["nickname"] == "测试玩家"

    me = client.get(url("/api/v1/terminals/me"), headers=_headers(tid))
    assert me.status_code == 200
    assert me.json()["registered"] is True


def test_submit_score_and_leaderboard(client):
    tid = str(uuid.uuid4())
    headers = _headers(tid)
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
    uid = body["entry"]["userId"]

    board = client.get(
        url("/api/v1/leaderboard"),
        params={"gameId": "stroop", "mode": "challenge", "tier": "normal"},
    )
    assert board.status_code == 200
    items = board.json()["items"]
    mine = [it for it in items if it.get("userId") == uid or it.get("terminalId") == tid]
    assert mine and mine[0]["nickname"] == "score_player"

    bests = client.get(url("/api/v1/scores/me/bests"), headers=headers)
    assert bests.status_code == 200
    assert "stroop" in bests.json()["bests"]


def test_rank_meta(client):
    r = client.get(url("/api/v1/rank/meta"))
    assert r.status_code == 200
    data = r.json()
    assert any(g["id"] == "24points" for g in data["games"])
    assert "intro" in data["tiers"]["24points"]
    standard = ["intro", "simple", "normal", "hard", "master", "god"]
    for gid in ("stroop", "cancel", "simon", "spot-diff", "maze", "sudoku"):
        assert data["tiers"][gid] == standard


def test_global_leaderboard(client):
    tid = str(uuid.uuid4())
    headers = _headers(tid)
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


def test_recent_leaderboard(client):
    tid = str(uuid.uuid4())
    headers = _headers(tid)
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
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
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
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
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


def test_score_stores_user_id(client):
    client.cookies.clear()
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
    assert r.json()["entry"]["nickname"] == "cara"


def test_leaderboard_one_row_per_user(tmp_path, monkeypatch):
    """Bound scores collapse to one board row per userId (best across terminals)."""
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    from app import scores
    from app.terminals import register_terminal

    t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
    register_terminal(t1, "a")
    register_terminal(t2, "b")
    uid = "user-same"
    scores.submit_score(
        t1, "stroop", "challenge", "normal",
        {"correct": 10, "total": 10, "timeMs": 40000},
        user_id=uid, username="same_user",
    )
    scores.submit_score(
        t2, "stroop", "challenge", "normal",
        {"correct": 10, "total": 10, "timeMs": 20000},
        user_id=uid, username="same_user",
    )
    board = scores.get_leaderboard("stroop", "challenge", "normal")
    mine = [it for it in board["items"] if it.get("userId") == uid]
    assert len(mine) == 1
    assert mine[0]["nickname"] == "same_user"


def test_personal_bests_prefer_session_user(client):
    """Shared device: /scores/me/bests with user cookie returns only that user's PBs."""
    client.cookies.clear()
    tid = str(uuid.uuid4())
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": tid, "nickname": "pad"},
    )
    headers = _headers(tid)

    login_as(client, "alice_pb")
    r_a = client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 30, "total": 30, "timeMs": 20000},
        },
        headers=headers,
    )
    assert r_a.status_code == 200
    alice_uid = r_a.json()["entry"]["userId"]
    alice_score = r_a.json()["entry"]["score"]

    client.post(url("/api/v1/auth/logout"))
    client.cookies.clear()
    login_as(client, "bob_pb")
    r_b = client.post(
        url("/api/v1/scores"),
        json={
            "gameId": "stroop",
            "mode": "challenge",
            "tier": "normal",
            "metrics": {"correct": 10, "total": 30, "timeMs": 50000},
        },
        headers=headers,
    )
    assert r_b.status_code == 200
    bob_uid = r_b.json()["entry"]["userId"]
    bob_score = r_b.json()["entry"]["score"]
    assert bob_uid != alice_uid
    assert bob_score < alice_score

    # Bob's session: must see Bob's weaker PB, not Alice's stronger one
    bests_bob = client.get(url("/api/v1/scores/me/bests"), headers=headers)
    assert bests_bob.status_code == 200
    body_bob = bests_bob.json()
    assert body_bob.get("userId") == bob_uid
    stroop_bob = body_bob["bests"]["stroop"]["challenge"]["normal"]
    assert stroop_bob["score"] == bob_score

    client.post(url("/api/v1/auth/logout"))
    client.cookies.clear()
    login_as(client, "alice_pb")
    bests_alice = client.get(url("/api/v1/scores/me/bests"), headers=headers)
    assert bests_alice.status_code == 200
    body_alice = bests_alice.json()
    assert body_alice.get("userId") == alice_uid
    stroop_alice = body_alice["bests"]["stroop"]["challenge"]["normal"]
    assert stroop_alice["score"] == alice_score
