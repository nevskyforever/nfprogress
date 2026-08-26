#!/bin/bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"
"$SCRIPT_DIR/Build Tauri ARM.sh"
"$SCRIPT_DIR/Build Tauri Intel.sh"
