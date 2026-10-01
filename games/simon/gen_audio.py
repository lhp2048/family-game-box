#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate Simon Says voice clips (mp3) for Android WebView fallback.

Usage:
  python3 games/simon/gen_audio.py

Requires network + edge-tts:
  pip install edge-tts
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "audio"

ACTIONS = {
    "hands_up": "举手",
    "hands_down": "放下",
    "turn_left": "向左转",
    "turn_right": "向右转",
    "jump": "跳",
    "squat": "蹲",
}

VOICE = "zh-CN-XiaoxiaoNeural"


def phrases() -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for key, label in ACTIONS.items():
        items.append((key, label))
        items.append(("say_" + key, "老师说" + label))
    return items


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
    for name, text in phrases():
        dest = OUT / (name + ".mp3")
        print("→ %s  (%s)" % (dest.name, text))
        await synthesize(text, dest)
        if dest.stat().st_size < 500:
            print("  ERROR: empty/too small", file=sys.stderr)
            return 2
        ok += 1
    # remove placeholder beep if present
    beep = OUT / "_beep.wav"
    if beep.exists():
        beep.unlink()
    print("Done: %d clips in %s" % (ok, OUT))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
