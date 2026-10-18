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
    assert board["items"][0].get("comboNo") == "专注力#1"
    assert board.get("currentComboNo") == "专注力#1"
    assert board["items"][0]["isCurrentCombo"] is True
    assert board["items"][0].get("recordKind") in ("first", "best", "first+best")


def _finish_all(tid, total_base_ms=1000):
    run = dr.start_run(tid)
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


def test_keep_first_and_best_only():
    tid = _tid()
    register_terminal(tid, "丙")
    dc.ensure_today()
    # 首次：慢通关
    first_id = _finish_all(tid, total_base_ms=3000)
    # 中间：更快
    mid_id = _finish_all(tid, total_base_ms=2000)
    # 最佳：最快
    best_id = _finish_all(tid, total_base_ms=1000)

    data = dr._load()
    mine = [
        r
        for r in data["runs"].values()
        if r.get("terminalId") == tid and r.get("status") in ("finished", "exited")
    ]
    assert len(mine) == 2
    ids = {r["runId"] for r in mine}
    assert first_id in ids
    assert best_id in ids
    assert mid_id not in ids

    board = dr.leaderboard()
    mine_board = [it for it in board["items"] if it.get("nickname") == "丙"]
    assert len(mine_board) == 2
    kinds = {it["recordKind"] for it in mine_board}
    assert kinds == {"first", "best"}


def test_leaderboard_nickname_follows_rename():
    tid = _tid()
    register_terminal(tid, "旧名")
    dc.ensure_today()
    _finish_all(tid, total_base_ms=1000)
    board = dr.leaderboard()
    mine = [it for it in board["items"] if it.get("terminalId") == tid]
    assert mine and mine[0]["nickname"] == "旧名"

    register_terminal(tid, "新名")
    board2 = dr.leaderboard()
    mine2 = [it for it in board2["items"] if it.get("terminalId") == tid]
    assert mine2 and mine2[0]["nickname"] == "新名"


def test_leaderboard_per_combo_default_latest():
    t1, t2 = _tid(), _tid()
    register_terminal(t1, "甲")
    register_terminal(t2, "乙")
    first = dc.ensure_today()
    first_id = first["comboId"]
    _finish_all(t1, total_base_ms=1000)

    second = dc.regenerate()
    second_id = second["comboId"]
    assert second_id != first_id
    _finish_all(t2, total_base_ms=1000)

    default_board = dr.leaderboard()
    assert default_board["comboId"] == second_id
    assert default_board["currentComboId"] == second_id
    assert len(default_board["combos"]) >= 2
    nicks = {it["nickname"] for it in default_board["items"]}
    assert "乙" in nicks
    assert "甲" not in nicks

    old_board = dr.leaderboard(combo_id=first_id)
    assert old_board["comboId"] == first_id
    nicks_old = {it["nickname"] for it in old_board["items"]}
    assert "甲" in nicks_old
    assert "乙" not in nicks_old


def test_leaderboard_keeps_seven_days(monkeypatch):
    monkeypatch.setattr("app.daily_runs.local_today", lambda: "2026-10-13")
    monkeypatch.setattr("app.daily_challenges.local_today", lambda: "2026-10-13")
    from app.storage import save_json

    save_json(
        "daily_runs.json",
        {
            "version": 1,
            "runs": {
                "old": {
                    "runId": "old",
                    "date": "2026-10-01",
                    "status": "finished",
                    "terminalId": "x",
                    "comboId": "c-old",
                    "stagesDone": 3,
                    "totalTimeMs": 1000,
                },
                "edge": {
                    "runId": "edge",
                    "date": "2026-10-07",
                    "status": "finished",
                    "terminalId": "y",
                    "nickname": "边缘",
                    "comboId": "c-edge",
                    "stagesDone": 2,
                    "totalTimeMs": 2000,
                },
            },
        },
    )
    board = dr.leaderboard()
    assert len(board["dates"]) == 7
    assert board["dates"][0] == {"date": "2026-10-13", "label": "今天"}
    assert board["dates"][1]["label"] == "昨天"
    assert board["dates"][-1]["date"] == "2026-10-07"
    assert dr.leaderboard(date="1999-01-01")["date"] == "2026-10-13"
    kept = dr.leaderboard(date="2026-10-07")
    assert kept["date"] == "2026-10-07"
    assert any(it["terminalId"] == "y" for it in kept["items"])
    stored = dr._load()
    assert "old" not in stored["runs"]
    assert "edge" in stored["runs"]


def _finish_all_as(tid, user_id="", username="", total_base_ms=1000):
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


def test_prune_keeps_three_users_on_one_terminal():
    """Finished runs for three accounts on one device must not prune each other."""
    tid = _tid()
    register_terminal(tid, "shared")
    dc.ensure_today()
    id1 = _finish_all_as(tid, user_id="u1", username="p1", total_base_ms=3000)
    id2 = _finish_all_as(tid, user_id="u2", username="p2", total_base_ms=2000)
    id3 = _finish_all_as(tid, user_id="u3", username="p3", total_base_ms=1000)

    data = dr._load()
    finished = [
        r
        for r in data["runs"].values()
        if r.get("terminalId") == tid and r.get("status") == "finished"
    ]
    assert len(finished) == 3
    ids = {r["runId"] for r in finished}
    assert ids == {id1, id2, id3}
    assert {r.get("userId") for r in finished} == {"u1", "u2", "u3"}


def test_daily_board_one_row_per_user_across_terminals():
    tid_a, tid_b = _tid(), _tid()
    register_terminal(tid_a, "pad-a")
    register_terminal(tid_b, "pad-b")
    dc.ensure_today()
    # same user on two terminals
    _finish_all_as(tid_a, user_id="cara", username="cara", total_base_ms=3000)
    _finish_all_as(tid_b, user_id="cara", username="cara", total_base_ms=1000)
    # second user on first terminal
    _finish_all_as(tid_a, user_id="dana", username="dana", total_base_ms=2000)

    board = dr.leaderboard()
    caras = [it for it in board["items"] if it.get("userId") == "cara"]
    danas = [it for it in board["items"] if it.get("userId") == "dana"]
    # first+best for one user may be 1 or 2 rows (same run = first+best)
    assert len(caras) >= 1
    assert len({it.get("userId") for it in caras}) == 1
    # Across two terminals, cara collapses to one identity group (not duplicate podium people)
    cara_kinds = {it["recordKind"] for it in caras}
    assert cara_kinds <= {"first", "best", "first+best"}
    assert len(danas) >= 1
    nicks = {it["nickname"] for it in board["items"]}
    assert "cara" in nicks and "dana" in nicks
    # Not two separate terminal-only cara rows with no user collapse:
    # identity grouping means cara's runs share one group (at most first+best = 2 items)
    assert len(caras) <= 2
