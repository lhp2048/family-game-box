#!/usr/bin/env bash
# Resolve APP_ROOT / LIB_DIR / SCRIPT_DIR for dist (scripts/) vs source (deploy/mac|linux/) layouts.

cart_init_paths() {
  local caller="${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}"
  SCRIPT_DIR="$(cd "$(dirname "${caller}")" && pwd)"
  if [[ -f "${SCRIPT_DIR}/../app/main.py" ]]; then
    APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
  elif [[ -f "${SCRIPT_DIR}/../../app/main.py" ]]; then
    APP_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  else
    echo "ERROR: app/main.py not found near ${SCRIPT_DIR}" >&2
    return 1
  fi
  if [[ -d "${SCRIPT_DIR}/lib" ]]; then
    LIB_DIR="${SCRIPT_DIR}/lib"
  elif [[ -d "${SCRIPT_DIR}/../lib" ]]; then
    LIB_DIR="$(cd "${SCRIPT_DIR}/../lib" && pwd)"
  else
    LIB_DIR=""
  fi
}
