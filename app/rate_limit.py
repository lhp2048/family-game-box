"""In-memory auth attempt limits (per process). Resets on cold start on serverless."""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple

MAX_FAILURES = 8
LOCKOUT_SECONDS = 15 * 60

_lock = threading.Lock()
_buckets: Dict[str, Dict[str, float]] = {}


def clear_all() -> None:
    with _lock:
        _buckets.clear()


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:128] or "unknown"
    if request.client and request.client.host:
        return str(request.client.host)[:128]
    return "unknown"


def make_key(scope: str, ip: str, identity: str = "") -> str:
    scope = (scope or "auth").strip()[:64]
    ip = (ip or "unknown")[:128]
    ident = (identity or "").strip().casefold()[:64]
    if ident:
        return "%s|%s|%s" % (scope, ip, ident)
    return "%s|%s" % (scope, ip)


def check_allowed(key: str, now: Optional[float] = None) -> Tuple[bool, int]:
    """Return (allowed, retry_after_seconds)."""
    t = now if now is not None else time.time()
    with _lock:
        entry = _buckets.get(key)
        if not entry:
            return True, 0
        locked = float(entry.get("locked_until") or 0)
        if locked > t:
            return False, max(1, int(locked - t))
        return True, 0


def record_failure(key: str, now: Optional[float] = None) -> int:
    """Increment failures; lock if threshold reached. Returns retry_after if locked."""
    t = now if now is not None else time.time()
    with _lock:
        entry = _buckets.setdefault(key, {"fails": 0.0, "locked_until": 0.0})
        locked = float(entry.get("locked_until") or 0)
        if locked > t:
            return max(1, int(locked - t))
        fails = int(entry.get("fails") or 0) + 1
        entry["fails"] = float(fails)
        if fails >= MAX_FAILURES:
            entry["locked_until"] = t + LOCKOUT_SECONDS
            entry["fails"] = 0.0
            return LOCKOUT_SECONDS
        return 0


def record_success(key: str) -> None:
    with _lock:
        _buckets.pop(key, None)
