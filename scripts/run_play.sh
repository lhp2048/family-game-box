#!/usr/bin/env bash
# Open 24-points play page in the default browser.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"
fgb_init || exit 1

cd "${FGB_ROOT}"

PAGE=""
for candidate in \
  "${FGB_ROOT}/dist/web/games/24points/play.html" \
  "${FGB_ROOT}/web/games/24points/play.html" \
  "${FGB_ROOT}/output/play.html"; do
  if [[ -f "${candidate}" ]]; then
    PAGE="${candidate}"
    break
  fi
done

if [[ -z "${PAGE}" ]]; then
  echo "[ERROR] play.html missing — run ./scripts/build.sh first" >&2
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "${PAGE}" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${PAGE}" >/dev/null 2>&1 || true
else
  echo "Open: file://${PAGE}"
fi
