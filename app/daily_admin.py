from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.rank_config import STANDARD_TIER_IDS
from app.storage import load_json, save_json

STORE = "daily_admin.json"
SESSION_HOURS = 12
PLAY_COOKIE = "fgb_play"
PLAY_TTL = 30 * 24 * 3600
_play_gate_cache: Optional[Dict[str, Any]] = None
_play_gate_cache_dir: Optional[str] = None


def _playable_ids() -> List[str]:
    from app.game_registry import daily_candidate_games

    return [g["id"] for g in daily_candidate_games()]


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
    from app.rank_config import RANKABLE_GAMES

    return {"stages": [{"gameId": g["id"], "tier": "normal"} for g in RANKABLE_GAMES]}


DAILY_TAIL_GAME_ID = "mental-speed"


def _normalize_stage_row(s: Dict[str, Any]) -> Optional[Dict[str, str]]:
    gid = str(s.get("gameId") or "").strip()
    if not gid:
        return None
    tier = str(s.get("tier") or "normal").strip() or "normal"
    return {"gameId": gid, "tier": tier}


def _ensure_mental_speed_last(stages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Persisted templates from before 心算快答 may omit the final daily stage."""
    clean: List[Dict[str, str]] = []
    for s in stages:
        row = _normalize_stage_row(s)
        if row:
            clean.append(row)
    if not clean:
        return list(default_template()["stages"])
    playable = set(_playable_ids())
    if DAILY_TAIL_GAME_ID not in playable:
        return clean
    ids = [r["gameId"] for r in clean]
    if DAILY_TAIL_GAME_ID not in ids:
        clean.append({"gameId": DAILY_TAIL_GAME_ID, "tier": "normal"})
    return clean


def _play_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    data.setdefault("playGateEnabled", False)
    data.setdefault("playPassphraseSalt", "")
    data.setdefault("playPassphraseHash", "")
    data.setdefault("playTokenKey", "")
    data.setdefault("playGeneration", 0)
    return data


def _public_play(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "playGateEnabled": bool(data.get("playGateEnabled")),
        "hasPlayPassphrase": bool(data.get("playPassphraseHash")),
    }


def _load() -> Dict[str, Any]:
    data = load_json(STORE, _empty())
    if not isinstance(data.get("template"), dict):
        data["template"] = default_template()
    else:
        raw = data.get("template", {}).get("stages") or []
        if not isinstance(raw, list):
            raw = []
        prev = [r for s in raw if (r := _normalize_stage_row(s))]
        normed = _ensure_mental_speed_last(raw)
        if normed != prev:
            data["template"] = {"stages": normed}
            _save(data)
    return _play_fields(data)


def clear_play_gate_cache() -> None:
    global _play_gate_cache, _play_gate_cache_dir
    _play_gate_cache = None
    _play_gate_cache_dir = None


def play_gate_snapshot() -> Dict[str, Any]:
    global _play_gate_cache, _play_gate_cache_dir
    from app.storage import DATA_DIR

    here = str(DATA_DIR)
    if _play_gate_cache is None or _play_gate_cache_dir != here:
        data = _load()
        _play_gate_cache = {
            "playGateEnabled": bool(data.get("playGateEnabled")),
            "playGeneration": int(data.get("playGeneration") or 0),
            "playTokenKey": str(data.get("playTokenKey") or ""),
        }
        _play_gate_cache_dir = here
    return _play_gate_cache


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
        **_public_play(data),
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


def put_play_gate(enabled: bool, passphrase: Optional[str]) -> Dict[str, Any]:
    data = _load()
    passphrase = (passphrase or "").strip()
    changed = False
    if passphrase:
        if len(passphrase) < 4:
            raise ValueError("password too short")
        if not data.get("playTokenKey"):
            data["playTokenKey"] = secrets.token_hex(32)
        data["playPassphraseSalt"] = secrets.token_hex(16)
        data["playPassphraseHash"] = _hash(data["playPassphraseSalt"], passphrase)
        changed = True
    if enabled and not data.get("playPassphraseHash"):
        raise ValueError("passphrase not set")
    turning_on = enabled and not data.get("playGateEnabled")
    if changed or turning_on:
        data["playGeneration"] = int(data.get("playGeneration") or 0) + 1
    data["playGateEnabled"] = bool(enabled)
    _save(data)
    clear_play_gate_cache()
    return _public_play(data)


def issue_play_cookie(passphrase: str, now: Optional[int] = None) -> str:
    data = _load()
    passphrase = (passphrase or "").strip()
    if not data.get("playPassphraseHash"):
        raise ValueError("口令不对")
    if _hash(data.get("playPassphraseSalt") or "", passphrase or "") != data["playPassphraseHash"]:
        raise ValueError("口令不对")
    current = int(now if now is not None else time.time())
    exp = current + PLAY_TTL
    payload = "%s.%s" % (int(data["playGeneration"]), exp)
    sig = hmac.new(data["playTokenKey"].encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return payload + "." + sig


def play_cookie_ok(cookie: Optional[str], now: Optional[int] = None) -> bool:
    snap = play_gate_snapshot()
    if not cookie or not snap.get("playTokenKey"):
        return False
    parts = cookie.split(".")
    if len(parts) != 3:
        return False
    payload = parts[0] + "." + parts[1]
    try:
        expect = hmac.new(
            snap["playTokenKey"].encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expect, parts[2]):
            return False
    except (TypeError, ValueError):
        return False
    try:
        generation = int(parts[0])
        exp = int(parts[1])
    except ValueError:
        return False
    current = int(now if now is not None else time.time())
    return generation == int(snap.get("playGeneration") or 0) and current <= exp


def get_template() -> Dict[str, Any]:
    data = _load()
    stages = data.get("template", {}).get("stages") or []
    if not stages:
        return default_template()
    return {"stages": _ensure_mental_speed_last(list(stages))}


def put_template(stages: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not stages:
        raise ValueError("template stages empty")
    playable = set(_playable_ids())
    # allow already-template games that are built-in even if briefly disabled? require enabled+supportsDaily
    clean: List[Dict[str, str]] = []
    for s in stages:
        gid = str(s.get("gameId") or "").strip()
        tier = str(s.get("tier") or "").strip()
        if gid not in playable:
            raise ValueError("game not available for daily: %s" % gid)
        if tier not in STANDARD_TIER_IDS:
            raise ValueError("invalid tier: %s" % tier)
        clean.append({"gameId": gid, "tier": tier})
    data = _load()
    data["template"] = {"stages": clean}
    _save(data)
    return get_template()
