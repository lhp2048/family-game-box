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
