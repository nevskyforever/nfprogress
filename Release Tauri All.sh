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
  local exit_code=0

  while kill -0 "$pid" 2>/dev/null; do
    echo "Ожидание ${label}-релиза: сборка или загрузка ещё выполняется..."
    sleep 30
  done

  wait "$pid" || exit_code=$?
  if [ "$exit_code" -eq 0 ]; then
    echo "✅ ${label}-релиз завершён успешно."
  else
    echo "❌ ${label}-релиз завершился с кодом $exit_code." >&2
  fi
  return "$exit_code"
}

overall_exit_code=0
wait_with_progress "Apple Silicon" "$ARM_PID" || overall_exit_code=1
wait_with_progress "Intel" "$INTEL_PID" || overall_exit_code=1

if [ "$overall_exit_code" -eq 0 ]; then
  echo "✅ Все Tauri-релизы завершены успешно."
fi
exit "$overall_exit_code"
