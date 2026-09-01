from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.daily_challenges import ensure_today
from app import daily_runs
from app import scores
from app.storage import load_json
from app.terminals import get_terminal


def _fmt_ms(ms: int) -> str:
    s = max(0, int(ms)) // 1000
    m = s // 60
    r = s % 60
    return "%d:%02d" % (m, r)


def _fmt_daily_display(it: Dict[str, Any]) -> str:
    status = it.get("status")
    done = int(it.get("stagesDone") or 0)
    total_ms = int(it.get("totalTimeMs") or 0)
    combo = str(it.get("comboNo") or "")
    base = ""
    if status == "finished":
        base = _fmt_ms(total_ms)
    elif status == "exited":
        base = "退出 · %d 关 · %s" % (done, _fmt_ms(total_ms))
    else:
        base = str(status or "")
    if combo:
        return "%s · %s" % (base, combo)
    return base


def _load_runs() -> Dict[str, Any]:
    return load_json("daily_runs.json", {"version": 1, "runs": {}})


def _runs_for_terminal(day: str, terminal_id: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for run in (_load_runs().get("runs") or {}).values():
        if not isinstance(run, dict):
            continue
        if run.get("date") != day:
            continue
        if run.get("terminalId") != terminal_id:
            continue
        out.append(run)
    return out


def _sort_key_run(run: Dict[str, Any]):
    status = run.get("status")
    finished = 0 if status == "finished" else 1
    return (finished, -int(run.get("stagesDone") or 0), int(run.get("totalTimeMs") or 0))


def _best_ended_run(runs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ended = [r for r in runs if r.get("status") in ("finished", "exited")]
    if not ended:
        return None
    ended.sort(key=_sort_key_run)
    return ended[0]


def _gap_label(
    me_status: Optional[str],
    me_done: int,
    me_ms: int,
    first: Optional[Dict[str, Any]],
) -> tuple:
    if not first:
        return None, "—"
    first_status = first.get("status")
    first_done = int(first.get("stagesDone") or 0)
    first_ms = int(first.get("totalTimeMs") or 0)
    if me_status == "finished" and first_status == "finished":
        gap = me_ms - first_ms
        if gap > 0:
            return gap, "落后 %ds" % (gap // 1000)
        if gap < 0:
            return gap, "领先 %ds" % ((-gap) // 1000)
        return 0, "并列第1"
    if me_status is None:
        return None, "—"
    diff = me_done - first_done
    if diff < 0:
        return None, "少 %d 关" % (-diff)
    if diff > 0:
        return None, "多 %d 关" % diff
    return None, "—"


def _build_me(
    terminal_id: Optional[str],
    day: str,
    stage_count: int,
    items: List[Dict[str, Any]],
    podium: List[Dict[str, Any]],
) -> Dict[str, Any]:
    empty = {
        "nickname": None,
        "dailyRank": None,
        "dailyStatus": None,
        "stagesDone": 0,
        "stageCount": stage_count,
        "gapToFirstMs": None,
        "gapLabel": "—",
    }
    if not terminal_id:
        return empty
    term = get_terminal(terminal_id)
    nickname = (term or {}).get("nickname") or None
    runs = _runs_for_terminal(day, terminal_id)
    running = next((r for r in runs if r.get("status") == "running"), None)
    best = _best_ended_run(runs)

    daily_status = None
    stages_done = 0
    total_ms = 0
    run_id = None
    if running:
        daily_status = "running"
        stages_done = int(running.get("stagesDone") or 0)
        total_ms = int(running.get("totalTimeMs") or 0)
        run_id = running.get("runId")
    elif best:
        daily_status = best.get("status")
        stages_done = int(best.get("stagesDone") or 0)
        total_ms = int(best.get("totalTimeMs") or 0)
        run_id = best.get("runId")
    else:
        daily_status = "absent"

    daily_rank = None
    if run_id and daily_status in ("finished", "exited"):
        for idx, it in enumerate(items, start=1):
            if it.get("runId") == run_id:
                daily_rank = idx
                break

    first_item = items[0] if items else None
    if daily_status in ("finished", "exited"):
        gap_ms, gap_label = _gap_label(daily_status, stages_done, total_ms, first_item)
    else:
        gap_ms, gap_label = None, "—"

    return {
        "nickname": nickname,
        "dailyRank": daily_rank,
        "dailyStatus": daily_status,
        "stagesDone": stages_done,
        "stageCount": stage_count,
        "gapToFirstMs": gap_ms,
        "gapLabel": gap_label,
    }


def _build_daily(
    terminal_id: Optional[str],
    day: str,
    stage_count: int,
    me: Dict[str, Any],
) -> Dict[str, Any]:
    status = me.get("dailyStatus")
    done = int(me.get("stagesDone") or 0)
    if not terminal_id or status in (None, "absent"):
        return {
            "stageCount": stage_count,
            "myProgressLabel": "未开始",
            "cta": "start",
        }
    if status == "running":
        return {
            "stageCount": stage_count,
            "myProgressLabel": "进行中 %d/%d" % (done, stage_count),
            "cta": "continue",
        }
    if status == "finished":
        return {
            "stageCount": stage_count,
            "myProgressLabel": "已通关",
            "cta": "view",
        }
    # exited
    return {
        "stageCount": stage_count,
        "myProgressLabel": "已退出 %d/%d" % (done, stage_count),
        "cta": "start",
    }


def get_lobby_summary(terminal_id: Optional[str] = None) -> Dict[str, Any]:
    combo = ensure_today()
    day = combo["date"]
    stage_count = len(combo.get("stages") or [])
    board = daily_runs.leaderboard(date=day, limit=50)
    items = board.get("items") or []
    podium: List[Dict[str, Any]] = []
    for idx, it in enumerate(items[:3], start=1):
        podium.append(
            {
                "rank": idx,
                "nickname": it.get("nickname") or "",
                "status": it.get("status"),
                "stagesDone": int(it.get("stagesDone") or 0),
                "totalTimeMs": int(it.get("totalTimeMs") or 0),
                "display": _fmt_daily_display(it),
            }
        )
    me = _build_me(terminal_id, day, stage_count, items, podium)
    daily = _build_daily(terminal_id, day, stage_count, me)
    recent = scores.latest_for_terminal(terminal_id) if terminal_id else None
    return {
        "date": day,
        "me": me,
        "podium": podium,
        "daily": daily,
        "recent": recent,
    }
