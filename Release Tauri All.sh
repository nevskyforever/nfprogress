#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/Release Tauri ARM.sh"
"$SCRIPT_DIR/Release Tauri Intel.sh"
