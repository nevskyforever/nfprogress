#!/bin/bash
set -euo pipefail
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

source "$SCRIPT_DIR/scripts/configure-tauri-intel-python.sh"
configure_tauri_intel_python "$SCRIPT_DIR"

"$SCRIPT_DIR/scripts/build-tauri-local.sh" intel
