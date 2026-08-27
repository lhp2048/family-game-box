#!/usr/bin/env bash
# Pack dist/ into zip + validate manifest + write package-index.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"
fgb_require_python || exit 1

if [[ ! -f "${FGB_DIST}/app/main.py" ]]; then
  echo "ERROR: run ./scripts/build.sh first" >&2
  exit 1
fi

if [[ -z "${FGB_PORTAL_SCRIPTS}" ]]; then
  echo "ERROR: portal scripts not found (family-smart-center-web/scripts)" >&2
  exit 1
fi

"${FGB_PYTHON}" "${FGB_PORTAL_SCRIPTS}/bump_manifest_version.py" \
  --manifest "${FGB_ROOT}/family-product.json" \
  --dist "${FGB_DIST}"

"${FGB_PYTHON}" "${FGB_PORTAL_SCRIPTS}/validate_manifest.py" \
  "${FGB_ROOT}/family-product.json" --dist "${FGB_DIST}"

ZIP_NAME="$("${FGB_PYTHON}" "${FGB_PORTAL_SCRIPTS}/read_manifest_field.py" \
  "${FGB_ROOT}/family-product.json" zipNameHint family_game_box.zip)"
ZIP_FILE="${FGB_OUT_DIR}/${ZIP_NAME}"
mkdir -p "${FGB_OUT_DIR}"
rm -f "${ZIP_FILE}"

"${FGB_PYTHON}" "${FGB_PORTAL_SCRIPTS}/make_zip.py" "${FGB_DIST}" "${ZIP_FILE}"
"${FGB_PYTHON}" "${FGB_PORTAL_SCRIPTS}/write_package_info.py" \
  --manifest "${FGB_ROOT}/family-product.json" \
  --zip "${ZIP_FILE}" \
  --dist "${FGB_DIST}" \
  --out-dir "${FGB_OUT_DIR}"

echo ""
echo "Packed: ${ZIP_FILE}"
