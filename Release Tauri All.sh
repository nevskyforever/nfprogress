#!/bin/bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

"$SCRIPT_DIR/Release Tauri ARM.sh" &
ARM_PID=$!
"$SCRIPT_DIR/Release Tauri Intel.sh" &
INTEL_PID=$!

echo "Запущены Tauri-релизы: Apple Silicon (PID $ARM_PID) и Intel (PID $INTEL_PID)."

wait_with_progress() {
  local label="$1"
  local pid="$2"
  local status=0

  while kill -0 "$pid" 2>/dev/null; do
    echo "Ожидание ${label}-релиза: сборка или загрузка ещё выполняется..."
    sleep 30
  done

  wait "$pid" || status=$?
  if [ "$status" -eq 0 ]; then
    echo "✅ ${label}-релиз завершён успешно."
  else
    echo "❌ ${label}-релиз завершился с кодом $status." >&2
  fi
  return "$status"
}

status=0
wait_with_progress "Apple Silicon" "$ARM_PID" || status=1
wait_with_progress "Intel" "$INTEL_PID" || status=1

if [ "$status" -eq 0 ]; then
  echo "✅ Все Tauri-релизы завершены успешно."
fi
exit "$status"
