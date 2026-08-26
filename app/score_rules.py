from __future__ import annotations

from typing import Any, Dict


def _int(metrics: Dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(metrics.get(key, default))
    except (TypeError, ValueError):
        return default


def rank_score(game_id: str, mode: str, _tier: str, metrics: Dict[str, Any]) -> int:
    """Higher score is always better for sorting."""
    if game_id in ("24points", "schulte"):
        if mode == "challenge":
            done = _int(metrics, "done")
            time_ms = _int(metrics, "timeMs")
            return done * 1_000_000 - min(time_ms, 999_999)
        time_ms = _int(metrics, "timeMs")
        return 1_000_000 - min(time_ms, 999_999)

    if mode == "challenge":
        correct = _int(metrics, "correct") or _int(metrics, "done")
        total = max(_int(metrics, "total"), 1)
        accuracy = correct * 1000 // total
        time_ms = _int(metrics, "timeMs")
        return accuracy * 1_000_000 + correct * 1000 - min(time_ms // 100, 9999)

    streak = _int(metrics, "maxStreak")
    correct = _int(metrics, "correct")
    return max(streak, 0) * 1000 + correct


def format_display(game_id: str, mode: str, metrics: Dict[str, Any]) -> str:
    if game_id in ("24points", "schulte"):
        if mode == "challenge":
            done = _int(metrics, "done")
            total = _int(metrics, "total")
            time_ms = _int(metrics, "timeMs")
            rate = round(done * 100 / total) if total else 0
            return "完成 %d/%d · %d%% · %s" % (done, total, rate, _fmt_ms(time_ms))
        return "用时 %s" % _fmt_ms(_int(metrics, "timeMs"))

    correct = _int(metrics, "correct")
    total = _int(metrics, "total")
    if mode == "challenge":
        rate = round(correct * 100 / total) if total else 0
        parts = ["正确率 %d%%" % rate]
        if total:
            parts.append("%d/%d" % (correct, total))
        time_ms = _int(metrics, "timeMs")
        if time_ms:
            parts.append(_fmt_ms(time_ms))
        return " · ".join(parts)

    streak = _int(metrics, "maxStreak")
    if streak:
        return "最长连击 %d · 正确 %d" % (streak, correct)
    return "正确 %d" % correct


def _fmt_ms(ms: int) -> str:
    if ms <= 0:
        return "00:00"
    sec = ms // 1000
    return "%02d:%02d" % (sec // 60, sec % 60)
