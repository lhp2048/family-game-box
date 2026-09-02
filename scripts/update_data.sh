#!/usr/bin/env bash
# Refresh 24-points source data (output/solutions.txt).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"
fgb_require_python || exit 1

cd "${FGB_ROOT}"
exec "${FGB_PYTHON}" solve_24.py --min 0 --max 24 --out output
