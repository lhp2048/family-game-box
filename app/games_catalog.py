from __future__ import annotations

from typing import Any, Dict, List

from app.game_registry import list_games as registry_list_games


def list_games() -> List[Dict[str, Any]]:
    return registry_list_games()
