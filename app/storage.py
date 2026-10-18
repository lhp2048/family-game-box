"""JSON document storage.

Local installs keep writing ``data/*.json``. When ``TURSO_DATABASE_URL`` and
``TURSO_AUTH_TOKEN`` are both set, the same documents are stored in a Turso
``kv`` table so a serverless host can persist them.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

_KV_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS kv ("
    "name TEXT PRIMARY KEY NOT NULL, "
    "doc TEXT NOT NULL)"
)
_UPSERT = (
    "INSERT INTO kv (name, doc) VALUES (?, ?) "
    "ON CONFLICT(name) DO UPDATE SET doc = excluded.doc"
)

_lock = threading.Lock()
_conn: Any = None
_conn_key: Tuple[str, str] | None = None


def data_path(name: str) -> Path:
    return DATA_DIR / name


def storage_backend() -> str:
    """``turso`` when both credentials are set, ``file`` when neither is, else ``incomplete``."""
    url, token = _credentials()
    if url and token:
        return "turso"
    if url or token:
        return "incomplete"
    return "file"


def reset_backend_cache() -> None:
    """Drop a cached Turso connection. Tests use this between cases."""
    with _lock:
        _drop_conn_locked()


def load_json(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if _backend_or_raise() == "turso":
        return _turso_load(name, default)
    return _file_load(name, default)


def save_json(name: str, data: Dict[str, Any]) -> None:
    if _backend_or_raise() == "turso":
        _turso_save(name, data)
        return
    _file_save(name, data)


def _credentials() -> Tuple[str, str]:
    url = os.environ.get("TURSO_DATABASE_URL", "").strip()
    token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
    return url, token


def _backend_or_raise() -> str:
    backend = storage_backend()
    if backend == "incomplete":
        raise RuntimeError(
            "Set both TURSO_DATABASE_URL and TURSO_AUTH_TOKEN, or leave both unset for file storage"
        )
    return backend


def _file_load(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    path = data_path(name)
    if not path.is_file():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return dict(default)


def _file_save(name: str, data: Dict[str, Any]) -> None:
    path = data_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _drop_conn_locked() -> None:
    global _conn, _conn_key
    conn = _conn
    _conn = None
    _conn_key = None
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def _ensure_conn_locked() -> Any:
    global _conn, _conn_key
    url, token = _credentials()
    key = (url, token)
    if _conn is not None and _conn_key == key:
        return _conn
    _drop_conn_locked()
    import libsql

    conn = libsql.connect(database=url, auth_token=token, _check_same_thread=False)
    try:
        conn.execute(_KV_SCHEMA)
        conn.commit()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    _conn = conn
    _conn_key = key
    return conn


def _with_conn(fn: Any) -> Any:
    with _lock:
        try:
            return fn(_ensure_conn_locked())
        except Exception:
            _drop_conn_locked()
            return fn(_ensure_conn_locked())


def _turso_load(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    row = _with_conn(
        lambda conn: conn.execute("SELECT doc FROM kv WHERE name = ?", (name,)).fetchone()
    )
    if not row or row[0] is None:
        return dict(default)
    try:
        data = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return dict(default)
    if isinstance(data, dict):
        return data
    return dict(default)


def _turso_save(name: str, data: Dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    def op(conn: Any) -> None:
        conn.execute(_UPSERT, (name, payload))
        conn.commit()

    _with_conn(op)
