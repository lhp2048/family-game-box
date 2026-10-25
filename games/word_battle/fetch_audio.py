#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build female English letter-name clips for word-battle.

Source: ChotoTheBright — Freesound sound 700028 (CC0), one continuous A–Z read,
split on silence into 26 clips. Not tim.kahn / pack 4371.

https://freesound.org/people/ChotoTheBright/sounds/700028/

Usage:
  python3 games/word_battle/fetch_audio.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "audio"
SRC = OUT / "_src"

SOUND_ID = 700028
PREVIEW_HQ = "https://cdn.freesound.org/previews/700/%d_13863797-hq.mp3" % SOUND_ID
USER_AGENT = "family-game-box/1.0 (word-battle; CC0 ChotoTheBright alphabet)"

SILENCE_DETECT = "silencedetect=noise=-34dB:d=0.06"
MERGE_GAP_SEC = 0.32
MIN_SPEECH_SEC = 0.12
# Segments are already tight; avoid silenceremove eating very short letters.
CLIP_AF_TAIL = "volume=1.14,alimiter=limit=0.98"
MAX_LETTER_SEC = 0.85


def _open(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_alphabet_track(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_open(PREVIEW_HQ))


def _silence_events(ffmpeg: str, src: Path) -> list[tuple[str, float]]:
    out = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(src),
            "-af",
            SILENCE_DETECT,
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    events: list[tuple[str, float]] = []
    for line in out.splitlines():
        if "silence_start" in line:
            events.append(("s", float(line.split("silence_start:")[1].split()[0])))
        if "silence_end" in line:
            events.append(("e", float(line.split("silence_end:")[1].split()[0])))
    return events


def speech_segments(events: list[tuple[str, float]]) -> list[tuple[float, float]]:
    speech: list[tuple[float, float]] = []
    in_speech = False
    start = 0.0
    for kind, t in events:
        if kind == "e":
            start = t
            in_speech = True
        elif kind == "s" and in_speech:
            speech.append((start, t))
            in_speech = False
    if not speech:
        return []
    merged = [speech[0]]
    for seg in speech[1:]:
        prev = merged[-1]
        if seg[0] - prev[1] < MERGE_GAP_SEC:
            merged[-1] = (prev[0], seg[1])
        else:
            merged.append(seg)
    return [s for s in merged if s[1] - s[0] >= MIN_SPEECH_SEC]


def extract_clip(ffmpeg: str, src: Path, start: float, end: float, dest: Path) -> None:
    pad = 0.03
    ss = max(0.0, start - pad)
    dur = (end - start) + pad * 2
    af = "atrim=start=%.4f:duration=%.4f,asetpts=PTS-STARTPTS,%s" % (ss, dur, CLIP_AF_TAIL)
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
            af,
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


def clip_duration(ffprobe: str, path: Path) -> float:
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
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print("ffmpeg/ffprobe required", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    track = SRC / "alphabet-hq.mp3"
    print("Downloading %s" % PREVIEW_HQ)
    try:
        download_alphabet_track(track)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    events = _silence_events(ffmpeg, track)
    segments = speech_segments(events)
    letters = "abcdefghijklmnopqrstuvwxyz"
    if len(segments) != len(letters):
        print(
            "ERROR: expected %d speech segments, got %d (tune MERGE_GAP_SEC)"
            % (len(letters), len(segments)),
            file=sys.stderr,
        )
        return 2

    ok = 0
    for letter, (start, end) in zip(letters, segments):
        dest = OUT / (letter + ".mp3")
        print("→ %s (%.2f–%.2fs)" % (dest.name, start, end))
        extract_clip(ffmpeg, track, start, end, dest)
        dur = clip_duration(ffprobe, dest)
        print("  %.2fs" % dur)
        if dest.stat().st_size < 400 or dur < 0.08:
            print("  ERROR: %s too small (%.2fs)" % (dest.name, dur), file=sys.stderr)
            return 2
        if dur > MAX_LETTER_SEC:
            print("  WARN: longer than %.2fs" % MAX_LETTER_SEC, file=sys.stderr)
        ok += 1

    shutil.rmtree(SRC, ignore_errors=True)
    print("Done: %d clips in %s (ChotoTheBright CC0)" % (ok, OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
