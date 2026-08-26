#!/usr/bin/env bash
# Service maintenance: install | start | stop | restart | status | uninstall
# Usage: ./service.sh install [--port 18029]
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-18029}"

usage() {
  cat <<'EOF'
Usage: ./service.sh <action> [options]

Actions:
  install    Setup venv + autostart service
  start      Start service
  stop       Stop service
  restart    Restart service (--force)
  status     Show service status
  diagnose   Check bind + health endpoint
  uninstall  Remove autostart + stop

Examples:
  ./service.sh install
  ./service.sh install --port 18029
  ./service.sh restart --force
EOF
}

platform_script() {
  local name="$1"
  if [[ -f "${SELF_DIR}/scripts/${name}" ]]; then
    echo "${SELF_DIR}/scripts/${name}"
  elif [[ -n "${PLATFORM_SUFFIX:-}" && -f "${SELF_DIR}/${PLATFORM_SUFFIX}/${name}" ]]; then
    echo "${SELF_DIR}/${PLATFORM_SUFFIX}/${name}"
  else
    echo "ERROR: ${name} not found under ${SELF_DIR}" >&2
    return 1
  fi
}

lib_dir() {
  if [[ -d "${SELF_DIR}/scripts/lib" ]]; then
    echo "${SELF_DIR}/scripts/lib"
  elif [[ -d "${SELF_DIR}/lib" ]]; then
    echo "${SELF_DIR}/lib"
  fi
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

ACTION="$1"
shift

case "$(uname -s)" in
  Darwin) PLATFORM_SUFFIX=mac ;;
  Linux)  PLATFORM_SUFFIX=linux ;;
  MINGW* | MSYS* | CYGWIN*)
    echo "On Windows use: service.bat ${ACTION}" >&2
    exit 1
    ;;
  *)
    echo "Unsupported OS: $(uname -s)" >&2
    exit 1
    ;;
esac

case "${ACTION}" in
  install)
    exec bash "$(platform_script "install_service_${PLATFORM_SUFFIX}.sh")" "$@"
    ;;
  start)
    exec bash "$(platform_script "start_service_${PLATFORM_SUFFIX}.sh")" "$@"
    ;;
  stop)
    exec bash "$(platform_script "stop_service_${PLATFORM_SUFFIX}.sh")" "$@"
    ;;
  restart)
    exec bash "$(platform_script "restart_service_${PLATFORM_SUFFIX}.sh")" "$@"
    ;;
  status)
    exec bash "$(platform_script "install_service_${PLATFORM_SUFFIX}.sh")" --status "$@"
    ;;
  diagnose)
    LIB="$(lib_dir)"
    if [[ -n "${LIB}" && -f "${LIB}/service_common.sh" ]]; then
      # shellcheck source=lib/service_common.sh
      source "${LIB}/service_common.sh"
    fi
    if [[ -n "${LIB}" && -f "${LIB}/resolve_python.sh" ]]; then
      # shellcheck source=lib/resolve_python.sh
      source "${LIB}/resolve_python.sh"
      APP_ROOT="${SELF_DIR}"
      if [[ -f "${SELF_DIR}/../app/main.py" ]]; then
        APP_ROOT="$(cd "${SELF_DIR}/.." && pwd)"
      fi
      show_cart_python_info "${APP_ROOT}"
    fi
    if declare -F run_diagnose >/dev/null; then
      run_diagnose "${PORT}" "0.0.0.0"
      exit $?
    fi
    echo "service_common.sh not found" >&2
    exit 1
    ;;
  uninstall)
    exec bash "$(platform_script "install_service_${PLATFORM_SUFFIX}.sh")" --uninstall "$@"
    ;;
  -h | --help | help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown action: ${ACTION}" >&2
    usage >&2
    exit 1
    ;;
esac
