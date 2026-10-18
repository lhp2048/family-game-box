from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


class StorageError(RuntimeError):
    pass


def turso_configured() -> bool:
    return bool(os.environ.get("TURSO_DATABASE_URL", "").strip())


def _on_vercel() -> bool:
    return bool(os.environ.get("VERCEL", "").strip())


def _turso_store():
    from app.turso_store import TursoStore

    return TursoStore(
        os.environ.get("TURSO_DATABASE_URL", "").strip(),
        os.environ.get("TURSO_AUTH_TOKEN", "").strip(),
    )


def health() -> Dict[str, Any]:
    if turso_configured():
        try:
            _turso_store().ping()
        except StorageError:
            return {"storage": "turso", "ready": False}
        return {"storage": "turso", "ready": True}
    if _on_vercel():
        return {"storage": "turso", "ready": False}
    return {"storage": "file", "ready": True}


def data_path(name: str) -> Path:
    return DATA_DIR / name


def load_json(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if turso_configured():
        return _turso_store().load(name, default)
    if _on_vercel():
        raise StorageError("暂时存不上")
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


def save_json(name: str, data: Dict[str, Any]) -> None:
    if turso_configured():
        _turso_store().save(name, data)
        return
    if _on_vercel():
        raise StorageError("暂时存不上")
    path = data_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
