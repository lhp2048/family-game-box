#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download U.S. English letter-name clips from Wikimedia Commons (PD-self) → MP3.

Usage:
  python3 games/word_battle/fetch_audio.py

Requires: curl or urllib, ffmpeg on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "audio"

# Commons filenames (Category:U.S. English pronunciation of letters)
COMMONS_FILES: dict[str, str] = {
    "a": "En-us-a.ogg",
    "b": "En-us-b.ogg",
    "c": "En-us-c.ogg",
    "d": "En-us-d.ogg",
    "e": "En-us-e.ogg",
    "f": "En-us-f.ogg",
    "g": "En-us-g.ogg",
    "h": "En-us-h.ogg",
    "i": "En-us-i.ogg",
    "j": "En-us-j.ogg",
    "k": "En-us-k.ogg",
    "l": "En-us-L.ogg",
    "m": "En-us-m.ogg",
    "n": "En-us-n.ogg",
    "o": "En-us-o.ogg",
    "p": "En-us-p.ogg",
    "q": "En-us-q.ogg",
    "r": "En-us-r.ogg",
    "s": "En-us-s.ogg",
    "t": "En-us-t.ogg",
    "u": "En-us-u.ogg",
    "v": "En-us-v.ogg",
    "w": "En-us-w.ogg",
    "x": "En-us-x.ogg",
    "y": "En-us-y.ogg",
    "z": "En-us-z.ogg",
}

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "family-game-box/1.0 (word-battle audio fetch; contact: lhp2048)"


def _open(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def commons_url(filename: str) -> str:
    titles = "File:" + filename
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": titles,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }
    )
    with _open(API + "?" + params, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    if "missing" in page:
        raise RuntimeError("missing file on Commons: %s" % filename)
    return page["imageinfo"][0]["url"].split("?")[0]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _open(url, timeout=120) as resp:
        dest.write_bytes(resp.read())


def to_mp3(src: Path, dest: Path) -> None:
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
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "4",
            str(dest),
        ],
        check=True,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_src"
    tmp.mkdir(exist_ok=True)
    ok = 0
    for letter, filename in COMMONS_FILES.items():
        mp3 = OUT / (letter + ".mp3")
        if mp3.is_file() and mp3.stat().st_size > 400:
            print("skip %s (exists)" % mp3.name)
            ok += 1
            continue
        print("→ %s (%s)" % (mp3.name, filename))
        time.sleep(1.2)
        url = commons_url(filename)
        time.sleep(0.8)
        ogg = tmp / filename
        download(url, ogg)
        to_mp3(ogg, mp3)
        if mp3.stat().st_size < 400:
            print("  ERROR: %s too small" % mp3, file=sys.stderr)
            return 2
        ok += 1
    shutil.rmtree(tmp, ignore_errors=True)
    print("Done: %d clips in %s" % (ok, OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
