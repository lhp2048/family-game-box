#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch single-session English letter-name MP3s for word-battle.

Source: Peter's Useful Crap — letters-only zip (one recording, A–Z split).
https://www.theblog.ca/mp3-audio-files-alphabet

Usage:
  python3 games/word_battle/fetch_audio.py

Requires: network, unzip, ffmpeg on PATH.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "audio"

ZIP_URL = (
    "https://www.theblog.ca/wp-content/uploads/2011/02/"
    "only_letters-transfer_RO-07feb-2eaa0f.zip"
)
USER_AGENT = "family-game-box/1.0 (word-battle letter audio; educational game)"

LETTER_RE = re.compile(r"^([a-z])\s*\(1\)\.mp3$", re.I)


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp:
        dest.write_bytes(resp.read())


def _normalize_mp3(src: Path, dest: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        shutil.copy2(src, dest)
        return
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        zpath = Path(tmpdir) / "letters.zip"
        print("Downloading %s" % ZIP_URL)
        _download(ZIP_URL, zpath)
        extract = Path(tmpdir) / "raw"
        extract.mkdir()
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(extract)
        found: dict[str, Path] = {}
        for path in extract.iterdir():
            if not path.is_file():
                continue
            match = LETTER_RE.match(path.name)
            if match:
                found[match.group(1).lower()] = path
        missing = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in found]
        if missing:
            print("ERROR: missing letters in zip: %s" % ",".join(missing), file=sys.stderr)
            return 2
        ok = 0
        for letter in "abcdefghijklmnopqrstuvwxyz":
            dest = OUT / (letter + ".mp3")
            print("→ %s" % dest.name)
            _normalize_mp3(found[letter], dest)
            if dest.stat().st_size < 400:
                print("  ERROR: %s too small" % dest, file=sys.stderr)
                return 2
            ok += 1
            time.sleep(0.05)
    print("Done: %d clips in %s (single-speaker letters-only pack)" % (ok, OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
