#!/bin/bash
# Start the new desktop application in Tauri development mode.
set -euo pipefail

# Resolve paths from this file, never from the caller's current directory.
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"
ROOT_DIR="$SCRIPT_DIR"

MODE="${1:-}"
DATA_ROOT=""

case "$MODE" in
  "") ;;
  --data-dir)
    if [ "$#" -ne 2 ] || [ -z "${2:-}" ]; then
      echo "Использование: $0 [--fresh|--legacy|--data-dir PATH|--check]"
      exit 2
    fi
    DATA_ROOT="$2"
    ;;
  --fresh|--legacy|--check)
    if [ "$#" -ne 1 ]; then
      echo "Использование: $0 [--fresh|--legacy|--data-dir PATH|--check]"
      exit 2
    fi
    ;;
  *)
    echo "Использование: $0 [--fresh|--legacy|--data-dir PATH|--check]"
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

if [ "$MODE" != "--check" ] && lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
  PORT_PID="$(lsof -nP -iTCP:5173 -sTCP:LISTEN -t | head -n 1)"
  PORT_COMMAND="$(ps -p "$PORT_PID" -o command= 2>/dev/null || true)"
  echo "Порт 5173 уже занят процессом из другого запуска: ${PORT_COMMAND:-PID $PORT_PID}." >&2
  echo "Остановите старый Tauri/Vite и повторите запуск из $ROOT_DIR." >&2
  exit 1
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Устанавливаются frontend-зависимости..."
  (cd "$ROOT_DIR/frontend" && npm ci)
fi

if [ "$MODE" = "--check" ]; then
  echo "Tauri development prerequisites are ready."
  echo "Rust target: $TARGET"
  exit 0
fi

if [ -z "$DATA_ROOT" ]; then
  case "$MODE" in
    --fresh)
      DATA_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/nfprogress-tauri-dev.XXXXXX")"
      ;;
    --legacy)
      DATA_ROOT="${HOME}/Documents/nfprogress/test_data"
      ;;
    *)
      DATA_ROOT="${NFPROGRESS_DATA_DIR:-${HOME}/Documents/nfprogress/test_data}"
      ;;
  esac
fi

if [ "$MODE" = "" ] || [ "$MODE" = "--legacy" ]; then
  if [ -z "${NFPROGRESS_DATA_DIR:-}" ] || [ "$MODE" = "--legacy" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
      echo "Для обновления canonical test_data нужен Python 3."
      exit 1
    fi
    echo "Обновляется canonical Tauri dev data root через Python migration pipeline..."
    (cd "$ROOT_DIR" && python3 -m backend.app --prepare-dev-data)
  fi
fi

echo "Tauri dev data root: $DATA_ROOT"
echo "Запускается Tauri dev. Это не production-сборка; при первом запуске Cargo может собрать debug-код."
cd "$ROOT_DIR/frontend"
NFPROGRESS_DATA_DIR="$DATA_ROOT" exec npm run tauri:dev
