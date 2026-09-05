#!/usr/bin/env bash
# Verify the architecture and package boundary of a macOS Tauri app bundle.
set -euo pipefail

APP_PATH="${1:-}"
TARGET="${2:-}"

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 APP_PATH aarch64-apple-darwin|x86_64-apple-darwin" >&2
  exit 2
fi

case "$TARGET" in
  aarch64-apple-darwin) EXPECTED_ARCH="arm64" ;;
  x86_64-apple-darwin) EXPECTED_ARCH="x86_64" ;;
  *)
    echo "Unsupported macOS target: $TARGET" >&2
    exit 2
    ;;
esac

if [ "$(uname -s)" != "Darwin" ]; then
  echo "macOS app verification must run on macOS." >&2
  exit 2
fi
if [ ! -d "$APP_PATH" ] || [ "${APP_PATH##*.}" != "app" ]; then
  echo "Expected a .app bundle: $APP_PATH" >&2
  exit 1
fi

BINARY_PATH="$APP_PATH/Contents/MacOS/nfprogress-desktop"
if [ ! -f "$BINARY_PATH" ]; then
  echo "Tauri executable is missing: $BINARY_PATH" >&2
  exit 1
fi

ARCHES="$(lipo -archs "$BINARY_PATH")"
if [ "$ARCHES" != "$EXPECTED_ARCH" ]; then
  echo "Unexpected Tauri executable architecture: expected $EXPECTED_ARCH, got $ARCHES" >&2
  exit 1
fi

FORBIDDEN_PATHS="$(find "$APP_PATH" -type f \( \
  -iname '*python*' -o \
  -iname '*fastapi*' -o \
  -iname '*nuitka*' -o \
  -iname '*backend*' -o \
  -iname '*sidecar*' -o \
  -iname '*migration-helper*' -o \
  -iname '*.pkl' \
\) -print)"
if [ -n "$FORBIDDEN_PATHS" ]; then
  echo "Tauri app contains forbidden legacy runtime payload:" >&2
  printf '%s\n' "$FORBIDDEN_PATHS" >&2
  exit 1
fi

echo "architecture=$TARGET ($ARCHES)"
echo "tauri_runtime_package_audit=PASS"
echo "app=$APP_PATH"
echo "executable=$BINARY_PATH"
