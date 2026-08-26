#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="family-game-box"
PORT="${PORT:-18029}"
systemctl --user stop "${SERVICE_NAME}.service" 2>/dev/null || true
pids="$(lsof -ti tcp:"${PORT}" 2>/dev/null || true)"
[[ -n "${pids}" ]] && kill ${pids} 2>/dev/null || true
echo "stopped ${SERVICE_NAME}"
