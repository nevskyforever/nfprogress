#!/bin/bash
# Prepare a local Tauri release archive and upload it for the release CI.
set -euo pipefail

ARCH="${1:-}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

case "$ARCH" in
  arm)
    BUILD_DIR="$ROOT_DIR/build-tauri-arm"
    ARTIFACT_PREFIX="nfprogress-tauri-mac-arm"
    ;;
  intel)
    BUILD_DIR="$ROOT_DIR/build-tauri-intel"
    ARTIFACT_PREFIX="nfprogress-tauri-mac-intel"
    ;;
  *)
    echo "Использование: $0 arm|intel"
    exit 2
    ;;
esac

python3 "$ROOT_DIR/scripts/sync-tauri-versions.py"
VERSION="$(python3 "$ROOT_DIR/scripts/sync-tauri-versions.py" --version-only)"
ARTIFACT_PATH="$BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.zip"

if [ ! -f "$ARTIFACT_PATH" ]; then
  "$ROOT_DIR/scripts/build-tauri-local.sh" "$ARCH"
fi

echo "Локальный Tauri-архив готов: $ARTIFACT_PATH"

if [ "${NFPROGRESS_TAURI_RELEASE_UPLOAD:-1}" = "1" ]; then
  REMOTE_NAME="nfprogress-mac-${ARCH}-${VERSION}.zip"
  "$ROOT_DIR/scripts/upload-release.sh" "$ARTIFACT_PATH" "$REMOTE_NAME"
else
  echo "Загрузка на хостинг отключена: NFPROGRESS_TAURI_RELEASE_UPLOAD=0"
fi
