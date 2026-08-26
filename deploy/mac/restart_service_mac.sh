#!/usr/bin/env bash
set -euo pipefail

LABEL="com.family.smart.game-box"
_set_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${_set_dir}/lib/paths.sh" ]]; then
  source "${_set_dir}/lib/paths.sh"
else
  source "${_set_dir}/../lib/paths.sh"
fi
cart_init_paths || exit 1
PLIST_DEST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="${APP_ROOT}/logs"
RUN_SCRIPT="${SCRIPT_DIR}/run_service.sh"

[[ -f "${LIB_DIR}/service_common.sh" ]] && source "${LIB_DIR}/service_common.sh"
[[ -f "${LIB_DIR}/resolve_python.sh" ]] && source "${LIB_DIR}/resolve_python.sh"

PORT="18029"
DO_FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) DO_FORCE=1; shift ;;
    --port) PORT="${2:-18029}"; shift 2 ;;
    *) shift ;;
  esac
done

launchctl_user_domain() { echo "gui/$(id -u)"; }

is_port_listening() {
  lsof -ti tcp:"${PORT}" >/dev/null 2>&1
}

restart_launchd() {
  local domain
  domain="$(launchctl_user_domain)"
  [[ ! -f "${PLIST_DEST}" ]] && return 1
  if ! launchctl print "${domain}/${LABEL}" &>/dev/null; then
    launchctl bootstrap "${domain}" "${PLIST_DEST}"
  fi
  launchctl kickstart -k "${domain}/${LABEL}" 2>/dev/null || launchctl bootstrap "${domain}" "${PLIST_DEST}"
  return 0
}

start_background() {
  mkdir -p "${LOG_DIR}"
  chmod +x "${RUN_SCRIPT}" 2>/dev/null || true
  PORT="${PORT}" nohup bash "${RUN_SCRIPT}" >> "${LOG_DIR}/launchd.out.log" 2>> "${LOG_DIR}/launchd.err.log" &
  disown $! 2>/dev/null || true
}

wait_ready() {
  if declare -F wait_for_cart_health >/dev/null; then
    wait_for_cart_health "${PORT}"
    return $?
  fi
  local i
  for i in $(seq 1 25); do
    is_port_listening && return 0
    sleep 1
  done
  return 1
}

[[ -f "${APP_ROOT}/app/main.py" ]] || { echo "ERROR: app/main.py not found" >&2; exit 1; }
[[ "${DO_FORCE}" -eq 0 ]] && is_port_listening && { echo "already running :${PORT}"; exit 0; }

if [[ "${DO_FORCE}" -eq 1 ]]; then
  kill_port_listeners "${PORT}" 2>/dev/null || true
fi

if [[ -f "${PLIST_DEST}" ]]; then
  restart_launchd || true
  sleep 1
fi

if ! is_port_listening; then
  echo "launchd not listening yet, starting run_service.sh in background"
  kill_port_listeners "${PORT}" 2>/dev/null || true
  start_background
fi

if wait_ready; then
  echo "OK: http://127.0.0.1:${PORT}/"
  exit 0
fi

echo "restart failed" >&2
echo "check logs: ${LOG_DIR}/launchd.err.log" >&2
exit 1
