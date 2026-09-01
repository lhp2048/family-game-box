from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.rank_config import STANDARD_TIER_IDS
from app.storage import load_json, save_json

STORE = "difficulty.json"
TIER_IDS = list(STANDARD_TIER_IDS)
GAME_IDS = [
    "24points",
    "schulte",
    "stroop",
    "cancel",
    "simon",
    "spot-diff",
    "maze",
    "sudoku",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_difficulty() -> Dict[str, Any]:
    return {
        "version": 1,
        "updatedAt": "",
        "games": {
            "schulte": {
                "tiers": {
                    "intro": {"size": 3, "reverse": False, "label": "入门"},
                    "simple": {"size": 4, "reverse": False, "label": "简单"},
                    "normal": {"size": 5, "reverse": False, "label": "普通"},
                    "hard": {"size": 5, "reverse": True, "label": "困难"},
                    "master": {"size": 6, "reverse": False, "label": "大师"},
                    "god": {"size": 6, "reverse": True, "label": "大神"},
                }
            },
            "sudoku": {
                "tiers": {
                    "intro": {"size": 4, "givens": 10, "label": "入门"},
                    "simple": {"size": 4, "givens": 8, "label": "简单"},
                    "normal": {"size": 6, "givens": 24, "label": "普通"},
                    "hard": {"size": 6, "givens": 20, "label": "困难"},
                    "master": {"size": 9, "givens": 36, "label": "大师"},
                    "god": {"size": 9, "givens": 28, "label": "大神"},
                }
            },
            "stroop": {
                "tiers": {
                    "intro": {
                        "label": "入门",
                        "trialLimit": 20,
                        "timeLimitMs": 0,
                        "congruentRate": 0.35,
                    },
                    "simple": {
                        "label": "简单",
                        "trialLimit": 30,
                        "timeLimitMs": 0,
                        "congruentRate": 0.28,
                    },
                    "normal": {
                        "label": "普通",
                        "trialLimit": 0,
                        "timeLimitMs": 60000,
                        "congruentRate": 0.2,
                    },
                    "hard": {
                        "label": "困难",
                        "trialLimit": 0,
                        "timeLimitMs": 90000,
                        "congruentRate": 0.15,
                    },
                    "master": {
                        "label": "大师",
                        "trialLimit": 50,
                        "timeLimitMs": 0,
                        "congruentRate": 0.12,
                    },
                    "god": {
                        "label": "大神",
                        "trialLimit": 0,
                        "timeLimitMs": 120000,
                        "congruentRate": 0.1,
                    },
                }
            },
            "cancel": {
                "tiers": {
                    "intro": {"size": 8, "pct": 0.12, "label": "入门"},
                    "simple": {"size": 10, "pct": 0.11, "label": "简单"},
                    "normal": {"size": 12, "pct": 0.10, "label": "普通"},
                    "hard": {"size": 14, "pct": 0.09, "label": "困难"},
                    "master": {"size": 16, "pct": 0.07, "label": "大师"},
                    "god": {"size": 18, "pct": 0.06, "label": "大神"},
                }
            },
            "simon": {
                "tiers": {
                    "intro": {"label": "入门", "trials": 15},
                    "simple": {"label": "简单", "trials": 20},
                    "normal": {"label": "普通", "trials": 30},
                    "hard": {"label": "困难", "trials": 40},
                    "master": {"label": "大师", "trials": 50},
                    "god": {"label": "大神", "trials": 60},
                }
            },
            "spot-diff": {
                "tiers": {
                    "intro": {"n": 5, "diffs": 3, "label": "入门"},
                    "simple": {"n": 6, "diffs": 4, "label": "简单"},
                    "normal": {"n": 7, "diffs": 5, "label": "普通"},
                    "hard": {"n": 8, "diffs": 6, "label": "困难"},
                    "master": {"n": 9, "diffs": 8, "label": "大师"},
                    "god": {"n": 10, "diffs": 10, "label": "大神"},
                }
            },
            "maze": {
                "tiers": {
                    "intro": {"size": 9, "label": "入门"},
                    "simple": {"size": 11, "label": "简单"},
                    "normal": {"size": 15, "label": "普通"},
                    "hard": {"size": 19, "label": "困难"},
                    "master": {"size": 21, "label": "大师"},
                    "god": {"size": 31, "label": "大神"},
                }
            },
            "24points": {
                "cuts": [0.12, 0.28, 0.50, 0.72, 0.88, 1.01],
                "tiers": {
                    "intro": {
                        "minNum": 1,
                        "maxNum": 9,
                        "label": "入门",
                        "desc": "数字范围：多为 1–9 的小数。",
                    },
                    "simple": {
                        "minNum": 1,
                        "maxNum": 10,
                        "label": "简单",
                        "desc": "数字范围：仍以较小数字为主。",
                    },
                    "normal": {
                        "minNum": 1,
                        "maxNum": 12,
                        "label": "普通",
                        "desc": "数字范围：小到中等数字都有。",
                    },
                    "hard": {
                        "minNum": 1,
                        "maxNum": 13,
                        "label": "困难",
                        "desc": "数字范围：更容易抽到较大数字。",
                    },
                    "master": {
                        "minNum": 1,
                        "maxNum": 16,
                        "label": "大师",
                        "desc": "数字范围：大数更常见。",
                    },
                    "god": {
                        "minNum": 1,
                        "maxNum": 24,
                        "label": "大神",
                        "desc": "数字范围：全库跨度。",
                    },
                },
            },
        },
    }


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "updatedAt": "", "games": {}}


