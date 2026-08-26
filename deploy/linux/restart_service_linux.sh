#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="family-game-box"
PORT="${PORT:-18029}"
DO_FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in --force) DO_FORCE=1; shift ;; --port) PORT="${2:-18029}"; shift 2 ;; *) shift ;; esac
done
if [[ "${DO_FORCE}" -eq 1 ]]; then
  systemctl --user restart "${SERVICE_NAME}.service" 2>/dev/null || bash "$(dirname "$0")/start_service_linux.sh"
else
  systemctl --user restart "${SERVICE_NAME}.service" 2>/dev/null || bash "$(dirname "$0")/install_service_linux.sh" --port "${PORT}"
fi
