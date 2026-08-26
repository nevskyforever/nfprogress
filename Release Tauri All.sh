#!/bin/bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"
"$SCRIPT_DIR/Release Tauri ARM.sh"
"$SCRIPT_DIR/Release Tauri Intel.sh"
