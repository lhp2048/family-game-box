"""每日语文挑战：同一天同一份卷子，服务端判分，榜与专注力挑战分开。"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from helpers import login_as, url
from app.main import app
from app import yuwen_daily as yd
from app.terminals import register_terminal

client = TestClient(app)


def _tid() -> str:
    return str(uuid.uuid4())


def test_same_day_same_paper():
    a = yd.paper_for("2026-10-11")
    b = yd.paper_for("2026-10-11")
    c = yd.paper_for("2026-10-12")
    assert [q["id"] for q in a["questions"]] == [q["id"] for q in b["questions"]]
    assert len(a["questions"]) == 10
    assert [q["id"] for q in a["questions"]] != [q["id"] for q in c["questions"]]
    assert "answer" not in a["questions"][0]
    assert a["title"] == "每日语文挑战"


def test_grade_lock_and_leaderboard(monkeypatch, tmp_path):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.yuwen_daily.local_today", lambda: "2026-10-11")
    monkeypatch.setattr("app.daily_challenges.local_today", lambda: "2026-10-11")
    tid = _tid()
    register_terminal(tid, "小卷")
    login_as(client, "yuwen_grade")
    paper = yd.paper_for("2026-10-11")
    first = paper["questions"][0]
    headers = {"X-Terminal-Id": tid}
    opened = client.get(url("/api/v1/yuwen-daily/today"), headers=headers)
    assert opened.status_code == 200
    assert opened.json()["paperId"] == paper["paperId"]

    wrong = client.post(
        url("/api/v1/yuwen-daily/answer"),
        headers=headers,
        json={"paperId": paper["paperId"], "questionId": first["id"], "choice": "A", "timeMs": 1000},
    )
    assert wrong.status_code == 200
    locked = wrong.json()["choice"]
    again = client.post(
        url("/api/v1/yuwen-daily/answer"),
        headers=headers,
        json={"paperId": paper["paperId"], "questionId": first["id"], "choice": "B", "timeMs": 50},
    )
    assert again.status_code == 200
    assert again.json()["choice"] == locked

    from app.yuwen_daily import _question_map

    qmap = _question_map()
    for q in paper["questions"]:
        if q["id"] == first["id"]:
            continue
        answer = qmap[q["id"]]["answer"]
        got = client.post(
            url("/api/v1/yuwen-daily/answer"),
            headers=headers,
            json={"paperId": paper["paperId"], "questionId": q["id"], "choice": answer, "timeMs": 5000},
        )
        assert got.status_code == 200
        assert got.json()["correct"] is True

    finished = client.post(
        url("/api/v1/yuwen-daily/finish"),
        headers=headers,
        json={"paperId": paper["paperId"], "timeMs": 8000},
    )
    assert finished.status_code == 200
    body = finished.json()
    assert body["rank"] == 1
    shown = body["run"]["display"]
    assert shown.startswith("正确率 90% · 9/10") or shown.startswith("正确率 100% · 10/10")

    board = client.get(url("/api/v1/yuwen-daily/leaderboard"))
    assert board.status_code == 200
    assert board.json()["title"] == "语文挑战榜"
    assert board.json()["items"][0]["nickname"] == "yuwen_grade"

    page = client.get(url("/yuwen-daily"))
    assert page.status_code == 200
    assert "每日语文挑战" in page.text
    board_page = client.get(url("/yuwen-daily/leaderboard"))
    assert "语文挑战榜" in board_page.text
    assert "正确率优先，相同再比用时" in board_page.text
    assert "date-tabs" in board_page.text
    assert 'id="podium"' in board_page.text
    assert "冠军" in board_page.text


def test_wrong_answer_adds_five_seconds(monkeypatch, tmp_path):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.yuwen_daily.local_today", lambda: "2026-10-14")
    tid = _tid()
    register_terminal(tid, "罚时")
    login_as(client, "yuwen_penalty")
    paper = yd.paper_for("2026-10-14")
    headers = {"X-Terminal-Id": tid}
    opened = client.get(url("/api/v1/yuwen-daily/today"), headers=headers)
    assert opened.status_code == 200
    qmap = yd._question_map()
    wrong = 0
    for index, question in enumerate(paper["questions"]):
        answer = qmap[question["id"]]["answer"]
        choice = answer if index else ("B" if answer != "B" else "A")
        if choice != answer:
            wrong += 1
        got = client.post(
            url("/api/v1/yuwen-daily/answer"),
            headers=headers,
            json={"paperId": paper["paperId"], "questionId": question["id"], "choice": choice, "timeMs": 1000},
        )
        assert got.status_code == 200
    finished = client.post(
        url("/api/v1/yuwen-daily/finish"),
        headers=headers,
        json={"paperId": paper["paperId"], "timeMs": 1000},
    )
    assert finished.status_code == 200
    assert wrong == 1
    assert finished.json()["run"]["timeMs"] == 1000 + yd.WRONG_PENALTY_MS
    page = client.get(url("/yuwen-daily"))
    assert "答错一题，用时加 5 秒" in page.text


def test_board_prefers_accuracy_then_time(monkeypatch, tmp_path):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.yuwen_daily.local_today", lambda: "2026-10-11")

    def run(tid: str, nick: str, correct: int, total: int, time_ms: int) -> dict:
        register_terminal(tid, nick)
        return {
            "runId": tid,
            "paperId": "yuwen-2026-10-11",
            "date": "2026-10-11",
            "terminalId": tid,
            "nickname": nick,
            "status": "finished",
            "correct": correct,
            "total": total,
            "timeMs": time_ms,
            "display": "",
        }

    high, faster, slower = _tid(), _tid(), _tid()
    yd._save(
        {
            "version": 1,
            "runs": {
                high: run(high, "高正确率", 9, 10, 90000),
                faster: run(faster, "同率更快", 4, 5, 3000),
                slower: run(slower, "同率更慢", 8, 10, 20000),
            },
        }
    )
    names = [item["nickname"] for item in yd.leaderboard("2026-10-11")["items"]]
    assert names == ["高正确率", "同率更快", "同率更慢"]


def test_board_keeps_seven_days(monkeypatch, tmp_path):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.yuwen_daily.local_today", lambda: "2026-10-13")
    from app.storage import save_json

    save_json(
        "yuwen_daily_runs.json",
        {
            "version": 1,
            "runs": {
                "old": {
                    "runId": "old",
                    "date": "2026-10-01",
                    "status": "finished",
                    "terminalId": "old-terminal",
                    "nickname": "过期",
                    "correct": 10,
                    "total": 10,
                    "timeMs": 1000,
                },
                "edge": {
                    "runId": "edge",
                    "date": "2026-10-07",
                    "status": "finished",
                    "terminalId": "edge-terminal",
                    "nickname": "边缘",
                    "correct": 8,
                    "total": 10,
                    "timeMs": 4000,
                },
            },
        },
    )
    board = yd.leaderboard()
    assert len(board["dates"]) == 7
    assert board["dates"][0]["label"] == "今天"
    assert board["date"] == "2026-10-13"
    kept = yd.leaderboard("2026-10-07")
    assert [item["nickname"] for item in kept["items"]] == ["边缘"]
    assert yd.leaderboard("2026-09-01")["date"] == "2026-10-13"
    stored = yd._load()
    assert "old" not in stored["runs"]
    assert "edge" in stored["runs"]


def test_same_device_two_users_runs_isolated(monkeypatch, tmp_path):
    """Two accounts on one terminal keep separate yuwen runs; B cannot finish A's."""
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.yuwen_daily.local_today", lambda: "2026-10-18")
    monkeypatch.setattr("app.daily_challenges.local_today", lambda: "2026-10-18")
    tid = _tid()
    register_terminal(tid, "shared-pad")
    paper = yd.paper_for("2026-10-18")
    qmap = yd._question_map()
    first = paper["questions"][0]
    alice, bob = "user-alice", "user-bob"

    yd.answer_question(
        tid, paper["paperId"], first["id"], "A", 1000, user_id=alice, username="alice"
    )

    # Bob must not resume Alice's progress UI
    bob_today = yd.today_payload(tid, user_id=bob)
    assert bob_today["progress"]["status"] == "absent"

    alice_today = yd.today_payload(tid, user_id=alice)
    assert alice_today["progress"]["status"] == "running"
    assert len(alice_today["progress"]["answered"]) == 1
    assert alice_today["progress"]["answered"][0]["choice"] == "A"

    # Bob starts his own run with a different choice
    yd.answer_question(
        tid, paper["paperId"], first["id"], "B", 1000, user_id=bob, username="bob"
    )
    alice_today2 = yd.today_payload(tid, user_id=alice)
    assert alice_today2["progress"]["answered"][0]["choice"] == "A"
    bob_today2 = yd.today_payload(tid, user_id=bob)
    assert bob_today2["progress"]["answered"][0]["choice"] == "B"

    # Bob cannot finish Alice's (or his incomplete) run as a steal
    try:
        yd.finish_run(tid, paper["paperId"], 8000, user_id=bob, username="bob")
        raise AssertionError("bob should not finish incomplete/foreign run")
    except ValueError as exc:
        assert "paper not finished" in str(exc) or "challenge not started" in str(exc)

    # Complete Alice only; her finish must stay alice-bound
    for q in paper["questions"][1:]:
        yd.answer_question(
            tid,
            paper["paperId"],
            q["id"],
            qmap[q["id"]]["answer"],
            5000,
            user_id=alice,
            username="alice",
        )
    alice_fin = yd.finish_run(
        tid, paper["paperId"], 8000, user_id=alice, username="alice"
    )
    assert alice_fin["userId"] == alice

    # Bob still cannot claim Alice's finished run via finish
    try:
        stolen = yd.finish_run(tid, paper["paperId"], 8000, user_id=bob, username="bob")
        # If finish resolves Bob's incomplete run → paper not finished; never Alice
        assert stolen.get("userId") != alice
        raise AssertionError("expected ValueError for bob finish")
    except ValueError:
        pass

    data = yd._load()
    alice_runs = [r for r in data["runs"].values() if r.get("userId") == alice]
    bob_runs = [r for r in data["runs"].values() if r.get("userId") == bob]
    assert len(alice_runs) == 1 and alice_runs[0]["status"] == "finished"
    assert len(bob_runs) == 1 and bob_runs[0]["status"] == "running"
    assert alice_runs[0]["userId"] == alice


