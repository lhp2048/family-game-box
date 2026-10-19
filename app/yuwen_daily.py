"""每日语文挑战：当天同一份卷子，服务端判分，独立排行。"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.daily_challenges import (
    board_dates_payload,
    clamp_board_date,
    local_today,
    prune_dated_runs,
)
from app.score_rules import accuracy_time_key, format_display
from app.storage import load_json, save_json
from app.scores import _board_identity_key
from app.terminals import get_terminal, nickname_lookup, resolve_nickname

ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "web" / "games" / "yuwen" / "questions.json"
STORE = "yuwen_daily_runs.json"
WRONG_PENALTY_MS = 5000

# 一份卷子：这些关各抽 1 题，顺序固定，题目随日期变。
PAPER_STAGES = [
    "zuyin",
    "zixing",
    "chengyu",
    "ciyu",
    "bingju",
    "biaodian",
    "mingju",
    "changshi",
    "gushi",
    "mingzhu",
]

_bank_cache: Optional[Dict[str, Any]] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_bank() -> Dict[str, Any]:
    global _bank_cache
    if _bank_cache is None:
        _bank_cache = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    return _bank_cache


def _stage_title(stage_id: str) -> str:
    for stage in _load_bank().get("stages") or []:
        if stage.get("id") == stage_id:
            return str(stage.get("title") or stage_id)
    return stage_id


def _question_map() -> Dict[int, Dict[str, Any]]:
    return {int(q["id"]): q for q in _load_bank().get("questions") or []}


def _display(correct: int, total: int, time_ms: int) -> str:
    return format_display(
        "yuwen",
        "challenge",
        {"correct": correct, "total": total, "timeMs": time_ms},
    )


def _run_key(run: Dict[str, Any]) -> tuple:
    return accuracy_time_key(
        {
            "correct": run.get("correct"),
            "total": run.get("total"),
            "timeMs": run.get("timeMs"),
        }
    )


def _public_question(q: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": int(q["id"]),
        "stage": q.get("stage") or "",
        "stageTitle": _stage_title(str(q.get("stage") or "")),
        "prompt": q.get("prompt") or "",
        "stem": q.get("stem") or "",
        "passage": q.get("passage") or "",
        "options": q.get("options") or {},
    }


def paper_for(day: str) -> Dict[str, Any]:
    rng = random.Random("yuwen-daily-v1:" + day)
    by_stage: Dict[str, List[Dict[str, Any]]] = {}
    for q in _load_bank().get("questions") or []:
        if q.get("group"):
            continue
        by_stage.setdefault(str(q.get("stage") or ""), []).append(q)
    picked: List[Dict[str, Any]] = []
    for stage_id in PAPER_STAGES:
        pool = by_stage.get(stage_id) or []
        if not pool:
            continue
        picked.append(pool[rng.randrange(len(pool))])
    return {
        "paperId": "yuwen-" + day,
        "date": day,
        "title": "每日语文挑战",
        "questions": [_public_question(q) for q in picked],
    }


def _empty() -> Dict[str, Any]:
    return {"version": 1, "runs": {}}


def _load() -> Dict[str, Any]:
    data = load_json(STORE, _empty())
    if not isinstance(data.get("runs"), dict):
        data["runs"] = {}
        return data
    if prune_dated_runs(data["runs"], local_today()):
        save_json(STORE, data)
    return data


def _save(data: Dict[str, Any]) -> None:
    runs = data.get("runs")
    if isinstance(runs, dict):
        prune_dated_runs(runs, local_today())
    save_json(STORE, data)


def _runs(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in (data.get("runs") or {}).values() if isinstance(r, dict)]


def _run_for(data: Dict[str, Any], terminal_id: str, paper_id: str) -> Optional[Dict[str, Any]]:
    """Latest unbound run for terminal+paper (ignores user-bound runs)."""
    found = [
        r
        for r in _runs(data)
        if r.get("terminalId") == terminal_id
        and r.get("paperId") == paper_id
        and not str(r.get("userId") or "").strip()
    ]
    if not found:
        return None
    found.sort(key=lambda r: str(r.get("startedAt") or ""))
    return found[-1]


def _run_for_user(data: Dict[str, Any], user_id: str, paper_id: str) -> Optional[Dict[str, Any]]:
    uid = str(user_id or "").strip()
    if not uid:
        return None
    found = [
        r
        for r in _runs(data)
        if str(r.get("userId") or "") == uid and r.get("paperId") == paper_id
    ]
    if not found:
        return None
    found.sort(key=lambda r: str(r.get("startedAt") or ""))
    return found[-1]


def _resolve_run(
    data: Dict[str, Any],
    terminal_id: str,
    paper_id: str,
    user_id: str = "",
) -> Optional[Dict[str, Any]]:
    uid = (user_id or "").strip()
    if uid:
        return _run_for_user(data, uid, paper_id)
    return _run_for(data, terminal_id, paper_id)


def _assert_run_owner(run: Dict[str, Any], user_id: str = "") -> None:
    """Refuse when an existing run belongs to a different logged-in user."""
    existing = str(run.get("userId") or "").strip()
    uid = (user_id or "").strip()
    if existing and uid and existing != uid:
        raise ValueError("not your challenge")
    if existing and not uid:
        raise ValueError("not your challenge")


def _elapsed_cap(run: Dict[str, Any]) -> int:
    started = str(run.get("startedAt") or "")
    try:
        then = datetime.fromisoformat(started)
    except ValueError:
        return 0
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - then
    return max(0, int(delta.total_seconds() * 1000))


def _reveal(q: Dict[str, Any], choice: str) -> Dict[str, Any]:
    answer = str(q.get("answer") or "")
    return {
        "id": int(q["id"]),
        "choice": choice,
        "correct": choice == answer,
        "answer": answer,
        "explain": q.get("explain") or "",
    }


def _progress(run: Optional[Dict[str, Any]], paper: Dict[str, Any]) -> Dict[str, Any]:
    total = len(paper["questions"])
    if not run:
        return {
            "status": "absent",
            "answered": [],
            "correct": 0,
            "total": total,
            "timeMs": 0,
            "display": "",
        }
    answers = run.get("answers") or {}
    revealed = []
    qmap = _question_map()
    for q in paper["questions"]:
        stored = answers.get(str(q["id"]))
        if not isinstance(stored, dict):
            continue
        full = qmap.get(int(q["id"]))
        if not full:
            continue
        revealed.append(_reveal(full, str(stored.get("choice") or "")))
    correct = sum(1 for item in revealed if item["correct"])
    return {
        "status": run.get("status") or "running",
        "answered": revealed,
        "correct": correct,
        "total": total,
        "timeMs": int(run.get("timeMs") or 0),
        "display": _display(correct, total, int(run.get("timeMs") or 0))
        if run.get("status") == "finished"
        else (run.get("display") or ""),
    }


def today_payload(
    terminal_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    day = local_today()
    paper = paper_for(day)
    uid = (user_id or "").strip() or None
    tid = (terminal_id or "").strip() or None
    run = None
    if uid or tid:
        run = _resolve_run(_load(), tid or "", paper["paperId"], user_id=uid or "")
    progress = _progress(run, paper)
    if progress["status"] == "finished" and (uid or tid):
        board = leaderboard(date=day, limit=100)
        my_key = _board_identity_key(
            {"userId": uid or "", "terminalId": tid or ""}
        ) if (uid or tid) else ""
        if not my_key and run:
            my_key = _board_identity_key(run)
        for item in board.get("items") or []:
            if my_key and _board_identity_key(item) == my_key:
                progress["rank"] = item.get("rank")
                break
    return {
        "paperId": paper["paperId"],
        "date": paper["date"],
        "title": paper["title"],
        "questions": paper["questions"],
        "progress": progress,
    }


def _ensure_run(
    data: Dict[str, Any],
    terminal_id: str,
    paper: Dict[str, Any],
    user_id: str = "",
    username: str = "",
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    run = _resolve_run(data, terminal_id, paper["paperId"], user_id=uid)
    if run:
        _assert_run_owner(run, uid)
        # Keep the active device on the run when the same user continues elsewhere.
        if uid and run.get("terminalId") != terminal_id:
            run["terminalId"] = terminal_id
            data["runs"][run["runId"]] = run
        if uid and not run.get("userId"):
            run["userId"] = uid
            run["username"] = (username or "").strip()
            if run["username"]:
                run["nickname"] = run["username"]
            data["runs"][run["runId"]] = run
        return run
    term = get_terminal(terminal_id)
    if not term:
        raise ValueError("terminal not registered")
    display_name = (username or "").strip() if uid else (term.get("nickname") or "")
    run = {
        "runId": str(uuid.uuid4()),
        "paperId": paper["paperId"],
        "date": paper["date"],
        "terminalId": terminal_id,
        "nickname": display_name,
        "status": "running",
        "startedAt": _now(),
        "endedAt": "",
        "answers": {},
        "correct": 0,
        "total": len(paper["questions"]),
        "timeMs": 0,
        "display": "",
    }
    if uid:
        run["userId"] = uid
        run["username"] = (username or "").strip() or display_name
    data["runs"][run["runId"]] = run
    return run


def answer_question(
    terminal_id: str,
    paper_id: str,
    question_id: int,
    choice: str,
    time_ms: int,
    user_id: str = "",
    username: str = "",
) -> Dict[str, Any]:
    term = get_terminal(terminal_id)
    if not term:
        raise ValueError("terminal not registered")
    day = local_today()
    paper = paper_for(day)
    if paper_id != paper["paperId"]:
        raise ValueError("paper is not today's")
    qmap = _question_map()
    full = qmap.get(int(question_id))
    ids = {int(q["id"]) for q in paper["questions"]}
    if not full or int(question_id) not in ids:
        raise ValueError("question not on today's paper")
    choice = (choice or "").strip().upper()
    if choice not in ("A", "B", "C", "D"):
        raise ValueError("invalid choice")

    data = _load()
    run = _ensure_run(data, terminal_id, paper, user_id=user_id, username=username)
    _assert_run_owner(run, user_id)
    key = str(int(question_id))
    stored = (run.get("answers") or {}).get(key)
    if not isinstance(stored, dict):
        if run.get("status") == "finished":
            raise ValueError("challenge already finished")
        cap = _elapsed_cap(run) + 1500
        reported = max(0, int(time_ms or 0))
        run["timeMs"] = min(reported, cap) if reported else int(run.get("timeMs") or 0)
        run.setdefault("answers", {})[key] = {"choice": choice}
        data["runs"][run["runId"]] = run
        _save(data)
        stored = run["answers"][key]
    revealed = _reveal(full, str(stored.get("choice") or ""))
    revealed["status"] = run.get("status")
    revealed["timeMs"] = int(run.get("timeMs") or 0)
    return revealed


def finish_run(
    terminal_id: str,
    paper_id: str,
    time_ms: int,
    user_id: str = "",
    username: str = "",
) -> Dict[str, Any]:
    term = get_terminal(terminal_id)
    if not term:
        raise ValueError("terminal not registered")
    day = local_today()
    paper = paper_for(day)
    if paper_id != paper["paperId"]:
        raise ValueError("paper is not today's")
    data = _load()
    uid = (user_id or "").strip()
    run = _resolve_run(data, terminal_id, paper_id, user_id=uid)
    if not run:
        raise ValueError("challenge not started")
    _assert_run_owner(run, uid)
    if run.get("status") == "finished":
        return run
    answers = run.get("answers") or {}
    if any(str(q["id"]) not in answers for q in paper["questions"]):
        raise ValueError("paper not finished")
    qmap = _question_map()
    correct = 0
    for q in paper["questions"]:
        full = qmap[int(q["id"])]
        choice = str((answers.get(str(q["id"])) or {}).get("choice") or "")
        if choice == str(full.get("answer") or ""):
            correct += 1
    cap = _elapsed_cap(run) + 1500
    reported = max(0, int(time_ms or 0))
    answering = min(reported, cap) if reported else int(run.get("timeMs") or 0)
    wrong = len(paper["questions"]) - correct
    used = answering + wrong * WRONG_PENALTY_MS
    run["correct"] = correct
    run["total"] = len(paper["questions"])
    run["timeMs"] = used
    run["display"] = _display(correct, run["total"], used)
    run["status"] = "finished"
    run["endedAt"] = _now()
    if uid:
        # Never overwrite a non-empty userId (prevents steal-on-finish).
        if not str(run.get("userId") or "").strip():
            run["userId"] = uid
        uname = (username or "").strip() or str(run.get("username") or "")
        if uname:
            run["username"] = uname
            run["nickname"] = uname
        else:
            run["nickname"] = term.get("nickname") or run.get("nickname") or ""
    else:
        run["nickname"] = term.get("nickname") or run.get("nickname") or ""
    if uid and run.get("terminalId") != terminal_id:
        run["terminalId"] = terminal_id
    data["runs"][run["runId"]] = run
    _save(data)
    return run


def _better(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """正确率高的在前；正确率相同，用时短的在前。"""
    return _run_key(a) > _run_key(b)


def leaderboard(date: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    today = local_today()
    day = clamp_board_date(date, today)
    best: Dict[str, Dict[str, Any]] = {}
    for run in _runs(_load()):
        if run.get("date") != day or run.get("status") != "finished":
            continue
        key = _board_identity_key(run)
        if not key:
            continue
        prev = best.get(key)
        if prev is None or _better(run, prev):
            best[key] = run
    ordered = sorted(best.values(), key=_run_key, reverse=True)
    nicks = nickname_lookup()
    items = []
    for idx, run in enumerate(ordered[:limit], start=1):
        tid = str(run.get("terminalId") or "")
        items.append(
            {
                "rank": idx,
                "terminalId": tid,
                "userId": str(run.get("userId") or ""),
                "nickname": (
                    str(run.get("username") or run.get("nickname") or "")
                    if run.get("userId")
                    else resolve_nickname(tid, fallback=str(run.get("nickname") or ""), lookup=nicks)
                ),
                "display": _display(
                    int(run.get("correct") or 0),
                    int(run.get("total") or 0),
                    int(run.get("timeMs") or 0),
                ),
                "correct": int(run.get("correct") or 0),
                "total": int(run.get("total") or 0),
                "timeMs": int(run.get("timeMs") or 0),
            }
        )
    return {"date": day, "dates": board_dates_payload(today), "title": "语文挑战榜", "items": items}


def lobby_slice(terminal_id: Optional[str], user_id: Optional[str] = None) -> Dict[str, Any]:
    day = local_today()
    paper = paper_for(day)
    board = leaderboard(date=day, limit=50)
    items = board.get("items") or []
    podium = [
        {"rank": it["rank"], "nickname": it.get("nickname") or "", "display": it.get("display") or ""}
        for it in items[:3]
    ]
    progress = {"status": "absent", "correct": 0, "total": len(paper["questions"]), "timeMs": 0, "display": ""}
    rank = None
    uid = (user_id or "").strip() or None
    tid = (terminal_id or "").strip() or None
    if uid or tid:
        data = _load()
        if uid:
            run = _run_for_user(data, uid, paper["paperId"])
        else:
            run = _run_for(data, tid, paper["paperId"])
        progress = _progress(run, paper)
        if progress["status"] == "finished" and run:
            match_key = _board_identity_key(run)
            for it in items:
                if match_key and _board_identity_key(it) == match_key:
                    rank = it.get("rank")
                    break
    status = progress["status"]
    done = len(progress.get("answered") or []) if isinstance(progress.get("answered"), list) else 0
    total = int(progress.get("total") or 0)
    if status == "finished":
        label = progress.get("display") or "已完成"
        cta = "view"
    elif status == "running":
        label = "进行中 %d/%d" % (done, total)
        cta = "continue"
    else:
        label = "未开始"
        cta = "start"
    return {
        "yuwenDaily": {
            "stageCount": total,
            "myProgressLabel": label,
            "cta": cta,
            "rank": rank,
        },
        "yuwenPodium": podium,
    }


def reassign_terminal_to_user(terminal_id: str, user_id: str, username: str) -> int:
    """Bind unbound historical yuwen runs for ``terminal_id`` to ``user_id``; return count updated."""
    tid = (terminal_id or "").strip()
    if not tid or not user_id:
        return 0
    name = (username or "").strip()
    data = _load()
    count = 0
    for run in (data.get("runs") or {}).values():
        if not isinstance(run, dict) or run.get("terminalId") != tid:
            continue
        if run.get("userId"):
            continue
        run["userId"] = user_id
        run["username"] = name
        run["nickname"] = name
        count += 1
    if count:
        _save(data)
    return count

def rename_username_for_user(user_id: str, new_username: str) -> int:
    """Update denormalized username/nickname on all yuwen runs for ``user_id``."""
    uid = (user_id or "").strip()
    if not uid:
        return 0
    name = (new_username or "").strip()
    data = _load()
    count = 0
    for run in (data.get("runs") or {}).values():
        if not isinstance(run, dict) or run.get("userId") != uid:
            continue
        run["username"] = name
        run["nickname"] = name
        count += 1
    if count:
        _save(data)
    return count

