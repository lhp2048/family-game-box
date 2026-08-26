#!/usr/bin/env bash
# macOS: install 家庭游戏盒 as launchd user service
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

if [[ -f "${LIB_DIR}/service_common.sh" ]]; then
  source "${LIB_DIR}/service_common.sh"
fi
if [[ -f "${LIB_DIR}/resolve_python.sh" ]]; then
  source "${LIB_DIR}/resolve_python.sh"
fi

DO_UNINSTALL=0
DO_STATUS=0
PORT="18029"
BIND="0.0.0.0"

launchctl_user_domain() { echo "gui/$(id -u)"; }

launchctl_load() {
  local domain
  domain="$(launchctl_user_domain)"
  if launchctl print "${domain}/${LABEL}" &>/dev/null; then
    launchctl bootout "${domain}" "${PLIST_DEST}" 2>/dev/null || true
  fi
  launchctl bootstrap "${domain}" "${PLIST_DEST}"
  launchctl kickstart -k "${domain}/${LABEL}" 2>/dev/null || true
}

launchctl_unload() {
  launchctl bootout "$(launchctl_user_domain)" "${PLIST_DEST}" 2>/dev/null || true
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --uninstall) DO_UNINSTALL=1; shift ;;
    --status)    DO_STATUS=1; shift ;;
    --port)      PORT="${2:-18029}"; shift 2 ;;
    --bind)      BIND="${2:-0.0.0.0}"; shift 2 ;;
    -h|--help)   exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ "$(uname -s)" == "Darwin" ]] || { echo "macOS only" >&2; exit 1; }

PYTHON="${APP_ROOT}/.venv/bin/python"

if [[ "${DO_STATUS}" -eq 1 ]]; then
  echo "App root: ${APP_ROOT}"
  echo "Plist: ${PLIST_DEST}"
  [[ -f "${PLIST_DEST}" ]] && echo "installed: yes" || echo "installed: no"
  launchctl print "$(launchctl_user_domain)/${LABEL}" 2>/dev/null | sed -n '1,20p' || echo "not loaded"
  [[ -x "${PYTHON}" ]] && "${PYTHON}" --version || echo "venv not ready"
  exit 0
fi

if [[ "${DO_UNINSTALL}" -eq 1 ]]; then
  launchctl_unload
  rm -f "${PLIST_DEST}"
  kill_port_listeners "${PORT}" 2>/dev/null || true
  echo "uninstalled ${LABEL}"
  exit 0
fi

[[ -f "${APP_ROOT}/app/main.py" ]] || { echo "ERROR: app/main.py not found" >&2; exit 1; }

chmod +x "${SCRIPT_DIR}/run_service.sh" "${SCRIPT_DIR}/"*.sh 2>/dev/null || true
cart_setup_venv "${APP_ROOT}" || exit 1
PYTHON="${APP_ROOT}/.venv/bin/python"
patch_env_port "${APP_ROOT}" "${PORT}" "${PYTHON}" || exit 1
ensure_runtime_dirs "${APP_ROOT}"
kill_port_listeners "${PORT}" 2>/dev/null || true

mkdir -p "${LOG_DIR}" "${HOME}/Library/LaunchAgents"
: > "${LOG_DIR}/launchd.out.log"
: > "${LOG_DIR}/launchd.err.log"

cat > "${PLIST_DEST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>${BIND}</string>
        <string>--port</string>
        <string>${PORT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${APP_ROOT}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/launchd.err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
</dict>
</plist>
EOF

echo "==> register launchd ${LABEL}"
launchctl_load

if wait_for_cart_health "${PORT}"; then
  echo "OK: http://127.0.0.1:${PORT}/"
else
  echo "WARN: /api/v1/health not ready — check ${LOG_DIR}/launchd.err.log" >&2
fi
print_access_urls "${PORT}" "${BIND}" 2>/dev/null || true
