#!/usr/bin/env bash
# Deprecated: use family-game-box/scripts/build.sh
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scripts/build.sh" "$@"
