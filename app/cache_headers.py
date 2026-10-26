"""Cache-Control for static assets vs HTML (Vercel edge + origin)."""

from __future__ import annotations

import os
from typing import Iterable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Long-lived assets: CSS/JS/images/audio/fonts (cache at browser + Vercel edge).
CACHE_LONG = "public, max-age=31536000, s-maxage=31536000, immutable"

# HTML and dynamic pages: always revalidate.
CACHE_HTML = "no-cache, must-revalidate"

# API responses.
CACHE_API = "private, no-store"

_LONG_EXTENSIONS = frozenset(
    {
        ".css",
        ".js",
        ".mjs",
        ".map",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".avif",
        ".svg",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp3",
        ".mp4",
        ".webm",
        ".ogg",
        ".wav",
        ".json",
    }
)


def cache_control_for_path(path: str) -> str | None:
    """Return Cache-Control value for a request path, or None to leave unchanged."""
    p = (path or "").split("?", 1)[0].lower()
    if not p:
        return CACHE_HTML

    # Strip optional mount prefix segments — match on resource suffix.
    if "/api/" in p or p.endswith("/api") or p.startswith("/api/"):
        return CACHE_API

    ext = os.path.splitext(p)[1]
    if ext == ".html":
        return CACHE_HTML

    if ext in _LONG_EXTENSIONS:
        return CACHE_LONG

    # Extensionless paths: lobby / game directory indexes.
    if p.endswith("/") or p.rstrip("/").split("/")[-1] in (
        "",
        "index",
        "admin",
        "leaderboard",
        "daily",
        "play",
        "library",
    ):
        return CACHE_HTML

    return None


def _replace_header(headers: list[tuple[bytes, bytes]], name: bytes, value: bytes) -> list[tuple[bytes, bytes]]:
    out: list[tuple[bytes, bytes]] = []
    replaced = False
    for k, v in headers:
        if k.lower() == name:
            if not replaced:
                out.append((name, value))
                replaced = True
            continue
        out.append((k, v))
    if not replaced:
        out.append((name, value))
    return out


class CacheHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        policy = cache_control_for_path(path)

        async def send_with_cache(message: Message) -> None:
            if message["type"] == "http.response.start" and policy:
                headers: Iterable[tuple[bytes, bytes]] = message.get("headers") or []
                headers = _replace_header(list(headers), b"cache-control", policy.encode("latin-1"))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_cache)
