#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ "${1:-}" == "--force" ]] && exec bash "${SCRIPT_DIR}/restart_service_mac.sh" --force
exec bash "${SCRIPT_DIR}/restart_service_mac.sh"
