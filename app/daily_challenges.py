from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


def combo_label_from_seq(day_seq: int) -> str:
    return "今日挑战#%d" % int(day_seq)


def _max_day_seq(data: Dict[str, Any], day: str) -> int:
    n = 0
    cur = data.get("current")
    if isinstance(cur, dict) and cur.get("date") == day:
        n = max(n, int(cur.get("daySeq") or 0))
    for h in data.get("history") or []:
        if isinstance(h, dict) and h.get("date") == day:
            n = max(n, int(h.get("daySeq") or 0))
    return n


def _next_day_seq(data: Dict[str, Any], day: str) -> int:
    return _max_day_seq(data, day) + 1


def _build_combo(source: str, day_seq: int, day: Optional[str] = None) -> Dict[str, Any]:
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
    seq = int(day_seq)
    return {
        "comboId": str(uuid.uuid4()),
        "date": day or local_today(),
        "createdAt": _now_iso(),
        "source": source,
        "daySeq": seq,
        "label": combo_label_from_seq(seq),
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
        # 旧数据补易记名（当日第一场视为 #1）
        if not int(cur.get("daySeq") or 0):
            cur["daySeq"] = 1
            cur["label"] = combo_label_from_seq(1)
            data["current"] = cur
            _save(data)
        elif not str(cur.get("label") or "").strip():
            cur["label"] = combo_label_from_seq(int(cur["daySeq"]))
            data["current"] = cur
            _save(data)
        return cur
    if isinstance(cur, dict) and cur.get("comboId"):
        _push_history(data, cur)
    combo = _build_combo(source, _next_day_seq(data, today), today)
    data["current"] = combo
    _save(data)
    return combo


def regenerate() -> Dict[str, Any]:
    data = _load()
    today = local_today()
    cur = data.get("current")
    if isinstance(cur, dict) and cur.get("comboId"):
        _push_history(data, cur)
    combo = _build_combo("admin", _next_day_seq(data, today), today)
    data["current"] = combo
    _save(data)
    return combo


def get_history() -> List[Dict[str, Any]]:
    data = _load()
    return list(data.get("history") or [])[:HISTORY_MAX]


def get_current() -> Any:
    return _load().get("current")


def find_combo(combo_id: str) -> Optional[Dict[str, Any]]:
    cid = str(combo_id or "")
    if not cid:
        return None
    data = _load()
    cur = data.get("current")
    if isinstance(cur, dict) and str(cur.get("comboId") or "") == cid:
        return cur
    for h in data.get("history") or []:
        if isinstance(h, dict) and str(h.get("comboId") or "") == cid:
            return h
    return None


def list_combos_for_date(day: str) -> List[Dict[str, Any]]:
    """当日挑战列表，最新（daySeq 大）在前。"""
    day = str(day or "")
    data = _load()
    out: List[Dict[str, Any]] = []
    seen = set()
    cur = data.get("current")
    if isinstance(cur, dict) and cur.get("date") == day and cur.get("comboId"):
        out.append(cur)
        seen.add(str(cur.get("comboId")))
    for h in data.get("history") or []:
        if not isinstance(h, dict):
            continue
        if h.get("date") != day:
            continue
        cid = str(h.get("comboId") or "")
        if not cid or cid in seen:
            continue
        out.append(h)
        seen.add(cid)

    def _key(c: Dict[str, Any]):
        return (int(c.get("daySeq") or 0), str(c.get("createdAt") or ""))

    out.sort(key=_key, reverse=True)
    return out


def combo_display_name(combo_id: str) -> str:
    """榜单/UI 用的易记名；旧数据无 daySeq 时回退短单号。"""
    combo = find_combo(combo_id)
    if isinstance(combo, dict):
        label = str(combo.get("label") or "").strip()
        if label:
            return label
        seq = int(combo.get("daySeq") or 0)
        if seq > 0:
            return combo_label_from_seq(seq)
    raw = str(combo_id or "").replace("-", "")
    if not raw:
        return ""
    return raw[:8].upper()
