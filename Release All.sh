#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
RELEASE_NOTES=$(git -C "$SCRIPT_DIR" log -1 --format=%B | awk '
  /^[[:space:]]*Обновление[[:space:]]+[0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$/ { found = 1; next }
  found && !started && /^[[:space:]]*$/ { next }
  found { started = 1; print }
')
if [ -n "$RELEASE_NOTES" ]; then
  export RELEASE_NOTES
fi

NFPROGRESS_SKIP_MANIFEST=1 "$SCRIPT_DIR/Release ARM.sh" &
ARM_PID=$!
NFPROGRESS_SKIP_MANIFEST=1 "$SCRIPT_DIR/Release Intel.sh" &
INTEL_PID=$!

set +e
wait "$ARM_PID"
ARM_STATUS=$?
wait "$INTEL_PID"
INTEL_STATUS=$?
set -e

if [ "$ARM_STATUS" -ne 0 ] || [ "$INTEL_STATUS" -ne 0 ]; then
  echo "❌ Одна или несколько macOS-сборок завершились с ошибкой."
  exit 1
fi

VERSION=$(python3 -c "import engine; print(engine.version)")
"$SCRIPT_DIR/scripts/download-release-manifest.sh"
python3 "$SCRIPT_DIR/scripts/update-release-manifest.py" "$VERSION" macos_arm
python3 "$SCRIPT_DIR/scripts/update-release-manifest.py" "$VERSION" macos_intel
"$SCRIPT_DIR/scripts/upload-release.sh" "$SCRIPT_DIR/update_manifest.json"
python3 "$SCRIPT_DIR/scripts/create-legacy-manifest.py"
SSH_UPLOAD_DIR="nfproject/public_html" "$SCRIPT_DIR/scripts/upload-release.sh" \
  "$SCRIPT_DIR/update_manifest_legacy.json" "$SCRIPT_DIR/update_manifest.json"
echo "Обе macOS-сборки и публикация завершены!"
