#!/usr/bin/env bash
set -euo pipefail

LABEL="com.family.smart.game-box"
PLIST_DEST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
PORT="${PORT:-18029}"

domain="gui/$(id -u)"
if [[ -f "${PLIST_DEST}" ]] && launchctl print "${domain}/${LABEL}" &>/dev/null; then
  launchctl bootout "${domain}" "${PLIST_DEST}" 2>/dev/null || true
  echo "stopped launchd: ${LABEL}"
fi
pids="$(lsof -ti tcp:"${PORT}" 2>/dev/null || true)"
if [[ -n "${pids}" ]]; then
  kill ${pids} 2>/dev/null || true
  echo "stopped port ${PORT}"
fi
