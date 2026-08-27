#!/usr/bin/env bash
# Open 24-points quiz page in browser.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PAGE=""
if [[ -f "${ROOT}/dist/quiz.html" ]]; then
  PAGE="${ROOT}/dist/quiz.html"
elif [[ -f "${ROOT}/output/quiz.html" ]]; then
  PAGE="${ROOT}/output/quiz.html"
else
  echo "[ERROR] quiz.html missing — run scripts/build.sh first" >&2
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "${PAGE}" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${PAGE}" >/dev/null 2>&1 || true
else
  echo "Open: file://${PAGE}"
fi
