from __future__ import annotations

from urllib.parse import quote

from app.daily_admin import play_cookie_ok, require_admin
from app.root_path import get_root_path, with_root


def safe_next(raw: str) -> str:
    if not raw.startswith("/") or raw.startswith("//"):
        return with_root("/")
    return raw


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
    from app.daily_admin import _load

    if not _load().get("playGateEnabled"):
        return True
    if not needs_play(method, path):
        return True
    try:
        require_admin(admin_token)
        return True
    except PermissionError:
        pass
    return play_cookie_ok(cookie)


def gate_location(path: str) -> str:
    return with_root("/play-gate") + "?next=" + quote(safe_next(path), safe="/")
