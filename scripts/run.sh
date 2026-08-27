#!/usr/bin/env bash
# Start local server without rebuilding (uses source web/).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"
fgb_require_python || exit 1

cd "${FGB_ROOT}"
fgb_free_port "${FGB_PORT}"

echo "Family Game Box"
echo "Root: ${FGB_ROOT}"
echo "URL:  http://${FGB_HOST}:${FGB_PORT}/"
echo "Press Ctrl+C to stop"
echo ""

fgb_open_url "http://${FGB_HOST}:${FGB_PORT}/"
export PYTHONUNBUFFERED=1
exec "${FGB_PYTHON}" -m uvicorn app.main:app --host 0.0.0.0 --port "${FGB_PORT}"
