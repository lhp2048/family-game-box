from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.rank_config import GAME_TIERS, RANKABLE_GAMES, tier_label
from app.score_rules import format_display, rank_score
from app.storage import load_json, save_json
from app.terminals import get_terminal, nickname_lookup, resolve_nickname, touch_terminal, validate_terminal_id

_MAX_ENTRIES = 5000
_LEADERBOARD_LIMIT = 50
_RECENT_LIMIT = 20

_GAME_TITLE = {g["id"]: g["title"] for g in RANKABLE_GAMES}
_MODE_TITLE = {"casual": "休闲", "challenge": "挑战"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "entries": []}


def _entry_key(game_id: str, mode: str, tier: str) -> str:
    return "%s|%s|%s" % (game_id, mode, tier)


def _load_entries() -> List[Dict[str, Any]]:
    store = load_json("scores.json", _empty_store())
    entries = store.get("entries", [])
    return entries if isinstance(entries, list) else []


def _save_entries(entries: List[Dict[str, Any]]) -> None:
    if len(entries) > _MAX_ENTRIES:
        entries = sorted(entries, key=lambda e: e.get("playedAt", ""), reverse=True)[:_MAX_ENTRIES]
    save_json("scores.json", {"version": 1, "entries": entries})


def _best_for_terminal(entries: List[Dict[str, Any]], terminal_id: str, game_id: str, mode: str, tier: str):
    best = None
    for item in entries:
        if item.get("terminalId") != terminal_id:
            continue
        if item.get("gameId") != game_id or item.get("mode") != mode or item.get("tier") != tier:
            continue
        if best is None or int(item.get("score", 0)) > int(best.get("score", 0)):
            best = item
    return best


def submit_score(
    terminal_id: str,
    game_id: str,
    mode: str,
    tier: str,
    metrics: Dict[str, Any],
    display: str = "",
    tier_label_override: str = "",
) -> Dict[str, Any]:
    if not validate_terminal_id(terminal_id):
        raise ValueError("invalid terminal id")
    if mode not in ("casual", "challenge"):
        raise ValueError("invalid mode")
    if game_id not in GAME_TIERS:
        raise ValueError("unsupported game")
    tier = (tier or "default").strip()
    allowed = GAME_TIERS.get(game_id, [])
    if tier not in allowed:
        raise ValueError("invalid tier for game")

    terminal = get_terminal(terminal_id)
    if not terminal:
        raise ValueError("terminal not registered")

    touch_terminal(terminal_id)
    score = rank_score(game_id, mode, tier, metrics)
    label = tier_label_override or tier_label(tier)
    shown = (display or "").strip() or format_display(game_id, mode, metrics)
    now = _now()
    entries = _load_entries()
    previous = _best_for_terminal(entries, terminal_id, game_id, mode, tier)
    is_personal_best = previous is None or score > int(previous.get("score", 0))

    entry = {
        "id": str(uuid.uuid4()),
        "terminalId": terminal_id,
        "nickname": terminal.get("nickname", ""),
        "gameId": game_id,
        "mode": mode,
        "tier": tier,
        "tierLabel": label,
        "score": score,
        "display": shown,
        "metrics": metrics,
        "playedAt": now,
        "isPersonalBest": is_personal_best,
    }
    entries.append(entry)
    _save_entries(entries)

    rank = leaderboard_rank(entries, game_id, mode, tier, score, terminal_id)
    return {
        "ok": True,
        "isPersonalBest": is_personal_best,
        "previousBest": previous,
        "entry": entry,
        "rank": rank,
    }


def leaderboard_rank(
    entries: List[Dict[str, Any]],
    game_id: str,
    mode: str,
    tier: str,
    score: int,
    terminal_id: str,
) -> int:
    board = leaderboard_entries(entries, game_id, mode, tier, limit=1000)
    for idx, item in enumerate(board, start=1):
        if item.get("terminalId") == terminal_id and int(item.get("score", 0)) == score:
            return idx
    return 0


def leaderboard_entries(
    entries: List[Dict[str, Any]],
    game_id: str,
    mode: str,
    tier: str,
    limit: int = _LEADERBOARD_LIMIT,
) -> List[Dict[str, Any]]:
    filtered = [
        e
        for e in entries
        if e.get("gameId") == game_id and e.get("mode") == mode and e.get("tier") == tier
    ]
    best_by_terminal: Dict[str, Dict[str, Any]] = {}
    for item in filtered:
        tid = str(item.get("terminalId", ""))
        if not tid:
            continue
        prev = best_by_terminal.get(tid)
        if prev is None or int(item.get("score", 0)) > int(prev.get("score", 0)):
            best_by_terminal[tid] = item
    board = sorted(best_by_terminal.values(), key=lambda e: int(e.get("score", 0)), reverse=True)
    return board[:limit]


