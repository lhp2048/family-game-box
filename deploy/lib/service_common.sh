#!/usr/bin/env bash
# Shared helpers for 家庭游戏盒 install/restart scripts.

CART_HEALTH_PATH="${CART_HEALTH_PATH:-/api/v1/health}"

kill_port_listeners() {
  local port="$1"
  local pids
  pids="$(lsof -ti tcp:"${port}" 2>/dev/null || true)"
  if [[ -z "${pids}" ]]; then
    return 0
  fi
  echo "Stopping existing listeners on port ${port}: ${pids}"
  kill ${pids} 2>/dev/null || true
  sleep 1
  pids="$(lsof -ti tcp:"${port}" 2>/dev/null || true)"
  [[ -n "${pids}" ]] && kill -9 ${pids} 2>/dev/null || true
}

remove_legacy_launchd_labels() {
  local domain="gui/$(id -u)"
  local legacy plist
  for legacy in "$@"; do
    [[ -z "${legacy}" ]] && continue
    plist="${HOME}/Library/LaunchAgents/${legacy}.plist"
    if [[ -f "${plist}" ]]; then
      launchctl bootout "${domain}" "${plist}" 2>/dev/null || true
      rm -f "${plist}"
      echo "==> 已移除旧 launchd 标识: ${legacy}"
    fi
  done
}

show_listen_check() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || echo "No listener on port ${port}"
  else
    echo "lsof not found"
  fi
}

get_primary_lan_ipv4() {
  python3 - <<'PY'
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    ip = sock.getsockname()[0]
    sock.close()
    if not ip.startswith("127."):
        print(ip)
except OSError:
    pass
PY
}

show_launchd_hint() {
  local label="${1:-com.family.smart.game-box}"
  local domain="gui/$(id -u)"
  echo ""
  echo "==> launchd status"
  if launchctl print "${domain}/${label}" &>/dev/null; then
    launchctl print "${domain}/${label}" | sed -n '1,20p'
  else
    echo "Service not loaded. Run: ./service.sh install"
  fi
}

print_access_urls() {
  local port="$1"
  local bind="${2:-0.0.0.0}"
  echo ""
  echo "Access URLs (port ${port}, bind ${bind}):"
  echo "  Local:  http://127.0.0.1:${port}/"
  echo "  Health: http://127.0.0.1:${port}${CART_HEALTH_PATH}"
  local lan_ip
  lan_ip="$(get_primary_lan_ipv4 || true)"
  if [[ -n "${lan_ip}" && "${bind}" == "0.0.0.0" ]]; then
    echo "  LAN:    http://${lan_ip}:${port}/"
  fi
}

run_diagnose() {
  local port="${1:-18029}"
  local bind="${2:-0.0.0.0}"
  print_access_urls "${port}" "${bind}"
  show_listen_check "${port}"
  curl -sf --max-time 3 "http://127.0.0.1:${port}${CART_HEALTH_PATH}" >/dev/null && echo "OK: health" || echo "WARN: health check failed"
}
