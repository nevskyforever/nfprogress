#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
VERSION=$(python3 -c "import engine; print(engine.version)")
ARTIFACT="$SCRIPT_DIR/build-arm/nfprogress-mac-arm-$VERSION.zip"

if [ -f "$ARTIFACT" ]; then
  echo "Готовая ARM-сборка версии $VERSION уже существует, повторная сборка не требуется."
else
  "$SCRIPT_DIR/Build ARM.sh"
fi

"$SCRIPT_DIR/scripts/upload-release.sh" "$ARTIFACT"
if [ "${NFPROGRESS_SKIP_MANIFEST:-0}" != "1" ]; then
  "$SCRIPT_DIR/scripts/download-release-manifest.sh"
  python3 "$SCRIPT_DIR/scripts/update-release-manifest.py" "$VERSION" macos_arm
  "$SCRIPT_DIR/scripts/upload-release.sh" "$SCRIPT_DIR/update_manifest.json"
  python3 "$SCRIPT_DIR/scripts/create-legacy-manifest.py"
  SSH_UPLOAD_DIR="nfproject/public_html" "$SCRIPT_DIR/scripts/upload-release.sh" \
    "$SCRIPT_DIR/update_manifest_legacy.json" "$SCRIPT_DIR/update_manifest.json"
fi
