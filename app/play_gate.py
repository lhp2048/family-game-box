from __future__ import annotations

import posixpath
from urllib.parse import quote, unquote

from app.daily_admin import play_cookie_ok, play_gate_snapshot, require_admin
from app.root_path import get_root_path, with_root


def _decode_next(raw: str) -> str:
    prev = raw
    for _ in range(5):
        nxt = unquote(prev)
        if nxt == prev:
            return nxt
        prev = nxt
    return prev


def safe_next(raw: str) -> str:
    fallback = with_root("/")
    if not raw:
        return fallback
    decoded = _decode_next(raw)
    if "\\" in decoded or any(ord(c) < 32 or ord(c) == 127 for c in decoded):
        return fallback
    if not decoded.startswith("/") or decoded.startswith("//"):
        return fallback
    normalized = posixpath.normpath(decoded)
    if normalized.startswith("//") or not normalized.startswith("/"):
        return fallback
    return decoded


def _relative(path: str) -> str:
    prefix = get_root_path()
    if prefix and (path == prefix or path.startswith(prefix + "/")):
        path = path[len(prefix) :] or "/"
    return path


def needs_play(method: str, path: str) -> bool:
    rel = _relative(path)
    if rel.startswith("/yuwen-daily/leaderboard") or rel.startswith("/daily/leaderboard"):
        return False
    if rel == "/daily" or rel.startswith("/daily/"):
        return True
    if rel == "/yuwen-daily" or rel.startswith("/yuwen-daily/"):
        return True
    if rel == "/games" or rel.startswith("/games/"):
        return True
    if rel == "/uploaded-games" or rel.startswith("/uploaded-games/"):
        return True
    if method == "GET" and rel in ("/api/v1/daily/today", "/api/v1/yuwen-daily/today"):
        return True
    if method == "POST" and rel in (
        "/api/v1/scores",
        "/api/v1/daily/runs",
        "/api/v1/yuwen-daily/answer",
        "/api/v1/yuwen-daily/finish",
    ):
        return True
    if method == "PATCH" and rel.startswith("/api/v1/daily/runs/"):
        return True
    return False


def allowed(method: str, path: str, cookie: str | None, admin_token: str | None) -> bool:
    if not needs_play(method, path):
        return True
    if not play_gate_snapshot()["playGateEnabled"]:
        return True
    if admin_token:
        try:
            require_admin(admin_token)
            return True
        except PermissionError:
            pass
    return play_cookie_ok(cookie)


def gate_location(path: str) -> str:
    return with_root("/play-gate") + "?next=" + quote(safe_next(path), safe="/")


def needs_user(method: str, path: str) -> bool:
    """Same protected set as play-gate (games / daily play / score writes)."""
    return needs_play(method, path)


def user_allowed(
    method: str, path: str, user_cookie: str | None, admin_token: str | None
) -> bool:
    if not needs_user(method, path):
        return True
    if admin_token:
        try:
            require_admin(admin_token)
            return True
        except PermissionError:
            pass
    from app.users import user_cookie_ok

    return user_cookie_ok(user_cookie)


def login_location(path: str) -> str:
    return with_root("/login") + "?next=" + quote(safe_next(path), safe="/")
