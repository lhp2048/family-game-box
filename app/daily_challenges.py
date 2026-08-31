from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.daily_admin import get_template
from app.rank_config import RANKABLE_GAMES, tier_label
from app.storage import load_json, save_json

STORE = "daily_challenges.json"
HISTORY_MAX = 20
_TITLES = {g["id"]: g["title"] for g in RANKABLE_GAMES}


def _empty() -> Dict[str, Any]:
    return {"version": 1, "current": None, "history": []}


def _load() -> Dict[str, Any]:
    return load_json(STORE, _empty())


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def local_today() -> str:
    return datetime.now().astimezone().date().isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_combo(source: str) -> Dict[str, Any]:
    tmpl = get_template()
    stages_in = tmpl.get("stages") or []
    if not stages_in:
        raise ValueError("empty template")
    stages = []
    for s in stages_in:
        gid = s["gameId"]
        tier = s["tier"]
        stages.append(
            {
                "gameId": gid,
                "title": _TITLES.get(gid, gid),
                "tier": tier,
                "tierLabel": tier_label(tier),
                "seed": secrets.randbelow(2**31 - 1) + 1,
            }
        )
    return {
        "comboId": str(uuid.uuid4()),
        "date": local_today(),
        "createdAt": _now_iso(),
        "source": source,
        "stages": stages,
    }


def _push_history(data: Dict[str, Any], combo: Dict[str, Any]) -> None:
    hist: List[Dict[str, Any]] = list(data.get("history") or [])
    hist.insert(0, combo)
    data["history"] = hist[:HISTORY_MAX]


def ensure_today(source: str = "auto") -> Dict[str, Any]:
    data = _load()
    cur = data.get("current")
    today = local_today()
    if isinstance(cur, dict) and cur.get("date") == today:
        return cur
    if isinstance(cur, dict) and cur.get("comboId"):
        _push_history(data, cur)
    combo = _build_combo(source)
    data["current"] = combo
    _save(data)
    return combo


def regenerate() -> Dict[str, Any]:
    data = _load()
    cur = data.get("current")
    if isinstance(cur, dict) and cur.get("comboId"):
        _push_history(data, cur)
    combo = _build_combo("admin")
    data["current"] = combo
    _save(data)
    return combo


def get_history() -> List[Dict[str, Any]]:
    data = _load()
    return list(data.get("history") or [])[:HISTORY_MAX]


def get_current() -> Any:
    return _load().get("current")
