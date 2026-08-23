#!/bin/bash
# Build a local macOS Tauri archive with its matching Python sidecar.
set -euo pipefail

ARCH="${1:-}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
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

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Устанавливаются frontend-зависимости..."
  (cd "$ROOT_DIR/frontend" && npm ci)
fi

run_python "$ROOT_DIR/scripts/sync-tauri-versions.py"
VERSION="$(run_python "$ROOT_DIR/scripts/sync-tauri-versions.py" --version-only)"
DMG_PATH="$BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.dmg"
ARTIFACT_PATH="$BUILD_DIR/$ARTIFACT_PREFIX-$VERSION.zip"
PACKAGE_NAME="$ARTIFACT_PREFIX-$VERSION"

mkdir -p "$BUILD_DIR"
run_python "$ROOT_DIR/scripts/build-backend-sidecar.py" --target "$TARGET"
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

echo "✅ Локальная Tauri-сборка завершена: $ARTIFACT_PATH"
