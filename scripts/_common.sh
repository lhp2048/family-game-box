#!/usr/bin/env bash
# Shared helpers for family-game-box scripts (macOS / Linux).
set -euo pipefail

fgb_script_dir() {
  cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd
}

fgb_init() {
  FGB_SCRIPT_DIR="$(fgb_script_dir)"
  FGB_ROOT="$(cd "${FGB_SCRIPT_DIR}/.." && pwd)"
  FGB_PORT="${FGB_DEV_PORT:-18029}"
  FGB_HOST="${FGB_DEV_HOST:-127.0.0.1}"
  FGB_DIST="${FGB_ROOT}/dist"
  FGB_OUT_DIR="${FGB_ROOT}/dist_out"

  if [[ -x "${FGB_ROOT}/.venv/bin/python" ]]; then
    FGB_PYTHON="${FGB_ROOT}/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    FGB_PYTHON="$(command -v python3)"
  else
    echo "[ERROR] Python not found. Run ./scripts/setup_venv.sh first." >&2
    return 1
  fi

  FGB_PORTAL_SCRIPTS=""
  for candidate in \
    "${FGB_ROOT}/../family-smart-center-web/scripts" \
    "${FGB_ROOT}/../family_smart_center_web/scripts"; do
    if [[ -d "${candidate}" ]]; then
      FGB_PORTAL_SCRIPTS="${candidate}"
      break
    fi
  done
}

fgb_require_python() {
  fgb_init || return 1
  if [[ ! -x "${FGB_PYTHON}" ]]; then
    echo "[ERROR] Python not found at ${FGB_PYTHON}" >&2
    return 1
  fi
}

fgb_free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    echo "Stopping process(es) on port ${port}: ${pids}"
    kill ${pids} 2>/dev/null || true
  fi
}

fgb_open_url() {
  local url="$1"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open "${url}" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${url}" >/dev/null 2>&1 || true
  else
    echo "Open in browser: ${url}"
  fi
}

fgb_generate_games() {
  fgb_require_python || return 1
  cd "${FGB_ROOT}"

  "${FGB_PYTHON}" games/24points/generate_library.py
  "${FGB_PYTHON}" games/24points/generate_play.py

  local game
  for game in stroop cancel simon spot_diff maze sudoku; do
    "${FGB_PYTHON}" "games/${game}/generate.py"
  done

  mkdir -p web/games/schulte
  "${FGB_PYTHON}" games/schulte/build_page.py
}
