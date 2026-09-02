#!/usr/bin/env bash
# Open games standalone index in browser.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PAGE=""
if [[ -f "${ROOT}/dist/index.html" ]]; then
  PAGE="${ROOT}/dist/index.html"
elif [[ -f "${ROOT}/output/index.html" ]]; then
  PAGE="${ROOT}/output/index.html"
else
  echo "[ERROR] no dist/index.html — run scripts/build.sh first" >&2
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "${PAGE}" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${PAGE}" >/dev/null 2>&1 || true
else
  echo "Open: file://${PAGE}"
fi
