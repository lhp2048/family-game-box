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
    "zuyin": "字音",
    "zixing": "字形",
    "chengyu": "成语",
    "ciyu": "词语与虚词",
    "bingju": "病句",
    "biaodian": "标点符号",
    "mingju": "名句默写",
    "changshi": "文学常识",
    "wenyan-base": "文言文基础",
    "gushi": "古诗词鉴赏",
    "yuyan": "语言表达",
    "xiandai": "现代文阅读",
    "zonghe": "综合性学习",
    "xiuci": "修辞手法",
    "wenyan-read": "文言文阅读",
    "xiandai-extra": "现代文补充",
    "gushi-extra": "古诗词补充",
    "yingyong": "应用文",
    "mingzhu": "名著阅读",
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
    "mental-speed": STANDARD_TIER_IDS[:],
    "number-slide": ["intro", "normal", "hard"],
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
    {"id": "mental-speed", "title": "心算快答"},
]


def tier_label(tier: str, fallback: str = "") -> str:
    return TIER_LABELS.get(tier, fallback or tier)


def rank_meta() -> Dict[str, Any]:
    from app.game_registry import list_all_games

    games = [
        {"id": g["id"], "title": g["title"]}
        for g in list_all_games(include_disabled=True)
        if g.get("rankable")
    ]
    tiers: Dict[str, List[str]] = {}
    for g in list_all_games(include_disabled=True):
        if not g.get("rankable"):
            continue
        tiers[g["id"]] = list(g.get("tiers") or STANDARD_TIER_IDS)
    return {
        "games": games,
        "modes": [
            {"id": "casual", "title": "休闲"},
            {"id": "challenge", "title": "挑战"},
        ],
        "tiers": tiers,
        "tierLabels": TIER_LABELS,
        "standardTiers": STANDARD_TIER_IDS,
    }
