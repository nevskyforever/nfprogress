#!/bin/bash
# Prepare an optional Tauri upload without touching the legacy updater manifest.
set -euo pipefail

ARCH="${1:-}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

case "$ARCH" in
  arm)
    BUILD_DIR="$ROOT_DIR/build-tauri-arm"
    ARTIFACT_PREFIX="nfprogress-tauri-mac-arm"
    ARCH_LABEL="ARM"
    ;;
  intel)
    BUILD_DIR="$ROOT_DIR/build-tauri-intel"
    ARTIFACT_PREFIX="nfprogress-tauri-mac-intel"
    ARCH_LABEL="Intel"
    ;;
  *)
    echo "Использование: $0 arm|intel"
    exit 2
    ;;
esac

VERSION="$(python3 -c 'import engine; print(engine.version)')"
ARTIFACT_PATH="$BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.zip"

if [ ! -f "$ARTIFACT_PATH" ]; then
  "$ROOT_DIR/scripts/build-tauri-local.sh" "$ARCH"
fi

echo "Локальный Tauri-архив готов: $ARTIFACT_PATH"
if [ "${NFPROGRESS_TAURI_RELEASE_UPLOAD:-0}" != "1" ]; then
  echo "Публикация не выполнялась: Tauri ещё не является подписанным release-каналом."
  echo "Для явной загрузки без изменения legacy update manifest задайте:"
  echo "  NFPROGRESS_TAURI_RELEASE_UPLOAD=1 bash 'Release Tauri $ARCH_LABEL.sh'"
  exit 0
fi

"$ROOT_DIR/scripts/upload-release.sh" "$ARTIFACT_PATH"
echo "Tauri-архив загружен. Legacy update manifest намеренно не изменён."