def test_yuwen_board_one_row_per_user_across_terminals(monkeypatch, tmp_path):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.yuwen_daily.local_today", lambda: "2026-10-18")
    t1, t2, t3 = _tid(), _tid(), _tid()
    register_terminal(t1, "a")
    register_terminal(t2, "b")
    register_terminal(t3, "c")
    cara = "user-cara"
    dana = "user-dana"

    def finished(tid, uid, uname, correct, time_ms):
        rid = str(uuid.uuid4())
        return {
            "runId": rid,
            "paperId": "yuwen-2026-10-18",
            "date": "2026-10-18",
            "terminalId": tid,
            "userId": uid,
            "username": uname,
            "nickname": uname,
            "status": "finished",
            "correct": correct,
            "total": 10,
            "timeMs": time_ms,
            "display": "",
        }

    r1 = finished(t1, cara, "cara", 9, 5000)
    r2 = finished(t2, cara, "cara", 10, 4000)  # better on second device
    r3 = finished(t3, dana, "dana", 8, 3000)
    # same terminal, second user
    r4 = finished(t1, dana, "dana", 7, 2000)
    yd._save(
        {
            "version": 1,
            "runs": {r["runId"]: r for r in (r1, r2, r3, r4)},
        }
    )
    items = yd.leaderboard("2026-10-18")["items"]
    caras = [it for it in items if it.get("userId") == cara]
    danas = [it for it in items if it.get("userId") == dana]
    assert len(caras) == 1
    assert caras[0]["correct"] == 10  # best across terminals
    assert caras[0]["nickname"] == "cara"
    assert len(danas) == 1
    # both users appear even though dana also played on cara's first terminal
    nicks = {it["nickname"] for it in items}
    assert nicks == {"cara", "dana"}

    # Lobby rank matches by user identity, not bare terminalId
    slice_cara = yd.lobby_slice(t1, user_id=cara)
    assert slice_cara["yuwenDaily"]["rank"] == caras[0]["rank"]
