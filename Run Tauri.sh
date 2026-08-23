#!/bin/bash
# Start the new desktop application in Tauri development mode.
set -eo pipefail

MODE=""
if [ "$#" -gt 0 ]; then
  MODE="$1"
fi
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "$MODE" in
  ""|--check) ;;
  *)
    echo "Использование: $0 [--check]"
    exit 2
    ;;
esac

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Этот локальный .sh-скрипт предназначен для macOS."
  exit 2
fi
if ! command -v rustc >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Для запуска Tauri нужны Rust/Cargo и Node.js."
  exit 1
fi

TARGET="$(rustc -vV | sed -n 's/^host: //p')"
case "$TARGET" in
  aarch64-apple-darwin|x86_64-apple-darwin) ;;
  *)
    echo "Неподдерживаемый Rust target: $TARGET"
    exit 1
    ;;
esac

SIDECAR_PATH="$ROOT_DIR/frontend/src-tauri/binaries/nfprogress-backend-$TARGET"
if [ ! -x "$SIDECAR_PATH" ]; then
  echo "Не найден sidecar для $TARGET: $SIDECAR_PATH"
  echo "Сначала создайте его из корня репозитория:"
  case "$TARGET" in
    aarch64-apple-darwin) echo "  bash 'Build Tauri ARM.sh'" ;;
    x86_64-apple-darwin) echo "  bash 'Build Tauri Intel.sh'" ;;
  esac
  exit 1
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Устанавливаются frontend-зависимости..."
  (cd "$ROOT_DIR/frontend" && npm ci)
fi

if [ -z "$NFPROGRESS_DATA_DIR" ]; then
  export NFPROGRESS_DATA_DIR="$ROOT_DIR/.nfprogress-dev-data/tauri"
fi
mkdir -p "$NFPROGRESS_DATA_DIR"

if [ "$MODE" = "--check" ]; then
  echo "Tauri development prerequisites are ready."
  echo "Rust target: $TARGET"
  echo "Sidecar: $SIDECAR_PATH"
  echo "Development data: $NFPROGRESS_DATA_DIR"
  exit 0
fi

if lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Порт 5173 уже занят. Остановите отдельный 'npm run dev' перед запуском Tauri."
  exit 1
fi

echo "Запускается Tauri dev. Это не production-сборка; при первом запуске Cargo может собрать debug-код."
echo "Данные тестового запуска: $NFPROGRESS_DATA_DIR"
cd "$ROOT_DIR/frontend"
exec npm run tauri:dev
