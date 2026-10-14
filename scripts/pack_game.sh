#!/usr/bin/env bash
# Pack a single game into an uploadable zip.
# Usage: ./scripts/pack_game.sh <slug>
#   slug: simon | stroop | maze | … (games/<slug>/ or web/games/<slug>/)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SLUG="${1:-}"
if [[ -z "$SLUG" ]]; then
  echo "Usage: $0 <game-slug>" >&2
  exit 1
fi

if [[ -f "$ROOT/games/$SLUG/generate.py" ]]; then
  echo "==> Generating $SLUG"
  (cd "$ROOT" && python3 "games/$SLUG/generate.py")
fi

OUT_DIR="$ROOT/dist_out/games"
mkdir -p "$OUT_DIR"
STAGE="$ROOT/dist_out/.pack_game_$SLUG"
rm -rf "$STAGE"
mkdir -p "$STAGE"

# Resolve web source directory
SRC=""
if [[ -d "$ROOT/web/games/$SLUG" ]]; then
  SRC="$ROOT/web/games/$SLUG"
elif [[ "$SLUG" == "spot_diff" && -d "$ROOT/web/games/spot-diff" ]]; then
  SRC="$ROOT/web/games/spot-diff"
  SLUG="spot-diff"
elif [[ -d "$ROOT/web/games/spot-diff" && "$SLUG" == "spot-diff" ]]; then
  SRC="$ROOT/web/games/spot-diff"
else
  echo "Cannot find web/games/$SLUG" >&2
  exit 1
fi

cp -R "$SRC/." "$STAGE/"

# game id mapping
GID="$SLUG"
ENTRY="index.html"
TITLE="$SLUG"
SUPPORTS_DAILY=true
case "$SLUG" in
  24points)
    GID="24points"
    ENTRY="play.html"
    TITLE="24 点挑战"
    ;;
  schulte) TITLE="舒尔特挑战" ;;
  stroop) TITLE="Stroop 色字" ;;
  cancel) TITLE="划销训练" ;;
  simon) TITLE="Simon Says" ;;
  spot-diff) TITLE="找不同" ;;
  maze) TITLE="迷宫追踪" ;;
  sudoku) TITLE="数独" ;;
esac

if [[ ! -f "$STAGE/$ENTRY" ]]; then
  echo "Missing entry $ENTRY in $SRC" >&2
  exit 1
fi

python3 - <<PY
import json
from pathlib import Path
stage = Path(r"""$STAGE""")
meta = {
  "id": "$GID",
  "title": "$TITLE",
  "subtitle": "",
  "entry": "$ENTRY",
  "modes": ["casual", "challenge"],
  "tiers": ["intro", "simple", "normal", "hard", "master", "god"],
  "supportsDaily": True,
}
path = stage / "game.json"
path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Wrote", path)
PY

ZIP_PATH="$OUT_DIR/${GID}.zip"
rm -f "$ZIP_PATH"
(
  cd "$STAGE"
  zip -r "$ZIP_PATH" . -x "*.DS_Store" -x "**/.git/**" >/dev/null
)
rm -rf "$STAGE"
echo "Packed: $ZIP_PATH"
ls -la "$ZIP_PATH"
