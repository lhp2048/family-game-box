#!/usr/bin/env bash
# Remove games/ build artifacts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

rm -rf dist release
echo "Cleaned dist/ and release/"
