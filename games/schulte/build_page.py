#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成带统一庆祝/确认 UI 的舒尔特页面。"""

from __future__ import annotations

import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import inject_standalone_overlays

SRC = Path(__file__).parent / "index.html"
WEB = Path(__file__).resolve().parents[2] / "web" / "games" / "schulte" / "index.html"


def main() -> None:
    html = inject_standalone_overlays(SRC.read_text(encoding="utf-8"))
    WEB.parent.mkdir(parents=True, exist_ok=True)
    WEB.write_text(html, encoding="utf-8")
    print("Wrote %s" % WEB)


if __name__ == "__main__":
    main()
