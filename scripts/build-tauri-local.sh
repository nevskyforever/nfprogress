#!/bin/bash
# Build a local macOS Tauri archive with its matching Python sidecar.
set -euo pipefail

ARCH="${1:-}"
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
PYTHON_BIN="${NFPROGRESS_TAURI_PYTHON:-python3}"
PYTHON_ARCH="${NFPROGRESS_TAURI_PYTHON_ARCH:-}"

case "$ARCH" in
  arm)
    TARGET="aarch64-apple-darwin"
    BUILD_DIR="$ROOT_DIR/build-tauri-arm"
    ARTIFACT_PREFIX="nfprogress-tauri-mac-arm"
    EXPECTED_PYTHON_ARCH="arm64"
    ;;
  intel)
    TARGET="x86_64-apple-darwin"
    BUILD_DIR="$ROOT_DIR/build-tauri-intel"
    ARTIFACT_PREFIX="nfprogress-tauri-mac-intel"
    EXPECTED_PYTHON_ARCH="x86_64"
    ;;
  *)
    echo "Использование: $0 arm|intel"
    exit 2
    ;;
esac

WORKSPACE_DIR="$ROOT_DIR/.tauri-build-workspaces/$ARCH"
FRONTEND_SOURCE_DIR="$ROOT_DIR/frontend"
FRONTEND_DIR="$WORKSPACE_DIR/frontend"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Локальная Tauri-сборка macOS должна выполняться на macOS."
  exit 2
fi

run_python() {
  if [ -n "$PYTHON_ARCH" ]; then
    /usr/bin/arch "-$PYTHON_ARCH" "$PYTHON_BIN" "$@"
  else
    "$PYTHON_BIN" "$@"
  fi
}

if ! command -v cargo >/dev/null 2>&1 || ! command -v rustup >/dev/null 2>&1; then
  echo "Не найдены Cargo/Rustup. Установите Rust toolchain для Tauri."
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Не найден npm. Установите Node.js 20.19 или новее."
  exit 1
fi
if ! command -v rsync >/dev/null 2>&1; then
  echo "Не найден rsync. Он нужен для изолированной Tauri-сборки."
  exit 1
fi
if ! run_python -m nuitka --version >/dev/null; then
  echo "Не найдена Nuitka для $PYTHON_BIN. Установите её:"
  echo "  $PYTHON_BIN -m pip install nuitka"
  exit 1
fi

ACTUAL_PYTHON_ARCH="$(run_python -c 'import platform; print(platform.machine())')"
if [ "$ACTUAL_PYTHON_ARCH" != "$EXPECTED_PYTHON_ARCH" ]; then
  echo "Для $ARCH-сборки нужен Python архитектуры $EXPECTED_PYTHON_ARCH, найден $ACTUAL_PYTHON_ARCH."
  if [ "$ARCH" = "intel" ] && [ "$(uname -m)" = "arm64" ]; then
    echo "На Apple Silicon используйте x86_64 virtualenv с backend-зависимостями, например:"
    printf '%s\n' \
      "  NFPROGRESS_TAURI_PYTHON=/path/to/x86_64-venv/bin/python \\" \
      "  NFPROGRESS_TAURI_PYTHON_ARCH=x86_64 bash 'Build Tauri Intel.sh'"
  fi
  exit 1
fi

if ! rustup target list --installed | grep -Fxq "$TARGET"; then
  echo "Не установлен Rust target $TARGET. Выполните:"
  echo "  rustup target add $TARGET"
  exit 1
fi

