#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Game registry: built-in + uploaded packages (hot reload, no restart)."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.rank_config import STANDARD_TIER_IDS, TIER_LABELS
from app.storage import DATA_DIR, load_json, save_json

STORE = "games_registry.json"
UPLOAD_DIRNAME = "uploaded-games"
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
MAX_ZIP_BYTES = 40 * 1024 * 1024
ALLOWED_SUFFIXES = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".json",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".mp3",
    ".wav",
    ".ogg",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".txt",
    ".md",
}

# Built-in catalog (source of truth for paths/titles)
BUILTIN_GAMES: List[Dict[str, Any]] = [
    {
        "id": "24points",
        "title": "24 点挑战",
        "subtitle": "心算与整数四则",
        "path": "/games/24points/play.html",
        "entry": "play.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
        "extra": {"library": "/games/24points/library.html"},
    },
    {
        "id": "schulte",
        "title": "舒尔特挑战",
        "subtitle": "注意力训练",
        "path": "/games/schulte/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "stroop",
        "title": "Stroop 色字",
        "subtitle": "抗干扰训练",
        "path": "/games/stroop/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "cancel",
        "title": "划销训练",
        "subtitle": "视觉搜索",
        "path": "/games/cancel/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "simon",
        "title": "Simon Says",
        "subtitle": "听觉专注",
        "path": "/games/simon/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "spot-diff",
        "title": "找不同",
        "subtitle": "细节观察",
        "path": "/games/spot-diff/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "maze",
        "title": "迷宫追踪",
        "subtitle": "路径预判",
        "path": "/games/maze/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "sudoku",
        "title": "数独",
        "subtitle": "逻辑推理",
        "path": "/games/sudoku/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "mental-speed",
        "title": "心算快答",
        "subtitle": "看式子键入得数 · 10 题竞速",
        "path": "/games/mental-speed/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": list(STANDARD_TIER_IDS),
    },
    {
        "id": "number-slide",
        "title": "数字华容道",
        "subtitle": "滑动拼图 · 步数与用时",
        "path": "/games/number-slide/",
        "entry": "index.html",
        "supportsDaily": True,
        "rankable": True,
        "tiers": ["intro", "normal", "hard"],
    },
    {
        "id": "yuwen",
        "title": "语文大擂台",
        "subtitle": "易错题，一关一类",
        "path": "/games/yuwen/",
        "entry": "index.html",
        "supportsDaily": False,
        "rankable": True,
        "tiers": [
            "zuyin",
            "zixing",
            "chengyu",
            "ciyu",
            "bingju",
            "biaodian",
            "mingju",
            "changshi",
            "wenyan-base",
            "gushi",
            "yuyan",
            "xiandai",
            "zonghe",
            "xiuci",
            "wenyan-read",
            "xiandai-extra",
            "gushi-extra",
            "yingyong",
            "mingzhu",
        ],
    },
    {
        "id": "24points-library",
        "title": "24 点 · 解法库",
        "subtitle": "工具 · 不是对局",
        "path": "/games/24points/library.html",
        "entry": "library.html",
        "supportsDaily": False,
        "rankable": False,
        "tiers": [],
        "extra": {"kind": "reference"},
    },
]

_BUILTIN_BY_ID = {g["id"]: g for g in BUILTIN_GAMES}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upload_root() -> Path:
    path = DATA_DIR / UPLOAD_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "builtins": {}, "uploaded": {}}


def _load() -> Dict[str, Any]:
    data = load_json(STORE, _empty_store())
    if not isinstance(data.get("builtins"), dict):
        data["builtins"] = {}
    if not isinstance(data.get("uploaded"), dict):
        data["uploaded"] = {}
    return data


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def validate_game_id(game_id: str) -> str:
    gid = (game_id or "").strip().lower()
    if not gid or len(gid) > 40 or not ID_RE.match(gid):
        raise ValueError("invalid game id (use lowercase letters, digits, hyphens)")
    return gid


