#!/usr/bin/env bash
# Production build: generate game assets and assemble dist/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"
fgb_require_python || exit 1

cd "${FGB_ROOT}"

if [[ ! -f "${FGB_ROOT}/output/solutions.txt" ]]; then
  echo "[ERROR] missing output/solutions.txt — run ./scripts/update_data.sh first" >&2
  exit 1
fi

echo "==> Generating game pages"
fgb_generate_games

echo "==> Assembling dist"
rm -rf "${FGB_DIST}"
mkdir -p "${FGB_DIST}/web/games/24points" "${FGB_DIST}/web/games/schulte"
mkdir -p "${FGB_DIST}/app" "${FGB_DIST}/scripts/lib" "${FGB_DIST}/logs"

cp "${FGB_ROOT}/web/index.html" "${FGB_DIST}/web/index.html"
cp "${FGB_ROOT}/web/leaderboard.html" "${FGB_DIST}/web/leaderboard.html"
mkdir -p "${FGB_DIST}/web/js"
cp -R "${FGB_ROOT}/web/js/." "${FGB_DIST}/web/js/"
cp -R "${FGB_ROOT}/web/games/." "${FGB_DIST}/web/games/"

cp -R "${FGB_ROOT}/app/." "${FGB_DIST}/app/"
find "${FGB_DIST}/app" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

cp "${FGB_ROOT}/requirements.txt" "${FGB_DIST}/requirements.txt"
cp "${FGB_ROOT}/family-product.json" "${FGB_DIST}/family-product.json"

if [[ -f "${FGB_ROOT}/deploy/INSTALL.txt" ]]; then
  cp "${FGB_ROOT}/deploy/INSTALL.txt" "${FGB_DIST}/INSTALL.txt"

  for name in service install; do
    [[ -f "${FGB_ROOT}/deploy/${name}.bat" ]] && cp "${FGB_ROOT}/deploy/${name}.bat" "${FGB_DIST}/${name}.bat"
    [[ -f "${FGB_ROOT}/deploy/${name}.sh" ]] && cp "${FGB_ROOT}/deploy/${name}.sh" "${FGB_DIST}/${name}.sh"
  done

  cp "${FGB_ROOT}/deploy/windows/"*.bat "${FGB_DIST}/scripts/" 2>/dev/null || true
  cp "${FGB_ROOT}/deploy/linux/"*.sh "${FGB_DIST}/scripts/"
  cp "${FGB_ROOT}/deploy/mac/"*.sh "${FGB_DIST}/scripts/"
  cp "${FGB_ROOT}/deploy/lib/"*.sh "${FGB_DIST}/scripts/lib/" 2>/dev/null || true

  chmod +x "${FGB_DIST}/scripts/"*.sh "${FGB_DIST}/"*.sh 2>/dev/null || true
  chmod +x "${FGB_DIST}/scripts/lib/"*.sh 2>/dev/null || true

  if [[ -n "${FGB_PORTAL_SCRIPTS}" ]]; then
    "${FGB_PYTHON}" "${FGB_PORTAL_SCRIPTS}/normalize_shell.py" "${FGB_ROOT}/deploy" "${FGB_DIST}"
    "${FGB_PYTHON}" "${FGB_PORTAL_SCRIPTS}/validate_manifest.py" \
      "${FGB_ROOT}/family-product.json" --dist "${FGB_DIST}"
  else
    echo "[WARN] Portal scripts not found — skipped normalize_shell / validate_manifest"
  fi
fi

echo ""
echo "Build OK: ${FGB_DIST}"
echo "  dist/web/index.html"
echo "  dist/web/games/24points/play.html"
echo "  dist/web/games/stroop/index.html"
echo "  dist/app/main.py"
