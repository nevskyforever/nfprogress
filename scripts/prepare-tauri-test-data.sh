#!/bin/bash
# Refresh the canonical Tauri test profile from the current application data.
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Не найден python3, необходимый для подготовки тестовых данных." >&2
  exit 1
fi

LOCK_PARENT="${TMPDIR:-/tmp}"
LOCK_DIR="$LOCK_PARENT/nfprogress-tauri-test-data-refresh.lock"
LOCK_OWNER=0

cleanup_lock() {
  if [ "$LOCK_OWNER" = "1" ]; then
    rm -f -- "$LOCK_DIR/pid"
    rmdir "$LOCK_DIR" 2>/dev/null || true
  fi
}

trap cleanup_lock EXIT
trap 'exit 130' HUP INT TERM

mkdir -p "$LOCK_PARENT"
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
  lock_pid=""
  if [ -f "$LOCK_DIR/pid" ] \
    && read -r lock_pid < "$LOCK_DIR/pid" \
    && [[ "$lock_pid" =~ ^[0-9]+$ ]] \
    && ! kill -0 "$lock_pid" 2>/dev/null; then
    rm -f -- "$LOCK_DIR/pid"
    rmdir "$LOCK_DIR" 2>/dev/null || true
    continue
  fi
  echo "Ожидается завершение обновления общего Tauri test_data..." >&2
  sleep 1
done

LOCK_OWNER=1
printf '%s\n' "$$" > "$LOCK_DIR/pid"

echo "Обновляются реальные данные в canonical Tauri test_data..."
(cd "$ROOT_DIR" && python3 -m backend.app --prepare-dev-data)
