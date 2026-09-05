#!/bin/bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

TARGETS=("ARM")
if [ "${1:-}" = "intel" ] || [ "${NFPROGRESS_TAURI_INCLUDE_INTEL:-0}" = "1" ]; then
  TARGETS+=("Intel")
fi

echo "Tauri-релизные цели: ${TARGETS[*]}"
for target in "${TARGETS[@]}"; do
  case "$target" in
    ARM)
      "$SCRIPT_DIR/Release Tauri ARM.sh"
      ;;
    Intel)
      "$SCRIPT_DIR/Release Tauri Intel.sh"
      ;;
  esac
done

echo "✅ Выбранные Tauri-релизы завершены успешно."
