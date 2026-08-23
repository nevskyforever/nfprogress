#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/Build Tauri ARM.sh"
"$SCRIPT_DIR/Build Tauri Intel.sh"
