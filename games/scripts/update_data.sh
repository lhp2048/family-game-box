#!/usr/bin/env bash
# Refresh 24-points data for games/ standalone tree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
if [[ -x "${ROOT}/../.venv/bin/python" ]]; then
  PYTHON="${ROOT}/../.venv/bin/python"
fi

cd "${ROOT}"
exec "${PYTHON}" solve_24.py --min 0 --max 24 --out output
