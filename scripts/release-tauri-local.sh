#!/bin/bash
# Prepare a local Tauri release archive. Publishing belongs to signed CI only.
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

VERSION="$(python3 -c 'import engine; print(engine.version)')"
ARTIFACT_PATH="$BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.zip"

if [ ! -f "$ARTIFACT_PATH" ]; then
  "$ROOT_DIR/scripts/build-tauri-local.sh" "$ARCH"
fi

echo "Локальный Tauri-архив готов: $ARTIFACT_PATH"
echo "Публикация не выполнялась: официальный канал обновлений создаёт и подписывает CI."
