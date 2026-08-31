#!/bin/bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

# Both target builds update shared Tauri metadata and frontend/dist.  Run them
# one at a time so neither build can package partially written common files.
"$SCRIPT_DIR/Build Tauri ARM.sh"
"$SCRIPT_DIR/Build Tauri Intel.sh"
