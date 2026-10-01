#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate Stroop color-word voice clips (mp3) for Android WebView.

Usage:
  .venv/bin/python games/stroop/gen_audio.py

Requires network + edge-tts:
  .venv/bin/pip install edge-tts
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "audio"

# id → 播报字义（与页面「红」→「红色」一致）
COLORS = {
    "red": "红色",
    "yellow": "黄色",
    "blue": "蓝色",
    "green": "绿色",
    "black": "黑色",
    "purple": "紫色",
    "orange": "橙色",
    "white": "白色",
}

VOICE = "zh-CN-XiaoxiaoNeural"


async def synthesize(text: str, dest: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(dest))


async def main_async() -> int:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("缺少 edge-tts，请先执行: .venv/bin/pip install edge-tts", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for name, text in COLORS.items():
        dest = OUT / (name + ".mp3")
        print("→ %s  (%s)" % (dest.name, text))
        await synthesize(text, dest)
        if dest.stat().st_size < 500:
            print("  ERROR: empty/too small", file=sys.stderr)
            return 2
        ok += 1
    print("Done: %d clips in %s" % (ok, OUT))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
