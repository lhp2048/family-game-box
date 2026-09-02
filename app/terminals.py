from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.storage import load_json, save_json

_TERMINAL_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)
_NICKNAME_RE = re.compile(r"^[\w\u4e00-\u9fff\u3400-\u4dbf\-·\.]{1,16}$", re.U)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "terminals": {}}


def validate_terminal_id(terminal_id: str) -> bool:
    return bool(_TERMINAL_RE.match(terminal_id or ""))


def normalize_nickname(value: str) -> str:
    nick = (value or "").strip()
    if not nick or len(nick) > 16:
        raise ValueError("nickname must be 1-16 characters")
    if not _NICKNAME_RE.match(nick):
        raise ValueError("nickname has invalid characters")
    return nick


def get_terminal(terminal_id: str) -> Optional[Dict[str, Any]]:
    if not validate_terminal_id(terminal_id):
        return None
    store = load_json("terminals.json", _empty_store())
    item = store.get("terminals", {}).get(terminal_id)
    if not isinstance(item, dict):
        return None
    return item


def nickname_lookup() -> Dict[str, str]:
    """terminalId -> 当前昵称（排行榜读时用，避免历史快照不同步）。"""
    store = load_json("terminals.json", _empty_store())
    out: Dict[str, str] = {}
    for tid, item in (store.get("terminals") or {}).items():
        if isinstance(item, dict):
            nick = item.get("nickname") or ""
            if nick:
                out[str(tid)] = nick
    return out


def resolve_nickname(
    terminal_id: str,
    fallback: str = "",
    lookup: Optional[Dict[str, str]] = None,
) -> str:
    """优先当前终端昵称；终端已删时回退成绩/挑战记录里的快照。"""
    tid = str(terminal_id or "")
    if lookup is not None:
        current = lookup.get(tid) or ""
    else:
        term = get_terminal(tid) if tid else None
        current = (term or {}).get("nickname") or ""
    return current or (fallback or "")


def get_me(terminal_id: str) -> Dict[str, Any]:
    item = get_terminal(terminal_id)
    if not item:
        return {"registered": False, "terminalId": terminal_id}
    return {
        "registered": True,
        "terminalId": terminal_id,
        "nickname": item.get("nickname", ""),
        "createdAt": item.get("createdAt"),
        "updatedAt": item.get("updatedAt"),
    }


def register_terminal(terminal_id: str, nickname: str) -> Dict[str, Any]:
    if not validate_terminal_id(terminal_id):
        raise ValueError("invalid terminal id")
    nick = normalize_nickname(nickname)
    store = load_json("terminals.json", _empty_store())
    terminals = store.setdefault("terminals", {})
    now = _now()
    existing = terminals.get(terminal_id)
    if isinstance(existing, dict):
        existing["nickname"] = nick
        existing["updatedAt"] = now
        existing["lastSeenAt"] = now
        terminals[terminal_id] = existing
    else:
        terminals[terminal_id] = {
            "nickname": nick,
            "createdAt": now,
            "updatedAt": now,
            "lastSeenAt": now,
        }
    save_json("terminals.json", store)
    return get_me(terminal_id)


def touch_terminal(terminal_id: str) -> None:
    if not validate_terminal_id(terminal_id):
        return
    store = load_json("terminals.json", _empty_store())
    terminals = store.setdefault("terminals", {})
    item = terminals.get(terminal_id)
    if not isinstance(item, dict):
        return
    item["lastSeenAt"] = _now()
    terminals[terminal_id] = item
    save_json("terminals.json", store)


def new_terminal_id() -> str:
    return str(uuid.uuid4())
