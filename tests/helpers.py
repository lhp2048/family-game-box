from __future__ import annotations

from app.root_path import get_root_path

PREFIX = get_root_path()


def url(path: str) -> str:
    """Prefix absolute API/page paths with ROOT_PATH when configured."""
    if not path.startswith("/"):
        path = "/" + path
    if not PREFIX:
        return path
    if path == "/":
        return PREFIX + "/"
    return PREFIX + path
