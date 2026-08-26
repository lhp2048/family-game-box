#!/usr/bin/env bash
# Linux: 家庭游戏盒 foreground / systemd wrapper
set -euo pipefail

_set_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${_set_dir}/lib/paths.sh" ]]; then
  source "${_set_dir}/lib/paths.sh"
else
  source "${_set_dir}/../lib/paths.sh"
fi
cart_init_paths || exit 1

PYTHON="${APP_ROOT}/.venv/bin/python"
[[ -x "${PYTHON}" ]] || { echo "ERROR: .venv missing, run ./service.sh install" >&2; exit 1; }

export PYTHONUNBUFFERED=1
cd "${APP_ROOT}"
exec "${PYTHON}" -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-18029}"
