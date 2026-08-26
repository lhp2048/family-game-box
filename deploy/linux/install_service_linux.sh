#!/usr/bin/env bash
# Linux: setup venv + systemd user service
set -euo pipefail

SERVICE_NAME="family-game-box"
_set_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${_set_dir}/lib/paths.sh" ]]; then source "${_set_dir}/lib/paths.sh"; else source "${_set_dir}/../lib/paths.sh"; fi
cart_init_paths || exit 1
RUN_SCRIPT="${SCRIPT_DIR}/run_service.sh"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_FILE="${UNIT_DIR}/${SERVICE_NAME}.service"
[[ -f "${LIB_DIR}/service_common.sh" ]] && source "${LIB_DIR}/service_common.sh"
[[ -f "${LIB_DIR}/resolve_python.sh" ]] && source "${LIB_DIR}/resolve_python.sh"

DO_UNINSTALL=0
DO_STATUS=0
PORT="18029"
BIND="0.0.0.0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --uninstall) DO_UNINSTALL=1; shift ;;
    --status)    DO_STATUS=1; shift ;;
    --port)      PORT="${2:-18029}"; shift 2 ;;
    *) shift ;;
  esac
done

[[ "$(uname -s)" == "Darwin" ]] && { echo "use install_service_mac.sh on macOS" >&2; exit 1; }

if [[ "${DO_STATUS}" -eq 1 ]]; then
  systemctl --user status "${SERVICE_NAME}.service" --no-pager 2>/dev/null || echo "not installed"
  exit 0
fi
if [[ "${DO_UNINSTALL}" -eq 1 ]]; then
  systemctl --user disable --now "${SERVICE_NAME}.service" 2>/dev/null || true
  rm -f "${UNIT_FILE}"
  systemctl --user daemon-reload
  kill_port_listeners "${PORT}" 2>/dev/null || true
  echo "uninstalled ${SERVICE_NAME}"
  exit 0
fi

[[ -f "${APP_ROOT}/app/main.py" ]] || { echo "ERROR: app/main.py not found" >&2; exit 1; }
chmod +x "${RUN_SCRIPT}" "${SCRIPT_DIR}/"*.sh 2>/dev/null || true
cart_setup_venv "${APP_ROOT}" || exit 1
patch_env_port "${APP_ROOT}" "${PORT}" "${APP_ROOT}/.venv/bin/python" || exit 1
ensure_runtime_dirs "${APP_ROOT}"
kill_port_listeners "${PORT}" 2>/dev/null || true
mkdir -p "${UNIT_DIR}"
cat > "${UNIT_FILE}" <<EOF
[Unit]
Description=家庭游戏盒服务
After=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_ROOT}
Environment=PORT=${PORT}
ExecStart=/bin/bash ${RUN_SCRIPT}
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}.service"
sleep 2
wait_for_cart_health "${PORT}" && echo "OK: http://127.0.0.1:${PORT}/" || echo "WARN: health not ready"
echo "Boot without login: loginctl enable-linger \$USER"
