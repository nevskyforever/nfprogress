#!/bin/bash
# Prepare a local Tauri release archive and upload it for the release CI.
set -euo pipefail

ARCH="${1:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

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

MANIFEST_PATH="$ROOT_DIR/update_manifest.json"
REMOTE_MANIFEST_PATH="$(mktemp "${TMPDIR:-/tmp}/nfprogress-manifest.XXXXXX")"
trap 'rm -f -- "$REMOTE_MANIFEST_PATH"' EXIT
if curl --fail --location --retry 3 --silent --show-error \
  --output "$REMOTE_MANIFEST_PATH" \
  "https://nfproject.ru/app/update_manifest.json"; then
  mv "$REMOTE_MANIFEST_PATH" "$MANIFEST_PATH"
else
  echo "Удалённый манифест недоступен; используется локальная копия."
fi

export RELEASE_NOTES="${RELEASE_NOTES:-}"
python3 "$ROOT_DIR/scripts/update-release-manifest.py" "$VERSION" "macos_${ARCH}" "$ARTIFACT_PATH"
python3 "$ROOT_DIR/scripts/create-legacy-manifest.py"

if [ "${NFPROGRESS_TAURI_RELEASE_UPLOAD:-1}" = "1" ]; then
  REMOTE_NAME="nfprogress-mac-${ARCH}-${VERSION}.zip"
  "$ROOT_DIR/scripts/upload-release.sh" "$ARTIFACT_PATH" "$REMOTE_NAME"
  "$ROOT_DIR/scripts/upload-release.sh" "$MANIFEST_PATH" "update_manifest.json"
  "$ROOT_DIR/scripts/upload-release.sh" "$ROOT_DIR/update_manifest_legacy.json" "update_manifest_legacy.json"
else
  echo "Загрузка на хостинг отключена: NFPROGRESS_TAURI_RELEASE_UPLOAD=0"
fi
