from __future__ import annotations

from typing import Any, Dict, List

STANDARD_TIER_IDS = ["intro", "simple", "normal", "hard", "master", "god"]

TIER_LABELS: Dict[str, str] = {
    "intro": "入门",
    "simple": "简单",
    "normal": "普通",
    "hard": "困难",
    "master": "大师",
    "god": "大神",
    # legacy labels (old scores)
    "time60": "60 秒",
    "time120": "120 秒",
    "trials20": "20 试次",
    "trials30": "30 试次",
    "trials50": "50 试次",
    "easy": "简单",
    "mid": "中等",
    "digit_easy": "数字 · 简单",
    "digit_mid": "数字 · 中等",
    "digit_hard": "数字 · 困难",
    "hanzi_easy": "汉字 · 简单",
    "hanzi_mid": "汉字 · 中等",
    "hanzi_hard": "汉字 · 困难",
    "4": "四宫",
    "6": "六宫",
    "9": "九宫",
    "5": "5×5",
    "7": "7×7",
    "8": "8×8",
    "m9": "入门 9×9",
    "m15": "标准 15×15",
    "m21": "进阶 21×21",
    "m31": "大师 31×31",
    "default": "默认",
}

GAME_TIERS: Dict[str, List[str]] = {
    "24points": STANDARD_TIER_IDS[:],
    "schulte": STANDARD_TIER_IDS[:],
    "stroop": STANDARD_TIER_IDS[:],
    "cancel": STANDARD_TIER_IDS[:],
    "simon": STANDARD_TIER_IDS[:],
    "spot-diff": STANDARD_TIER_IDS[:],
    "maze": STANDARD_TIER_IDS[:],
    "sudoku": STANDARD_TIER_IDS[:],
}

RANKABLE_GAMES = [
    {"id": "24points", "title": "24 点挑战"},
    {"id": "schulte", "title": "舒尔特挑战"},
    {"id": "stroop", "title": "Stroop 色字"},
    {"id": "cancel", "title": "划销训练"},
    {"id": "simon", "title": "Simon Says"},
    {"id": "spot-diff", "title": "找不同"},
    {"id": "maze", "title": "迷宫追踪"},
    {"id": "sudoku", "title": "数独"},
]


def tier_label(tier: str, fallback: str = "") -> str:
    return TIER_LABELS.get(tier, fallback or tier)


def rank_meta() -> Dict[str, Any]:
    return {
        "games": RANKABLE_GAMES,
        "modes": [
            {"id": "casual", "title": "休闲"},
            {"id": "challenge", "title": "挑战"},
        ],
        "tiers": GAME_TIERS,
        "tierLabels": TIER_LABELS,
        "standardTiers": STANDARD_TIER_IDS,
    }
