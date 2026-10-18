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


def login_as(
    client,
    username: str = "player1",
    password: str = "pass1234",
    passphrase: str | None = None,
):
    """Ensure TestClient has a valid fgb_user cookie (register or login)."""
    body = {"username": username, "password": password}
    if passphrase is not None:
        body["passphrase"] = passphrase
    r = client.post(url("/api/v1/auth/register"), json=body)
    if r.status_code != 200:
        r = client.post(
            url("/api/v1/auth/login"),
            json={"username": username, "password": password},
        )
    assert r.status_code == 200, r.text
    return r
