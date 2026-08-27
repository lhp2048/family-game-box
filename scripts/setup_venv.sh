#!/usr/bin/env bash
# Family Game Box 虚拟环境初始化（macOS / Linux）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

LIB="${ROOT}/deploy/lib/resolve_python.sh"
if [[ ! -f "${LIB}" ]]; then
  echo "ERROR: ${LIB} not found" >&2
  exit 1
fi
# shellcheck source=../deploy/lib/resolve_python.sh
source "${LIB}"

if _venv_needs_recreate "${ROOT}"; then
  if [[ -d "${ROOT}/.venv" ]]; then
    echo "==> Removing old .venv (Python version too low)"
    rm -rf "${ROOT}/.venv"
  fi
fi

cart_setup_venv "${ROOT}" || exit 1

echo ""
echo "Done. Dev: ./scripts/dev.sh   Service: ./service.sh install"