def _load_store() -> Dict[str, Any]:
    data = load_json(STORE, _empty_store())
    if not isinstance(data.get("games"), dict):
        data["games"] = {}
    return data


def _save_store(data: Dict[str, Any]) -> None:
    data["updatedAt"] = _now()
    save_json(STORE, data)


def _merge_game(default_game: Dict[str, Any], stored: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(default_game)
    if "cuts" in stored and stored["cuts"] is not None:
        out["cuts"] = list(stored["cuts"])
    st_tiers = stored.get("tiers") or {}
    if isinstance(st_tiers, dict):
        for tid, vals in st_tiers.items():
            if tid not in out["tiers"] or not isinstance(vals, dict):
                continue
            merged = copy.deepcopy(out["tiers"][tid])
            merged.update(vals)
            out["tiers"][tid] = merged
    return out


def get_difficulty(game_id: Optional[str] = None) -> Dict[str, Any]:
    defaults = default_difficulty()
    store = _load_store()
    games: Dict[str, Any] = {}
    for gid in GAME_IDS:
        base = defaults["games"][gid]
        overlay = store.get("games", {}).get(gid) or {}
        games[gid] = _merge_game(base, overlay if isinstance(overlay, dict) else {})
    if game_id:
        if game_id not in games:
            raise ValueError("unknown gameId: %s" % game_id)
        return {
            "version": 1,
            "updatedAt": store.get("updatedAt") or "",
            "games": {game_id: games[game_id]},
        }
    return {
        "version": 1,
        "updatedAt": store.get("updatedAt") or "",
        "games": games,
    }


def _validate_tier_common(tid: str, tier: Dict[str, Any]) -> None:
    if tid not in TIER_IDS:
        raise ValueError("invalid tier: %s" % tid)
    if not isinstance(tier, dict):
        raise ValueError("tier must be object: %s" % tid)


def _validate_schulte(tiers: Dict[str, Any]) -> None:
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        size = int(t.get("size", 0))
        if size not in (3, 4, 5, 6):
            raise ValueError("schulte size invalid: %s" % tid)
        if not isinstance(t.get("reverse", False), bool):
            raise ValueError("schulte reverse must be bool: %s" % tid)


def _validate_sudoku(tiers: Dict[str, Any]) -> None:
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        size = int(t.get("size", 0))
        if size not in (4, 6, 9):
            raise ValueError("sudoku size invalid: %s" % tid)
        givens = int(t.get("givens", 0))
        if givens < 1 or givens > size * size - 1:
            raise ValueError("sudoku givens invalid: %s" % tid)


def _validate_stroop(tiers: Dict[str, Any]) -> None:
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        trial = int(t.get("trialLimit", 0))
        time_ms = int(t.get("timeLimitMs", 0))
        if trial < 0 or time_ms < 0:
            raise ValueError("stroop limits must be >=0: %s" % tid)
        if trial <= 0 and time_ms <= 0:
            raise ValueError("stroop needs trialLimit or timeLimitMs: %s" % tid)
        rate = float(t.get("congruentRate", 0))
        if rate < 0 or rate > 1:
            raise ValueError("stroop congruentRate invalid: %s" % tid)


def _validate_cancel(tiers: Dict[str, Any]) -> None:
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        size = int(t.get("size", 0))
        if size < 8 or size > 20 or size % 2:
            raise ValueError("cancel size invalid: %s" % tid)
        pct = float(t.get("pct", 0))
        if pct <= 0 or pct >= 0.5:
            raise ValueError("cancel pct invalid: %s" % tid)


def _validate_simon(tiers: Dict[str, Any]) -> None:
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        trials = int(t.get("trials", 0))
        if trials < 5 or trials > 100:
            raise ValueError("simon trials invalid: %s" % tid)


def _validate_spot(tiers: Dict[str, Any]) -> None:
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        n = int(t.get("n", 0))
        diffs = int(t.get("diffs", 0))
        if n < 4 or n > 12:
            raise ValueError("spot-diff n invalid: %s" % tid)
        if diffs < 1 or diffs > (n * n) // 2:
            raise ValueError("spot-diff diffs invalid: %s" % tid)


def _validate_maze(tiers: Dict[str, Any]) -> None:
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        size = int(t.get("size", 0))
        if size < 5 or size > 31 or size % 2 == 0:
            raise ValueError("maze size invalid: %s" % tid)


def _validate_24points(game: Dict[str, Any]) -> None:
    cuts = game.get("cuts")
    if cuts is not None:
        if not isinstance(cuts, list) or len(cuts) != 6:
            raise ValueError("24points cuts must have length 6")
        prev = -1.0
        for c in cuts:
            v = float(c)
            if v < prev:
                raise ValueError("24points cuts must be non-decreasing")
            prev = v
        if float(cuts[-1]) < 1.0:
            raise ValueError("24points cuts last must be >= 1.0")
    tiers = game.get("tiers") or {}
    for tid, t in tiers.items():
        _validate_tier_common(tid, t)
        mn = int(t.get("minNum", 1))
        mx = int(t.get("maxNum", 24))
        if mn < 0 or mx < mn or mx > 24:
            raise ValueError("24points num range invalid: %s" % tid)


_VALIDATORS = {
    "schulte": lambda g: _validate_schulte(g.get("tiers") or {}),
    "sudoku": lambda g: _validate_sudoku(g.get("tiers") or {}),
    "stroop": lambda g: _validate_stroop(g.get("tiers") or {}),
    "cancel": lambda g: _validate_cancel(g.get("tiers") or {}),
    "simon": lambda g: _validate_simon(g.get("tiers") or {}),
    "spot-diff": lambda g: _validate_spot(g.get("tiers") or {}),
    "maze": lambda g: _validate_maze(g.get("tiers") or {}),
    "24points": _validate_24points,
}


def validate_game(game_id: str, payload: Dict[str, Any]) -> None:
    if game_id not in GAME_IDS:
        raise ValueError("unknown gameId: %s" % game_id)
    if not isinstance(payload, dict):
        raise ValueError("game payload must be object")
    # Validate against merged view so partial updates still check full tier fields
    defaults = default_difficulty()["games"][game_id]
    merged = _merge_game(defaults, payload)
    _VALIDATORS[game_id](merged)


def put_difficulty(games_partial: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(games_partial, dict) or not games_partial:
        raise ValueError("games required")
    store = _load_store()
    games_store = store.setdefault("games", {})
    for gid, payload in games_partial.items():
        if not isinstance(payload, dict):
            raise ValueError("invalid payload for %s" % gid)
        validate_game(gid, payload)
        existing = games_store.get(gid) if isinstance(games_store.get(gid), dict) else {}
        # Store overlay: deep-merge into existing overlay then keep only overrides shape
        new_overlay: Dict[str, Any] = copy.deepcopy(existing) if existing else {}
        if "cuts" in payload:
            new_overlay["cuts"] = list(payload["cuts"])
        if "tiers" in payload and isinstance(payload["tiers"], dict):
            tiers_out = new_overlay.setdefault("tiers", {})
            for tid, vals in payload["tiers"].items():
                if not isinstance(vals, dict):
                    continue
                cur = tiers_out.get(tid) if isinstance(tiers_out.get(tid), dict) else {}
                merged_tier = copy.deepcopy(cur)
                merged_tier.update(vals)
                tiers_out[tid] = merged_tier
        games_store[gid] = new_overlay
        # Re-validate full merged result
        validate_game(gid, games_store[gid])
    _save_store(store)
    return get_difficulty()


def reset_difficulty(game_id: Optional[str] = None) -> Dict[str, Any]:
    store = _load_store()
    if game_id:
        if game_id not in GAME_IDS:
            raise ValueError("unknown gameId: %s" % game_id)
        store.get("games", {}).pop(game_id, None)
    else:
        store["games"] = {}
    _save_store(store)
    return get_difficulty(game_id) if game_id else get_difficulty()
