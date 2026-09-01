from __future__ import annotations

import os


DEFAULT_ROOT_PATH = "/game-box"


def get_root_path() -> str:
    """Normalized app mount prefix, e.g. '/game-box', or '' for site root."""
    raw = os.environ.get("ROOT_PATH", DEFAULT_ROOT_PATH).strip()
    if raw in ("", "/"):
        return ""
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/")


def with_root(path: str, root: str | None = None) -> str:
    """Join root prefix with an absolute path starting with '/'."""
    prefix = get_root_path() if root is None else root
    if not path.startswith("/"):
        path = "/" + path
    if not prefix:
        return path
    if path == "/":
        return prefix + "/"
    return prefix + path
