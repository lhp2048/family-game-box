#!/usr/bin/env bash
# Local dev: venv, build game assets, hot reload (default :18029).
# Usage: ./scripts/dev.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -x "${ROOT}/.venv/bin/python" ]]; then
  echo "[.venv missing] Initializing..."
  "${SCRIPT_DIR}/setup_venv.sh"
fi

"${SCRIPT_DIR}/build.sh"

# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"
fgb_require_python || exit 1

cd "${FGB_ROOT}"
fgb_free_port "${FGB_PORT}"

export PYTHONUNBUFFERED=1

echo ""
echo "Family Game Box [DEV]"
echo "Root: ${FGB_ROOT}"
echo "URL:  http://${FGB_HOST}:${FGB_PORT}/"
echo "Static from source tree web/ (not dist/)"
echo "Press Ctrl+C to stop"
echo ""

fgb_open_url "http://${FGB_HOST}:${FGB_PORT}/"
exec "${FGB_PYTHON}" -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${FGB_PORT}" \
  --reload
