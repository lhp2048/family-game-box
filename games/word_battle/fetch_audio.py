#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch female English letter-name clips (tim.kahn / Freesound pack 4371).

Pack: https://freesound.org/people/tim.kahn/packs/4371/
Sound IDs 67712–67737 → a.wav … z.wav (CC BY 4.0).

HQ previews are pulled from Freesound CDN (same recordings; no API key required).
Optional: set FREESOUND_API_KEY to download original WAV via API v2 instead.

Usage:
  python3 games/word_battle/fetch_audio.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "audio"

PACK_URL = "https://freesound.org/people/tim.kahn/packs/4371/"
FIRST_SOUND_ID = 67712  # a.wav
USER_AGENT = "family-game-box/1.0 (word-battle; CC-BY tim.kahn alphabet)"

# Trim trailing/leading silence; slightly louder for mobile speakers (still same tim.kahn takes)
FFMPEG_AF = (
    "silenceremove=stop_periods=-1:stop_duration=0.01:stop_threshold=-30dB:"
    "start_periods=1:start_duration=0.01:start_threshold=-30dB,"
    "volume=1.12"
)
MAX_LETTER_SEC = 0.75


def _open(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def preview_hq_url(sound_id: int) -> str:
    folder = str(sound_id)[:2]
    return "https://cdn.freesound.org/previews/%s/%d_7037-hq.mp3" % (folder, sound_id)


def download_preview_mp3(sound_id: int, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = OUT / "_src" / ("%d.mp3" % sound_id)
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(_open(preview_hq_url(sound_id)))
    process_mp3(raw, dest)


def download_wav_api(sound_id: int, dest: Path, token: str) -> None:
    meta_url = "https://freesound.org/apiv2/sounds/%d/?token=%s" % (sound_id, token)
    meta = json.loads(_open(meta_url, timeout=60).decode("utf-8"))
    dl = meta.get("download")
    if not dl:
        raise RuntimeError("no download url for sound %d" % sound_id)
    sep = "&" if "?" in dl else "?"
    wav = OUT / "_src" / ("%d.wav" % sound_id)
    wav.write_bytes(_open("%s%stoken=%s" % (dl, sep, token)))
    process_from_wav(wav, dest)


def _encode_mp3(src: Path, dest: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-af",
            FFMPEG_AF,
            "-codec:a",
            "libmp3lame",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-qscale:a",
            "4",
            str(dest),
        ],
        check=True,
    )


def process_from_wav(src: Path, dest: Path) -> None:
    _encode_mp3(src, dest)


def process_mp3(src: Path, dest: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        shutil.copy2(src, dest)
        return
    _encode_mp3(src, dest)


def clip_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    out = subprocess.check_output(
        [
            ffprobe,
            "-hide_banner",
            "-loglevel",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(out.strip() or "0")


def main() -> int:
    token = os.environ.get("FREESOUND_API_KEY", "").strip()
    letters = "abcdefghijklmnopqrstuvwxyz"
    ok = 0
    for i, letter in enumerate(letters):
        sound_id = FIRST_SOUND_ID + i
        dest = OUT / (letter + ".mp3")
        print("→ %s (Freesound %d)" % (dest.name, sound_id))
        try:
            if token:
                download_wav_api(sound_id, dest, token)
            else:
                download_preview_mp3(sound_id, dest)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            print("  ERROR: %s" % exc, file=sys.stderr)
            return 2
        if dest.stat().st_size < 400:
            print("  ERROR: %s too small" % dest, file=sys.stderr)
            return 2
        dur = clip_duration(dest)
        print("  %.2fs" % dur)
        if dur > MAX_LETTER_SEC:
            print("  WARN: %s longer than %.2fs" % (dest.name, MAX_LETTER_SEC), file=sys.stderr)
        ok += 1
        time.sleep(0.35)
    shutil.rmtree(OUT / "_src", ignore_errors=True)
    print("Done: %d clips in %s" % (ok, OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
