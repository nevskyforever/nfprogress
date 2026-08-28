#!/bin/bash
set -euo pipefail
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

# Release builds the archive when it is absent, so it needs the same
# Rosetta-compatible Python environment as the Intel build launcher.
if [ -z "${NFPROGRESS_TAURI_PYTHON:-}" ] \
  && [ -x "$SCRIPT_DIR/.venv-tauri-intel/bin/python" ]; then
  export NFPROGRESS_TAURI_PYTHON="$SCRIPT_DIR/.venv-tauri-intel/bin/python"
  export NFPROGRESS_TAURI_PYTHON_ARCH="${NFPROGRESS_TAURI_PYTHON_ARCH:-x86_64}"
fi

"$SCRIPT_DIR/scripts/release-tauri-local.sh" intel
