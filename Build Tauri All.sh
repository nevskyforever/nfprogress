#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
"$SCRIPT_DIR/Build Tauri ARM.sh"
"$SCRIPT_DIR/Build Tauri Intel.sh"
