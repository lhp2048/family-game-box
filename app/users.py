from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.storage import load_json, save_json

STORE = "users.json"
USER_COOKIE = "fgb_user"
USER_TTL = 30 * 24 * 3600
_USERNAME_RE = re.compile(r"^[\w\u4e00-\u9fff\u3400-\u4dbf\-·\.]{1,16}$", re.U)


def _empty() -> Dict[str, Any]:
    return {
        "version": 1,
        "users": {},
        "usernameIndex": {},
        "sessionKey": "",
        "sessionGeneration": 0,
        "claimedTerminals": {},
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(salt: str, password: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _load() -> Dict[str, Any]:
    data = load_json(STORE, _empty())
    data.setdefault("users", {})
    data.setdefault("usernameIndex", {})
    data.setdefault("claimedTerminals", {})
    data.setdefault("sessionGeneration", 0)
    if not data.get("sessionKey"):
        data["sessionKey"] = secrets.token_hex(32)
        _save(data)
    return data


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def _public_user(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "userId": item["userId"],
        "username": item["username"],
        "createdAt": item.get("createdAt"),
    }


def normalize_username(value: str) -> str:
    name = (value or "").strip()
    if not name or len(name) > 16:
        raise ValueError("用户名须为 1–16 个字符")
    if not _USERNAME_RE.match(name):
        raise ValueError("用户名含有无效字符")
    return name


def _normalize_password(password: str) -> str:
    pw = password or ""
    if len(pw) < 6 or len(pw) > 128:
        raise ValueError("口令须为 6–128 个字符")
    return pw


def register_user(username: str, password: str) -> dict:
    name = normalize_username(username)
    data = _load()
    key = name.casefold()
    if key in (data.get("usernameIndex") or {}):
        raise ValueError("用户名已占用")
    pw = _normalize_password(password)
    user_id = str(uuid.uuid4())
    salt = secrets.token_hex(16)
    item = {
        "userId": user_id,
        "username": name,
        "passwordSalt": salt,
        "passwordHash": _hash(salt, pw),
        "createdAt": _now_iso(),
    }
    data.setdefault("users", {})[user_id] = item
    data.setdefault("usernameIndex", {})[key] = user_id
    _save(data)
    return _public_user(item)


def authenticate(username: str, password: str) -> dict:
    name = (username or "").strip()
    data = _load()
    user_id = (data.get("usernameIndex") or {}).get(name.casefold())
    if not user_id:
        raise ValueError("口令不对")
    item = (data.get("users") or {}).get(user_id)
    if not isinstance(item, dict):
        raise ValueError("口令不对")
    if _hash(item.get("passwordSalt") or "", password or "") != item.get("passwordHash"):
        raise ValueError("口令不对")
    return _public_user(item)


def get_user(user_id: str) -> dict | None:
    if not user_id:
        return None
    data = _load()
    item = (data.get("users") or {}).get(user_id)
    if not isinstance(item, dict):
        return None
    return _public_user(item)


def get_user_by_username(username: str) -> dict | None:
    name = (username or "").strip()
    if not name:
        return None
    data = _load()
    user_id = (data.get("usernameIndex") or {}).get(name.casefold())
    if not user_id:
        return None
    item = (data.get("users") or {}).get(user_id)
    if not isinstance(item, dict):
        return None
    return _public_user(item)


def issue_user_cookie(user_id: str, now: int | None = None) -> str:
    data = _load()
    if user_id not in (data.get("users") or {}):
        raise ValueError("用户不存在")
    current = int(now if now is not None else time.time())
    exp = current + USER_TTL
    generation = int(data.get("sessionGeneration") or 0)
    payload = "%s.%s.%s" % (user_id, exp, generation)
    sig = hmac.new(
        data["sessionKey"].encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return payload + "." + sig


def _parse_user_cookie(
    cookie: Optional[str], now: Optional[int] = None
) -> Optional[str]:
    if not cookie:
        return None
    data = _load()
    key = data.get("sessionKey") or ""
    if not key:
        return None
    parts = cookie.split(".")
    if len(parts) != 4:
        return None
    user_id, exp_s, gen_s, sig = parts
    payload = "%s.%s.%s" % (user_id, exp_s, gen_s)
    try:
        expect = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
    except (TypeError, ValueError):
        return None
    try:
        exp = int(exp_s)
        generation = int(gen_s)
    except ValueError:
        return None
    current = int(now if now is not None else time.time())
    if generation != int(data.get("sessionGeneration") or 0):
        return None
    if current > exp:
        return None
    if user_id not in (data.get("users") or {}):
        return None
    return user_id


def user_cookie_ok(cookie: str | None, now: int | None = None) -> bool:
    return _parse_user_cookie(cookie, now=now) is not None


def user_id_from_cookie(cookie: str | None, now: int | None = None) -> str | None:
    return _parse_user_cookie(cookie, now=now)


def claim_available(terminal_id: str | None) -> bool:
    """True when terminal exists in store and has not been claimed yet."""
    tid = (terminal_id or "").strip()
    if not tid:
        return False
    from app.terminals import get_terminal

    if not get_terminal(tid):
        return False
    data = _load()
    claimed = data.get("claimedTerminals") or {}
    return tid not in claimed


def claim_terminal(user_id: str, terminal_id: str) -> dict:
    """Migrate one terminal's historical scores/runs onto ``user_id`` (once per terminal)."""
    tid = (terminal_id or "").strip()
    if not tid:
        raise ValueError("缺少终端标识")
    data = _load()
    users_map = data.get("users") or {}
    item = users_map.get(user_id)
    if not isinstance(item, dict):
        raise ValueError("用户不存在")
    claimed = data.setdefault("claimedTerminals", {})
    if tid in claimed:
        raise ValueError("该终端成绩已认领")
    username = str(item.get("username") or "")

    from app import daily_runs, scores, yuwen_daily

    scores_n = scores.reassign_terminal_to_user(tid, user_id, username)
    daily_n = daily_runs.reassign_terminal_to_user(tid, user_id, username)
    yuwen_n = yuwen_daily.reassign_terminal_to_user(tid, user_id, username)

    claimed[tid] = user_id
    _save(data)
    return {
        "ok": True,
        "terminalId": tid,
        "userId": user_id,
        "username": username,
        "scoresUpdated": scores_n,
        "dailyUpdated": daily_n,
        "yuwenUpdated": yuwen_n,
    }