prepare_frontend_workspace() {
  echo "Подготавливается изолированный frontend-workspace для $ARCH-сборки..."
  mkdir -p "$WORKSPACE_DIR"
  rsync --archive --delete \
    --exclude '.DS_Store' \
    --exclude 'node_modules/' \
    --exclude 'dist/' \
    --exclude '.vite/' \
    --exclude 'coverage/' \
    --exclude 'public/mindmap-assets/' \
    --exclude 'src-tauri/target/' \
    --exclude 'src-tauri/binaries/' \
    "$FRONTEND_SOURCE_DIR/" "$FRONTEND_DIR/"
  rsync --archive --delete \
    "$ROOT_DIR/mindmap_assets/" "$WORKSPACE_DIR/mindmap_assets/"
  cp -p \
    "$ROOT_DIR/Icon-256.png" \
    "$ROOT_DIR/appicon.icns" \
    "$ROOT_DIR/icon.ico" \
    "$WORKSPACE_DIR/"
}

prepare_frontend_workspace
NODE_MODULES_LOCK="$FRONTEND_DIR/node_modules/.package-lock.json"
if [ ! -f "$NODE_MODULES_LOCK" ] \
  || [ "$FRONTEND_DIR/package.json" -nt "$NODE_MODULES_LOCK" ] \
  || [ "$FRONTEND_DIR/package-lock.json" -nt "$NODE_MODULES_LOCK" ]; then
  echo "Устанавливаются или обновляются frontend-зависимости..."
  (cd "$FRONTEND_DIR" && npm ci)
fi

run_python "$ROOT_DIR/scripts/sync-tauri-versions.py" --frontend-dir "$FRONTEND_DIR"
VERSION="$(run_python "$ROOT_DIR/scripts/sync-tauri-versions.py" --version-only)"
DMG_PATH="$BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.dmg"
ARTIFACT_PATH="$BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.zip"
PACKAGE_NAME="$ARTIFACT_PREFIX-$VERSION"

mkdir -p "$BUILD_DIR"
run_python "$ROOT_DIR/scripts/build-backend-sidecar.py" \
  --target "$TARGET" \
  --frontend-dir "$FRONTEND_DIR"
NFPROGRESS_TAURI_FRONTEND_DIR="$FRONTEND_DIR" \
  "$ROOT_DIR/scripts/build-tauri-dmg.sh" "$TARGET" "$DMG_PATH"

STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/nfprogress-tauri-package.XXXXXX")"
trap 'rm -rf -- "$STAGING_DIR"' EXIT
PACKAGE_DIR="$STAGING_DIR/$PACKAGE_NAME"
mkdir -p "$PACKAGE_DIR"
cp "$DMG_PATH" "$PACKAGE_DIR/"
cp "$ROOT_DIR/LICENSE" "$PACKAGE_DIR/LICENSE.txt"
cp "$ROOT_DIR/SOURCE_CODE.txt" "$PACKAGE_DIR/SOURCE_CODE.txt"
SOURCE_REVISION="$(git -C "$ROOT_DIR" rev-parse HEAD)"
{
  printf '\nРевизия сборки: %s\n' "$SOURCE_REVISION"
  printf 'Архив исходного кода: https://github.com/nevskyforever/nfprogress/archive/%s.zip\n' "$SOURCE_REVISION"
} >> "$PACKAGE_DIR/SOURCE_CODE.txt"

rm -f "$ARTIFACT_PATH"
ditto -c -k --norsrc --keepParent "$PACKAGE_DIR" "$ARTIFACT_PATH"

# The ZIP is the local release artifact.  The DMG and older versioned archives
# have already served their purpose and otherwise accumulate with every build.
rm -f -- "$DMG_PATH"
find "$BUILD_DIR" -mindepth 1 -maxdepth 1 -type f \
  -name "$ARTIFACT_PREFIX-*" \
  ! -name "$(basename "$ARTIFACT_PATH")" \
  -delete

# Keep the dependency caches in the isolated workspace, but not the completed
# app bundle and sidecar that are already contained in the release ZIP.
rm -rf -- "$FRONTEND_DIR/src-tauri/target/$TARGET/release/bundle"
rm -f -- "$FRONTEND_DIR/src-tauri/binaries/nfprogress-backend-$TARGET"

echo "✅ Локальная Tauri-сборка завершена: $ARTIFACT_PATH"
