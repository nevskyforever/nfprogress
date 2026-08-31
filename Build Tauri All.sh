#!/bin/bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

"$SCRIPT_DIR/Build Tauri ARM.sh" &
ARM_PID=$!
"$SCRIPT_DIR/Build Tauri Intel.sh" &
INTEL_PID=$!

status=0
wait "$ARM_PID" || status=1
wait "$INTEL_PID" || status=1
exit "$status"
