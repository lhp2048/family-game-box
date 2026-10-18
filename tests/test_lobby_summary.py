import uuid

import pytest

from app import daily_challenges as dc
from app import daily_runs as dr
from app import lobby
from app import scores
from app import users
from app.terminals import register_terminal


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    yield


def _tid():
    return str(uuid.uuid4())


def _finish_run(tid, total_base_ms=1000, user_id="", username=""):
    run = dr.start_run(tid, user_id=user_id, username=username)
    n = len(run["stages"])
    for i in range(n):
        st = run["stages"][i]
        action = "finish" if i == n - 1 else "stage_done"
        dr.patch_run(
            tid,
            run["runId"],
            {
                "action": action,
                "stageIndex": i,
                "timeMs": 800,
                "totalTimeMs": (i + 1) * total_base_ms,
                "stage": {
                    "gameId": st["gameId"],
                    "tier": st["tier"],
                    "timeMs": 800,
                    "completed": True,
                },
            },
        )
    return run["runId"]


def test_summary_empty_no_terminal():
    data = lobby.get_lobby_summary(None)
    assert "date" in data
    assert data["me"]["nickname"] is None
    assert data["me"]["dailyRank"] is None
    assert data["podium"] == []
    assert data["recent"] is None
    assert data["daily"]["cta"] == "start"
    assert data["daily"]["myProgressLabel"] == "未开始"


def test_summary_podium_and_gap():
    dc.ensure_today()
    t1, t2 = _tid(), _tid()
    register_terminal(t1, "甲")
    register_terminal(t2, "乙")
    _finish_run(t1, total_base_ms=1000)
    _finish_run(t2, total_base_ms=2000)
    data = lobby.get_lobby_summary(t2)
    assert data["me"]["nickname"] == "乙"
    assert data["me"]["dailyRank"] == 2
    assert data["me"]["dailyStatus"] == "finished"
    assert len(data["podium"]) >= 1
    assert data["podium"][0]["nickname"] == "甲"
    assert data["me"]["gapToFirstMs"] is not None
    assert data["me"]["gapToFirstMs"] > 0
    assert "落后" in data["me"]["gapLabel"]
    assert data["daily"]["cta"] == "view"
    assert data["daily"]["myProgressLabel"] == "已通关"


def test_summary_podium_only_current_combo():
    first = dc.ensure_today()
    t1, t2 = _tid(), _tid()
    register_terminal(t1, "甲")
    register_terminal(t2, "乙")
    _finish_run(t1, total_base_ms=1000)
    dc.regenerate()
    _finish_run(t2, total_base_ms=1000)
    data = lobby.get_lobby_summary(t2)
    names = [p["nickname"] for p in data["podium"]]
    assert "乙" in names
    assert "甲" not in names
    assert data["me"]["dailyStatus"] == "finished"
    # 旧挑战成绩不影响当前场「我的」状态
    data_old_player = lobby.get_lobby_summary(t1)
    assert data_old_player["me"]["dailyStatus"] == "absent"
    assert first["comboId"] != dc.get_current()["comboId"]


def test_summary_recent_score():
    dc.ensure_today()
    tid = _tid()
    register_terminal(tid, "丙")
    scores.submit_score(
        tid,
        "schulte",
        "casual",
        "normal",
        {"timeMs": 12345, "errors": 0},
        display="12.3s",
    )
    data = lobby.get_lobby_summary(tid)
    assert data["recent"] is not None
    assert data["recent"]["gameId"] == "schulte"
    assert data["recent"]["display"]


def test_summary_prefers_user_identity_across_terminals():
    """Logged-in user sees 'me' / recent from userId even on a different terminal."""
    dc.ensure_today()
    created = users.register_user("lobby_user", "pass1234")
    uid = created["userId"]
    t1, t2 = _tid(), _tid()
    register_terminal(t1, "设备甲")
    register_terminal(t2, "设备乙")
    _finish_run(t1, total_base_ms=1500, user_id=uid, username="lobby_user")
    scores.submit_score(
        t1,
        "schulte",
        "casual",
        "normal",
        {"timeMs": 9999, "errors": 0},
        display="10.0s",
        user_id=uid,
        username="lobby_user",
    )
    # Other terminal, same user — no local terminal history
    data = lobby.get_lobby_summary(t2, user_id=uid)
    assert data["me"]["nickname"] == "lobby_user"
    assert data["me"]["dailyStatus"] == "finished"
    assert data["me"]["dailyRank"] == 1
    assert data["daily"]["cta"] == "view"
    assert data["recent"] is not None
    assert data["recent"]["gameId"] == "schulte"
    # Without user_id, empty terminal has no me progress
    bare = lobby.get_lobby_summary(t2)
    assert bare["me"]["dailyStatus"] == "absent"
    assert bare["recent"] is None


def test_lobby_summary_http():
    from fastapi.testclient import TestClient
    from helpers import url
    from app.main import app

    client = TestClient(app)
    r = client.get(url("/api/v1/lobby/summary"))
    assert r.status_code == 200
    body = r.json()
    assert "podium" in body and "daily" in body and "me" in body


def test_lobby_summary_http_with_user_cookie():
    from fastapi.testclient import TestClient
    from helpers import login_as, url
    from app.main import app

    client = TestClient(app)
    login_as(client, "lobby_http")
    tid = _tid()
    client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": tid, "nickname": "ignored"},
    )
    # finish via API would need more setup; unit path already covers userId.
    # Just ensure cookie does not 500 and me nickname comes from username when present.
    r = client.get(url("/api/v1/lobby/summary"), headers={"X-Terminal-Id": tid})
    assert r.status_code == 200
    body = r.json()
    assert body["me"]["nickname"] == "lobby_http"
