#!/usr/bin/env bash
# Remove build and pack artifacts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT}"

rm -rf dist dist_out release
echo "Cleaned dist/, dist_out/, and release/"
