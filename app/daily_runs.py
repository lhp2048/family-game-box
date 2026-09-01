from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.daily_challenges import ensure_today, get_current, local_today
from app.storage import load_json, save_json
from app.terminals import get_terminal

STORE = "daily_runs.json"


def _empty() -> Dict[str, Any]:
    return {"version": 1, "runs": {}}


def _load() -> Dict[str, Any]:
    return load_json(STORE, _empty())


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run(terminal_id: str) -> Dict[str, Any]:
    term = get_terminal(terminal_id)
    if not term:
        raise ValueError("terminal not registered")
    combo = ensure_today()
    run_id = str(uuid.uuid4())
    run = {
        "runId": run_id,
        "comboId": combo["comboId"],
        "date": combo["date"],
        "terminalId": terminal_id,
        "nickname": term.get("nickname") or "",
        "status": "running",
        "startedAt": _now(),
        "endedAt": "",
        "totalTimeMs": 0,
        "stagesDone": 0,
        "stageResults": [],
        "stages": combo["stages"],
    }
    data = _load()
    data.setdefault("runs", {})[run_id] = run
    _save(data)
    return run


def _append_stage(run: Dict[str, Any], stage: Optional[Dict[str, Any]]) -> None:
    if not isinstance(stage, dict):
        return
    entry = {
        "gameId": str(stage.get("gameId") or ""),
        "tier": str(stage.get("tier") or ""),
        "timeMs": int(stage.get("timeMs") or 0),
        "completed": bool(stage.get("completed")),
    }
    run.setdefault("stageResults", []).append(entry)
    if entry["completed"]:
        run["stagesDone"] = int(run.get("stagesDone") or 0) + 1


def _rank_key(run: Dict[str, Any]):
    status = run.get("status")
    finished = 0 if status == "finished" else 1
    return (finished, -int(run.get("stagesDone") or 0), int(run.get("totalTimeMs") or 0))


def _prune_player_combo_runs(data: Dict[str, Any], terminal_id: str, combo_id: str) -> None:
    """同一终端 + 同一挑战组合：只保留首次结束记录与最佳记录（可重合为一条）。"""
    runs = data.setdefault("runs", {})
    ended: List[Dict[str, Any]] = []
    for run in runs.values():
        if not isinstance(run, dict):
            continue
        if run.get("terminalId") != terminal_id:
            continue
        if str(run.get("comboId") or "") != str(combo_id or ""):
            continue
        if run.get("status") not in ("finished", "exited"):
            continue
        ended.append(run)
    if len(ended) <= 1:
        return
    first = min(ended, key=lambda r: str(r.get("startedAt") or r.get("endedAt") or ""))
    best = min(ended, key=_rank_key)
    keep = {str(first.get("runId") or ""), str(best.get("runId") or "")}
    drop = []
    for rid, run in list(runs.items()):
        if not isinstance(run, dict):
            continue
        if run.get("terminalId") != terminal_id:
            continue
        if str(run.get("comboId") or "") != str(combo_id or ""):
            continue
        if run.get("status") not in ("finished", "exited"):
            continue
        rid_s = str(rid)
        run_id = str(run.get("runId") or "")
        if rid_s not in keep and run_id not in keep:
            drop.append(rid)
    for rid in drop:
        runs.pop(rid, None)


def _record_kinds_for_group(ended: List[Dict[str, Any]]) -> Dict[str, str]:
    """runId -> first | best | first+best"""
    if not ended:
        return {}
    first = min(ended, key=lambda r: str(r.get("startedAt") or r.get("endedAt") or ""))
    best = min(ended, key=_rank_key)
    fid = str(first.get("runId") or "")
    bid = str(best.get("runId") or "")
    out: Dict[str, str] = {}
    if fid == bid:
        out[fid] = "first+best"
    else:
        out[fid] = "first"
        out[bid] = "best"
    return out


def patch_run(terminal_id: str, run_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    run = (data.get("runs") or {}).get(run_id)
    if not isinstance(run, dict):
        raise ValueError("run not found")
    if run.get("terminalId") != terminal_id:
        raise PermissionError("not your run")
    if run.get("status") != "running":
        raise ValueError("run not running")
    action = str(body.get("action") or "")
    stage = body.get("stage")
    if "totalTimeMs" in body:
        run["totalTimeMs"] = int(body.get("totalTimeMs") or 0)
    if action == "stage_done":
        st = dict(stage or {})
        st["completed"] = True
        _append_stage(run, st)
    elif action == "exit":
        if isinstance(stage, dict):
            st = dict(stage)
            st["completed"] = bool(st.get("completed"))
            _append_stage(run, st)
        run["status"] = "exited"
        run["endedAt"] = _now()
    elif action == "finish":
        if isinstance(stage, dict):
            st = dict(stage)
            st["completed"] = True
            _append_stage(run, st)
        run["status"] = "finished"
        run["endedAt"] = _now()
    else:
        raise ValueError("invalid action")
    data["runs"][run_id] = run
    if run.get("status") in ("finished", "exited"):
        _prune_player_combo_runs(data, terminal_id, str(run.get("comboId") or ""))
    _save(data)
    # 可能被 prune 掉的是「当前以外」的旧 run；当前这条一定保留
    return data["runs"].get(run_id) or run


def _combo_no(combo_id: str) -> str:
    """短单号：去掉横线后取前 8 位大写，便于同榜区分不同挑战组合。"""
    raw = str(combo_id or "").replace("-", "")
    if not raw:
        return ""
    return raw[:8].upper()


def leaderboard(date: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    day = date or local_today()
    cur = get_current()
    if isinstance(cur, dict) and cur.get("date") == day and cur.get("comboId"):
        current_combo = str(cur.get("comboId") or "")
    elif day == local_today():
        current_combo = str(ensure_today().get("comboId") or "")
    else:
        current_combo = ""

    # 先按 (terminalId, comboId) 分组，标首次/最佳，再展平进榜
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for run in (_load().get("runs") or {}).values():
        if not isinstance(run, dict):
            continue
        if run.get("date") != day:
            continue
        if run.get("status") == "running":
            continue
        tid = str(run.get("terminalId") or "")
        cid = str(run.get("comboId") or "")
        key = tid + "|" + cid
        groups.setdefault(key, []).append(run)

    items: List[Dict[str, Any]] = []
    for ended in groups.values():
        kinds = _record_kinds_for_group(ended)
        for run in ended:
            rid = str(run.get("runId") or "")
            kind = kinds.get(rid)
            if not kind:
                continue
            cid = str(run.get("comboId") or "")
            items.append(
                {
                    "runId": rid,
                    "comboId": cid,
                    "comboNo": _combo_no(cid),
                    "isCurrentCombo": bool(cid and cid == current_combo),
                    "recordKind": kind,
                    "nickname": run.get("nickname"),
                    "terminalId": run.get("terminalId") or "",
                    "status": run.get("status"),
                    "stagesDone": int(run.get("stagesDone") or 0),
                    "totalTimeMs": int(run.get("totalTimeMs") or 0),
                    "stageResults": run.get("stageResults") or [],
                    "endedAt": run.get("endedAt") or "",
                }
            )

    def _key(it: Dict[str, Any]):
        finished = 0 if it["status"] == "finished" else 1
        return (finished, -it["stagesDone"], it["totalTimeMs"])

    items.sort(key=_key)
    return {
        "date": day,
        "currentComboId": current_combo,
        "currentComboNo": _combo_no(current_combo),
        "items": items[: max(1, min(limit, 100))],
    }