def get_leaderboard(game_id: str, mode: str, tier: str, limit: int = 20) -> Dict[str, Any]:
    if game_id not in GAME_TIERS:
        raise ValueError("unsupported game")
    if mode not in ("casual", "challenge"):
        raise ValueError("invalid mode")
    tier = (tier or "default").strip()
    if tier not in GAME_TIERS.get(game_id, []):
        raise ValueError("invalid tier for game")
    entries = _load_entries()
    board = leaderboard_entries(entries, game_id, mode, tier, limit=limit)
    nicks = nickname_lookup()
    return {
        "gameId": game_id,
        "mode": mode,
        "tier": tier,
        "tierLabel": tier_label(tier),
        "items": [
            {
                "rank": idx,
                "nickname": resolve_nickname(
                    str(item.get("terminalId", "")),
                    fallback=str(item.get("nickname", "")),
                    lookup=nicks,
                ),
                "terminalId": item.get("terminalId", ""),
                "display": item.get("display", ""),
                "score": item.get("score", 0),
                "playedAt": item.get("playedAt"),
            }
            for idx, item in enumerate(board, start=1)
        ],
    }


def get_personal_bests(terminal_id: str, game_id: Optional[str] = None) -> Dict[str, Any]:
    if not validate_terminal_id(terminal_id):
        raise ValueError("invalid terminal id")
    entries = _load_entries()
    bests: Dict[str, Any] = {}
    for gid, tiers in GAME_TIERS.items():
        if game_id and gid != game_id:
            continue
        game_best: Dict[str, Any] = {}
        for mode in ("casual", "challenge"):
            mode_best: Dict[str, Any] = {}
            for tier in tiers:
                item = _best_for_terminal(entries, terminal_id, gid, mode, tier)
                if item:
                    mode_best[tier] = {
                        "display": item.get("display", ""),
                        "score": item.get("score", 0),
                        "playedAt": item.get("playedAt"),
                        "tierLabel": item.get("tierLabel", tier_label(tier)),
                    }
            if mode_best:
                game_best[mode] = mode_best
        if game_best:
            bests[gid] = game_best
    return {"terminalId": terminal_id, "bests": bests}


def global_leaderboard_entries(
    entries: List[Dict[str, Any]],
    limit: int = _LEADERBOARD_LIMIT,
) -> List[Dict[str, Any]]:
    """All score records, newest first. No game/mode/tier grouping."""
    ordered = sorted(entries, key=lambda e: str(e.get("playedAt", "")), reverse=True)
    return ordered[:limit]


def get_global_leaderboard(limit: int = 50) -> Dict[str, Any]:
    entries = _load_entries()
    board = global_leaderboard_entries(entries, limit=limit)
    nicks = nickname_lookup()
    return {
        "kind": "global",
        "items": [
            {
                "rank": idx,
                "nickname": resolve_nickname(
                    str(item.get("terminalId", "")),
                    fallback=str(item.get("nickname", "")),
                    lookup=nicks,
                ),
                "terminalId": item.get("terminalId", ""),
                "display": item.get("display", ""),
                "playedAt": item.get("playedAt"),
            }
            for idx, item in enumerate(board, start=1)
        ],
    }


def get_recent_leaderboard(limit: int = _RECENT_LIMIT) -> Dict[str, Any]:
    entries = _load_entries()
    board = global_leaderboard_entries(entries, limit=limit)
    nicks = nickname_lookup()
    return {
        "kind": "recent",
        "items": [
            {
                "rank": idx,
                "nickname": resolve_nickname(
                    str(item.get("terminalId", "")),
                    fallback=str(item.get("nickname", "")),
                    lookup=nicks,
                ),
                "terminalId": item.get("terminalId", ""),
                "gameId": item.get("gameId", ""),
                "gameTitle": _GAME_TITLE.get(item.get("gameId", ""), item.get("gameId", "")),
                "mode": item.get("mode", ""),
                "modeLabel": _MODE_TITLE.get(item.get("mode", ""), item.get("mode", "")),
                "tierLabel": item.get("tierLabel", tier_label(str(item.get("tier", "")))),
                "display": item.get("display", ""),
                "playedAt": item.get("playedAt"),
            }
            for idx, item in enumerate(board, start=1)
        ],
    }


def latest_for_terminal(terminal_id: str) -> Optional[Dict[str, Any]]:
    if not terminal_id:
        return None
    best = None
    for item in _load_entries():
        if item.get("terminalId") != terminal_id:
            continue
        if best is None or str(item.get("playedAt") or "") > str(best.get("playedAt") or ""):
            best = item
    if not best:
        return None
    return {
        "gameId": best.get("gameId", ""),
        "gameTitle": _GAME_TITLE.get(best.get("gameId", ""), best.get("gameId", "")),
        "display": best.get("display", ""),
        "playedAt": best.get("playedAt"),
    }
