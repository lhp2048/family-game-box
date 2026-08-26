#!/usr/bin/env bash
# Resolve Python >= 3.10 for 家庭游戏盒 venv.

CART_MIN_PYTHON_MAJOR=3
CART_MIN_PYTHON_MINOR=10

CART_PYTHON_CANDIDATES=(
  python3.13 python3.12 python3.11 python3.10
  /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12
  /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10
  /usr/local/bin/python3.13 /usr/local/bin/python3.12
  /usr/local/bin/python3.11 /usr/local/bin/python3.10
)

_python_meets_minimum() {
  local bin="$1"
  "${bin}" -c "import sys; raise SystemExit(0 if sys.version_info >= (${CART_MIN_PYTHON_MAJOR}, ${CART_MIN_PYTHON_MINOR}) else 1)" 2>/dev/null
}

_python_try_select() {
  local bin="$1"
  if [[ -x "${bin}" ]]; then
    :
  elif command -v "${bin}" >/dev/null 2>&1; then
    bin="$(command -v "${bin}")"
  else
    return 1
  fi
  if _python_meets_minimum "${bin}"; then
    RESOLVED_PYTHON="${bin}"
    RESOLVED_PYTHON_VERSION="$("${bin}" --version 2>&1 | head -n 1)"
    return 0
  fi
  return 1
}

resolve_python_bin() {
  local requested="${1:-}"
  RESOLVED_PYTHON=""
  RESOLVED_PYTHON_VERSION=""

  if [[ -n "${requested}" ]]; then
    _python_try_select "${requested}" && return 0
    echo "ERROR: ${requested} not found or Python < ${CART_MIN_PYTHON_MAJOR}.${CART_MIN_PYTHON_MINOR}" >&2
    return 1
  fi
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    _python_try_select "${PYTHON_BIN}" && return 0
    echo "ERROR: PYTHON_BIN=${PYTHON_BIN} is not usable (need >= 3.10)" >&2
    return 1
  fi
  local c
  for c in "${CART_PYTHON_CANDIDATES[@]}"; do
    _python_try_select "${c}" && return 0
  done
  if command -v python3 >/dev/null 2>&1; then
    _python_try_select "$(command -v python3)" && return 0
  fi
  echo "ERROR: Python >= ${CART_MIN_PYTHON_MAJOR}.${CART_MIN_PYTHON_MINOR} required." >&2
  return 1
}

_venv_needs_recreate() {
  local app_root="$1"
  local venv_py="${app_root}/.venv/bin/python"
  [[ ! -x "${venv_py}" ]] && return 0
  ! "${venv_py}" -c "import sys; sys.exit(0 if sys.version_info >= (${CART_MIN_PYTHON_MAJOR}, ${CART_MIN_PYTHON_MINOR}) else 1)" 2>/dev/null
}

cart_setup_venv() {
  local app_root="$1"
  local requested="${2:-}"
  local venv="${app_root}/.venv"
  local venv_py="${venv}/bin/python"

  resolve_python_bin "${requested}" || return 1

  if _venv_needs_recreate "${app_root}"; then
    [[ -d "${venv}" ]] && rm -rf "${venv}"
  fi
  if [[ ! -x "${venv_py}" ]]; then
    echo "==> Creating venv"
    echo "    ${RESOLVED_PYTHON} (${RESOLVED_PYTHON_VERSION})"
    "${RESOLVED_PYTHON}" -m venv "${venv}"
  else
    echo "==> Using existing venv"
    echo "    $("${venv_py}" --version 2>&1 | head -n 1)"
  fi

  echo "==> Installing dependencies"
  "${venv_py}" -m pip install -U pip -q
  "${venv_py}" -m pip install -r "${app_root}/requirements.txt" -q
  (cd "${app_root}" && "${venv_py}" -c "import uvicorn; from app.main import app") || {
    echo "ERROR: dependency install failed" >&2
    return 1
  }
  CART_PYTHON="${venv_py}"
  export CART_PYTHON
  return 0
}

show_cart_python_info() {
  local app_root="$1"
  local venv_py="${app_root}/.venv/bin/python"
  if [[ -x "${venv_py}" ]]; then
    echo "Active venv: ${venv_py} ($("${venv_py}" --version 2>&1 | head -n 1))"
  else
    echo "Active venv: (none)"
  fi
}

ensure_env_file() {
  local app_root="$1"
  if [[ ! -f "${app_root}/.env" && -f "${app_root}/.env.example" ]]; then
    cp "${app_root}/.env.example" "${app_root}/.env"
    echo "==> Created .env from .env.example — 如需环境变量可编辑此文件"
  fi
}

patch_env_port() {
  local app_root="$1"
  local port="$2"
  local py="${3:-${app_root}/.venv/bin/python}"
  [[ -x "${py}" ]] || return 1
  ensure_env_file "${app_root}"
  CART_APP_ROOT="${app_root}" CART_PORT="${port}" "${py}" - <<'PY'
import os
import re
from pathlib import Path

root = Path(os.environ["CART_APP_ROOT"])
port = os.environ["CART_PORT"]
env_path = root / ".env"
text = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
if re.search(r"^\s*PORT\s*=", text, flags=re.MULTILINE):
    text = re.sub(r"^\s*PORT\s*=.*$", f"PORT={port}", text, count=1, flags=re.MULTILINE)
else:
    text = (text.rstrip() + "\n" if text else "") + f"PORT={port}\n"
env_path.write_text(text, encoding="utf-8")
print(f"  .env PORT={port}")
PY
}

ensure_runtime_dirs() {
  local app_root="$1"
  mkdir -p "${app_root}/logs"
}

wait_for_cart_health() {
  local port="$1"
  local i
  for i in $(seq 1 25); do
    if curl -sf --max-time 2 "http://127.0.0.1:${port}/api/v1/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}
