from __future__ import annotations

from typing import Any, Dict, List


def list_games() -> List[Dict[str, Any]]:
    return [
        {
            "id": "24points",
            "title": "24 点挑战",
            "status": "ready",
            "path": "/games/24points/play.html",
            "extra": {"library": "/games/24points/library.html"},
        },
        {
            "id": "schulte",
            "title": "舒尔特挑战",
            "status": "ready",
            "path": "/games/schulte/",
        },
        {
            "id": "stroop",
            "title": "Stroop 色字",
            "status": "ready",
            "path": "/games/stroop/",
        },
        {
            "id": "cancel",
            "title": "划销训练",
            "status": "ready",
            "path": "/games/cancel/",
        },
        {
            "id": "simon",
            "title": "Simon Says",
            "status": "ready",
            "path": "/games/simon/",
        },
        {
            "id": "spot-diff",
            "title": "找不同",
            "status": "ready",
            "path": "/games/spot-diff/",
        },
        {
            "id": "maze",
            "title": "迷宫追踪",
            "status": "ready",
            "path": "/games/maze/",
        },
        {
            "id": "sudoku",
            "title": "数独",
            "status": "ready",
            "path": "/games/sudoku/",
        },
        {
            "id": "24points-library",
            "title": "24 点 · 解法库",
            "status": "ready",
            "path": "/games/24points/library.html",
            "extra": {"kind": "reference"},
        },
    ]