def parse_game_json(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("game.json must be an object")
    gid = validate_game_id(str(raw.get("id") or ""))
    title = str(raw.get("title") or "").strip()
    if not title:
        raise ValueError("game.json title required")
    entry = str(raw.get("entry") or "index.html").strip().lstrip("/")
    if not entry or ".." in entry or entry.startswith("/") or "\\" in entry:
        raise ValueError("invalid entry path")
    tiers_raw = raw.get("tiers")
    if tiers_raw is None:
        tiers = list(STANDARD_TIER_IDS)
    elif isinstance(tiers_raw, list):
        tiers = [str(t).strip() for t in tiers_raw if str(t).strip()]
        for t in tiers:
            if t not in STANDARD_TIER_IDS:
                raise ValueError("unknown tier in game.json: %s" % t)
    else:
        raise ValueError("tiers must be an array")
    supports_daily = bool(raw.get("supportsDaily", False))
    defaults = raw.get("difficultyDefaults")
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("difficultyDefaults must be object")
    schema = raw.get("difficultySchema")
    if schema is not None and not isinstance(schema, list):
        raise ValueError("difficultySchema must be array")
    return {
        "id": gid,
        "title": title,
        "subtitle": str(raw.get("subtitle") or "").strip(),
        "entry": entry,
        "tiers": tiers,
        "supportsDaily": supports_daily,
        "difficultyDefaults": defaults if isinstance(defaults, dict) else {},
        "difficultySchema": schema if isinstance(schema, list) else [],
        "modes": raw.get("modes") if isinstance(raw.get("modes"), list) else ["casual", "challenge"],
    }


def _builtin_enabled(store: Dict[str, Any], gid: str) -> bool:
    ov = store.get("builtins", {}).get(gid)
    if isinstance(ov, dict) and "enabled" in ov:
        return bool(ov["enabled"])
    return True


def _public_item(item: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "id": item["id"],
        "title": item["title"],
        "subtitle": item.get("subtitle") or "",
        "status": "ready" if item.get("enabled", True) else "disabled",
        "enabled": bool(item.get("enabled", True)),
        "path": item["path"],
        "source": item.get("source", "builtin"),
        "supportsDaily": bool(item.get("supportsDaily")),
        "rankable": bool(item.get("rankable", True)),
        "tiers": list(item.get("tiers") or []),
    }
    if item.get("extra"):
        out["extra"] = item["extra"]
    if item.get("difficultySchema"):
        out["difficultySchema"] = item["difficultySchema"]
    return out


def list_all_games(*, include_disabled: bool = False) -> List[Dict[str, Any]]:
    store = _load()
    out: List[Dict[str, Any]] = []
    for base in BUILTIN_GAMES:
        enabled = _builtin_enabled(store, base["id"])
        if not include_disabled and not enabled:
            continue
        item = dict(base)
        item["enabled"] = enabled
        item["source"] = "builtin"
        out.append(_public_item(item))
    for gid, meta in sorted((store.get("uploaded") or {}).items()):
        if not isinstance(meta, dict):
            continue
        enabled = bool(meta.get("enabled", False))
        if not include_disabled and not enabled:
            continue
        entry = str(meta.get("entry") or "index.html")
        path = "/uploaded-games/%s/%s" % (gid, entry)
        if entry.endswith("/") or entry == "":
            path = "/uploaded-games/%s/" % gid
        item = {
            "id": gid,
            "title": meta.get("title") or gid,
            "subtitle": meta.get("subtitle") or "",
            "enabled": enabled,
            "path": path,
            "source": "uploaded",
            "supportsDaily": bool(meta.get("supportsDaily")),
            "rankable": True,
            "tiers": list(meta.get("tiers") or STANDARD_TIER_IDS),
            "difficultySchema": meta.get("difficultySchema") or [],
            "uploadedAt": meta.get("uploadedAt") or "",
        }
        out.append(_public_item(item))
    return out


def list_games() -> List[Dict[str, Any]]:
    """Public lobby catalog: enabled only."""
    return list_all_games(include_disabled=False)


def get_game(game_id: str) -> Optional[Dict[str, Any]]:
    gid = (game_id or "").strip()
    for g in list_all_games(include_disabled=True):
        if g["id"] == gid:
            return g
    return None


def game_path_map() -> Dict[str, str]:
    """id -> URL path for daily iframe (enabled games only)."""
    return {g["id"]: g["path"] for g in list_games() if g.get("rankable")}


def rankable_games() -> List[Dict[str, str]]:
    return [
        {"id": g["id"], "title": g["title"]}
        for g in list_all_games(include_disabled=True)
        if g.get("rankable") and g.get("enabled")
    ]


def daily_candidate_games() -> List[Dict[str, Any]]:
    return [
        g
        for g in list_all_games(include_disabled=True)
        if g.get("enabled") and g.get("supportsDaily") and g.get("rankable")
    ]


def set_enabled(game_id: str, enabled: bool) -> Dict[str, Any]:
    gid = (game_id or "").strip()
    store = _load()
    if gid in _BUILTIN_BY_ID:
        store.setdefault("builtins", {})[gid] = {"enabled": bool(enabled)}
        _save(store)
        return get_game(gid) or {}
    uploaded = store.get("uploaded") or {}
    if gid not in uploaded or not isinstance(uploaded.get(gid), dict):
        raise ValueError("unknown gameId: %s" % gid)
    uploaded[gid]["enabled"] = bool(enabled)
    store["uploaded"] = uploaded
    _save(store)
    return get_game(gid) or {}


def delete_uploaded(game_id: str) -> None:
    gid = validate_game_id(game_id)
    if gid in _BUILTIN_BY_ID:
        raise ValueError("cannot delete built-in game")
    store = _load()
    uploaded = store.get("uploaded") or {}
    if gid not in uploaded:
        raise ValueError("unknown uploaded game: %s" % gid)
    del uploaded[gid]
    store["uploaded"] = uploaded
    _save(store)
    dest = upload_root() / gid
    if dest.is_dir():
        shutil.rmtree(dest, ignore_errors=True)


def resolve_uploaded_file(game_id: str, rel: str) -> Tuple[Path, bool]:
    """Return (path, enabled). Raises ValueError if missing."""
    gid = validate_game_id(game_id)
    store = _load()
    meta = (store.get("uploaded") or {}).get(gid)
    if not isinstance(meta, dict):
        raise ValueError("unknown game")
    enabled = bool(meta.get("enabled", False))
    root = (upload_root() / gid).resolve()
    rel = (rel or "").lstrip("/")
    if not rel:
        entry = str(meta.get("entry") or "index.html")
        rel = entry
    if ".." in rel.split("/") or rel.startswith("/"):
        raise ValueError("invalid path")
    target = (root / rel).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("invalid path")
    if target.is_dir():
        index = target / "index.html"
        if index.is_file():
            return index, enabled
        raise ValueError("not found")
    if not target.is_file():
        raise ValueError("not found")
    return target, enabled


def _safe_zip_members(zf: zipfile.ZipFile) -> List[str]:
    names = []
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.endswith("/"):
            continue
        if name.startswith("/") or ".." in name.split("/"):
            raise ValueError("zip contains unsafe path: %s" % info.filename)
        suffix = Path(name).suffix.lower()
        if suffix and suffix not in ALLOWED_SUFFIXES:
            raise ValueError("disallowed file type: %s" % name)
        # allow extensionless? reject
        if not suffix:
            raise ValueError("disallowed file (no extension): %s" % name)
        names.append(name)
    if not names:
        raise ValueError("zip is empty")
    return names


def _find_game_json_root(names: List[str]) -> Tuple[str, str]:
    """Return (prefix, game_json_path_in_zip)."""
    candidates = [n for n in names if n == "game.json" or n.endswith("/game.json")]
    if not candidates:
        raise ValueError("zip missing game.json")
    # prefer shallowest
    candidates.sort(key=lambda n: n.count("/"))
    gj = candidates[0]
    if gj == "game.json":
        return "", gj
    prefix = gj[: -len("game.json")]
    return prefix, gj


def install_zip_bytes(data: bytes, *, keep_enabled: Optional[bool] = None) -> Dict[str, Any]:
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("zip too large")
    if len(data) < 64:
        raise ValueError("zip too small")
    with tempfile.TemporaryDirectory(prefix="fgb_game_") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "pack.zip"
        zip_path.write_bytes(data)
        try:
            zf = zipfile.ZipFile(zip_path, "r")
        except zipfile.BadZipFile as exc:
            raise ValueError("invalid zip") from exc
        with zf:
            names = _safe_zip_members(zf)
            prefix, gj_name = _find_game_json_root(names)
            raw_manifest = json.loads(zf.read(gj_name).decode("utf-8"))
            manifest = parse_game_json(raw_manifest)
            gid = manifest["id"]
            if gid in _BUILTIN_BY_ID:
                raise ValueError("id conflicts with built-in game: %s" % gid)
            entry_in_zip = prefix + manifest["entry"]
            if entry_in_zip not in names:
                raise ValueError("entry not found in zip: %s" % manifest["entry"])
            extract_root = tmp_path / "extract"
            extract_root.mkdir()
            for name in names:
                if prefix and not name.startswith(prefix):
                    continue
                rel = name[len(prefix) :] if prefix else name
                if not rel or ".." in rel.split("/"):
                    continue
                dest = extract_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
            dest_dir = upload_root() / gid
            store = _load()
            prev = (store.get("uploaded") or {}).get(gid)
            was_enabled = bool(prev.get("enabled")) if isinstance(prev, dict) else False
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(extract_root, dest_dir)
            enabled = was_enabled if keep_enabled is None and isinstance(prev, dict) else False
            if keep_enabled is not None:
                enabled = bool(keep_enabled)
            record = {
                "enabled": enabled,
                "title": manifest["title"],
                "subtitle": manifest["subtitle"],
                "entry": manifest["entry"],
                "tiers": manifest["tiers"],
                "supportsDaily": manifest["supportsDaily"],
                "difficultyDefaults": manifest["difficultyDefaults"],
                "difficultySchema": manifest["difficultySchema"],
                "modes": manifest["modes"],
                "uploadedAt": _now(),
            }
            store.setdefault("uploaded", {})[gid] = record
            _save(store)
            # Seed difficulty defaults (fill missing only)
            _seed_difficulty(gid, manifest["difficultyDefaults"])
            return get_game(gid) or _public_item(
                {
                    "id": gid,
                    "title": record["title"],
                    "subtitle": record["subtitle"],
                    "enabled": enabled,
                    "path": "/uploaded-games/%s/%s" % (gid, record["entry"]),
                    "source": "uploaded",
                    "supportsDaily": record["supportsDaily"],
                    "rankable": True,
                    "tiers": record["tiers"],
                    "difficultySchema": record["difficultySchema"],
                }
            )


def _seed_difficulty(game_id: str, defaults: Dict[str, Any]) -> None:
    if not defaults:
        return
    from app import difficulty as difficulty_mod

    difficulty_mod.ensure_uploaded_defaults(game_id, defaults)


def uploaded_difficulty_defaults(game_id: str) -> Dict[str, Any]:
    store = _load()
    meta = (store.get("uploaded") or {}).get(game_id)
    if not isinstance(meta, dict):
        return {}
    raw = meta.get("difficultyDefaults") or {}
    return raw if isinstance(raw, dict) else {}


def uploaded_difficulty_schema(game_id: str) -> List[Dict[str, Any]]:
    store = _load()
    meta = (store.get("uploaded") or {}).get(game_id)
    if not isinstance(meta, dict):
        return []
    raw = meta.get("difficultySchema") or []
    return raw if isinstance(raw, list) else []


def all_difficulty_game_ids() -> List[str]:
    ids = [g["id"] for g in BUILTIN_GAMES if g.get("rankable")]
    store = _load()
    for gid in store.get("uploaded") or {}:
        if gid not in ids:
            ids.append(gid)
    return ids


def tier_labels_for(game_id: str) -> Dict[str, str]:
    g = get_game(game_id)
    tiers = (g or {}).get("tiers") or STANDARD_TIER_IDS
    return {t: TIER_LABELS.get(t, t) for t in tiers}
