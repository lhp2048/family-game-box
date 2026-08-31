import uuid

import pytest

from app import daily_challenges as dc
from app import daily_runs as dr
from app.terminals import register_terminal


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def _tid():
    return str(uuid.uuid4())


def test_start_exit_and_finish_leaderboard():
    t1, t2 = _tid(), _tid()
    register_terminal(t1, "甲")
    register_terminal(t2, "乙")
    dc.ensure_today()
    r1 = dr.start_run(t1)
    assert r1["status"] == "running"
    dr.patch_run(
        t1,
        r1["runId"],
        {
            "action": "stage_done",
            "stageIndex": 0,
            "timeMs": 1000,
            "totalTimeMs": 1200,
            "stage": {"gameId": "24points", "tier": "normal", "timeMs": 1000, "completed": True},
        },
    )
    exited = dr.patch_run(
        t1,
        r1["runId"],
        {
            "action": "exit",
            "totalTimeMs": 5000,
            "stage": {"gameId": "schulte", "tier": "normal", "timeMs": 500, "completed": False},
        },
    )
    assert exited["status"] == "exited"
    assert exited["stagesDone"] == 1

    r2 = dr.start_run(t2)
    n = len(r2["stages"])
    for i in range(n):
        st = r2["stages"][i]
        action = "finish" if i == n - 1 else "stage_done"
        dr.patch_run(
            t2,
            r2["runId"],
            {
                "action": action,
                "stageIndex": i,
                "timeMs": 800,
                "totalTimeMs": (i + 1) * 1000,
                "stage": {
                    "gameId": st["gameId"],
                    "tier": st["tier"],
                    "timeMs": 800,
                    "completed": True,
                },
            },
        )
    board = dr.leaderboard()
    assert board["items"][0]["nickname"] == "乙"
    assert board["items"][0]["status"] == "finished"
    assert board["items"][1]["status"] == "exited"
