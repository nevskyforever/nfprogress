#!/bin/bash
# Prepare a local Tauri release archive and upload it for the release CI.
set -euo pipefail

ARCH="${1:-}"
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"
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
SOURCE_REVISION="$(git -C "$ROOT_DIR" rev-parse HEAD)"

if [ -f "$ARTIFACT_PATH" ] \
  && ! python3 "$ROOT_DIR/scripts/verify-tauri-artifact.py" "$ARTIFACT_PATH" "$SOURCE_REVISION"; then
  echo "Существующий Tauri-архив устарел после изменений ветки; выполняется новая сборка."
  "$ROOT_DIR/scripts/build-tauri-local.sh" "$ARCH"
elif [ ! -f "$ARTIFACT_PATH" ]; then
  "$ROOT_DIR/scripts/build-tauri-local.sh" "$ARCH"
fi

python3 "$ROOT_DIR/scripts/verify-tauri-artifact.py" "$ARTIFACT_PATH" "$SOURCE_REVISION"

echo "Локальный Tauri-архив готов: $ARTIFACT_PATH"

MANIFEST_PATH="$ROOT_DIR/update_manifest.json"
MANIFEST_LOCK_DIR="$ROOT_DIR/.release-tauri-manifest.lock"
REMOTE_MANIFEST_PATH="$(mktemp "${TMPDIR:-/tmp}/nfprogress-manifest.XXXXXX")"

while ! mkdir "$MANIFEST_LOCK_DIR" 2>/dev/null; do
  lock_pid=""
  if [ -f "$MANIFEST_LOCK_DIR/pid" ] \
    && read -r lock_pid < "$MANIFEST_LOCK_DIR/pid" \
    && [[ "$lock_pid" =~ ^[0-9]+$ ]] \
    && ! kill -0 "$lock_pid" 2>/dev/null; then
    echo "Удаляется блокировка манифеста от завершившегося релиза (PID $lock_pid)."
    rm -f -- "$MANIFEST_LOCK_DIR/pid"
    rmdir "$MANIFEST_LOCK_DIR" 2>/dev/null || true
    continue
  fi
  echo "Ожидается обновление общего манифеста другим macOS-релизом..."
  sleep 1
done
printf '%s\n' "$$" > "$MANIFEST_LOCK_DIR/pid"

cleanup_release_manifest() {
  rm -f -- "$REMOTE_MANIFEST_PATH"
  rm -f -- "$MANIFEST_LOCK_DIR/pid"
  rmdir "$MANIFEST_LOCK_DIR" 2>/dev/null || true
}
interrupt_release_manifest() {
  cleanup_release_manifest
  exit 130
}
trap cleanup_release_manifest EXIT
trap interrupt_release_manifest HUP INT TERM

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
python3 - "$MANIFEST_PATH" "macos_${ARCH}" <<'PY'
import json
import sys

manifest_path, platform = sys.argv[1:]
manifest = json.load(open(manifest_path, encoding="utf-8"))
release = manifest.get(platform, {})
if not isinstance(release, dict) or not release.get("sha256") or not release.get("size"):
    raise SystemExit(f"В манифесте нет sha256/size для {platform}.")
PY

if [ "${NFPROGRESS_TAURI_RELEASE_UPLOAD:-1}" = "1" ]; then
  REMOTE_NAME="nfprogress-mac-${ARCH}-${VERSION}.zip"
  "$ROOT_DIR/scripts/upload-release.sh" "$ARTIFACT_PATH" "$REMOTE_NAME"
  "$ROOT_DIR/scripts/upload-release.sh" "$MANIFEST_PATH" "update_manifest.json"
  "$ROOT_DIR/scripts/upload-release.sh" "$ROOT_DIR/update_manifest_legacy.json" "update_manifest_legacy.json"
else
  echo "Загрузка на хостинг отключена: NFPROGRESS_TAURI_RELEASE_UPLOAD=0"
fi
