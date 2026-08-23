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
SIDECAR_REBUILD=0
if [ ! -x "$SIDECAR_PATH" ]; then
  SIDECAR_REBUILD=1
else
  SIDECAR_HELP_FILE="$(mktemp "${TMPDIR:-/tmp}/nfprogress-sidecar-help.XXXXXX")"
  if ! "$SIDECAR_PATH" --help >"$SIDECAR_HELP_FILE" 2>&1 \
    || ! grep -q -- '--dev-data' "$SIDECAR_HELP_FILE"; then
    SIDECAR_REBUILD=1
  fi
  rm -f "$SIDECAR_HELP_FILE"
  if [ "$SIDECAR_REBUILD" = "0" ] \
    && find "$ROOT_DIR/backend" "$ROOT_DIR/nfprogress" -type f -name '*.py' \
      -newer "$SIDECAR_PATH" -print -quit | grep -q .; then
    SIDECAR_REBUILD=1
  fi
fi

if [ "$SIDECAR_REBUILD" = "1" ]; then
  if [ "$MODE" = "--check" ]; then
    echo "Не найден актуальный sidecar для $TARGET: $SIDECAR_PATH"
    echo "Обычный запуск соберёт его автоматически."
    exit 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Не найден python3, необходимый для сборки локального sidecar."
    exit 1
  fi
  echo "Sidecar для $TARGET отсутствует или устарел. Собирается локальный Python backend..."
  python3 "$ROOT_DIR/scripts/build-backend-sidecar.py" --target "$TARGET"
  if [ ! -x "$SIDECAR_PATH" ]; then
    echo "Сборка sidecar завершилась без ожидаемого файла: $SIDECAR_PATH"
    exit 1
  fi
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Устанавливаются frontend-зависимости..."
  (cd "$ROOT_DIR/frontend" && npm ci)
fi

if [ "$MODE" = "--check" ]; then
  echo "Tauri development prerequisites are ready."
  echo "Rust target: $TARGET"
  echo "Sidecar: $SIDECAR_PATH"
  echo "Development data: Python-compatible test_data (synchronized at backend startup)"
  exit 0
fi

if lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Порт 5173 уже занят. Остановите отдельный 'npm run dev' перед запуском Tauri."
  exit 1
fi

echo "Запускается Tauri dev. Это не production-сборка; при первом запуске Cargo может собрать debug-код."
echo "Данные тестового запуска: Python-compatible test_data (real stores are copied when newer)"
cd "$ROOT_DIR/frontend"
exec npm run tauri:dev
