from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.rank_config import RANKABLE_GAMES, STANDARD_TIER_IDS
from app.storage import load_json, save_json

STORE = "daily_admin.json"
SESSION_HOURS = 12
PLAYABLE_IDS = [g["id"] for g in RANKABLE_GAMES]


def _empty() -> Dict[str, Any]:
    return {
        "version": 1,
        "passwordHash": "",
        "salt": "",
        "sessionToken": "",
        "sessionExpiresAt": "",
        "template": default_template(),
    }


def default_template() -> Dict[str, Any]:
    return {"stages": [{"gameId": gid, "tier": "normal"} for gid in PLAYABLE_IDS]}


def _load() -> Dict[str, Any]:
    data = load_json(STORE, _empty())
    if not isinstance(data.get("template"), dict):
        data["template"] = default_template()
    return data


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def _hash(salt: str, password: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _issue_session(data: Dict[str, Any]) -> Dict[str, str]:
    token = secrets.token_urlsafe(24)
    exp = _now() + timedelta(hours=SESSION_HOURS)
    data["sessionToken"] = token
    data["sessionExpiresAt"] = exp.isoformat()
    _save(data)
    return {"token": token, "expiresAt": data["sessionExpiresAt"]}


def _session_ok(data: Dict[str, Any], token: Optional[str]) -> bool:
    if not token or not data.get("sessionToken") or token != data["sessionToken"]:
        return False
    raw = data.get("sessionExpiresAt") or ""
    try:
        exp = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return _now() <= exp


def admin_status(token: Optional[str] = None) -> Dict[str, Any]:
    data = _load()
    return {
        "hasPassword": bool(data.get("passwordHash")),
        "authenticated": _session_ok(data, token),
    }


def setup_password(password: str) -> Dict[str, str]:
    password = (password or "").strip()
    if len(password) < 4:
        raise ValueError("password too short")
    data = _load()
    if data.get("passwordHash"):
        raise ValueError("password already set")
    salt = secrets.token_hex(16)
    data["salt"] = salt
    data["passwordHash"] = _hash(salt, password)
    return _issue_session(data)


def login(password: str) -> Dict[str, str]:
    data = _load()
    if not data.get("passwordHash"):
        raise ValueError("password not set")
    if _hash(data.get("salt") or "", password or "") != data["passwordHash"]:
        raise ValueError("invalid password")
    return _issue_session(data)


def logout(token: str) -> None:
    data = _load()
    if token and token == data.get("sessionToken"):
        data["sessionToken"] = ""
        data["sessionExpiresAt"] = ""
        _save(data)


def require_admin(token: Optional[str]) -> None:
    if not _session_ok(_load(), token):
        raise PermissionError("admin auth required")


def get_template() -> Dict[str, Any]:
    data = _load()
    stages = data.get("template", {}).get("stages") or []
    if not stages:
        return default_template()
    return {"stages": list(stages)}


def put_template(stages: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not stages:
        raise ValueError("template stages empty")
    clean: List[Dict[str, str]] = []
    for s in stages:
        gid = str(s.get("gameId") or "").strip()
        tier = str(s.get("tier") or "").strip()
        if gid not in PLAYABLE_IDS:
            raise ValueError("unknown gameId: %s" % gid)
        if tier not in STANDARD_TIER_IDS:
            raise ValueError("invalid tier: %s" % tier)
        clean.append({"gameId": gid, "tier": tier})
    data = _load()
    data["template"] = {"stages": clean}
    _save(data)
    return get_template()
