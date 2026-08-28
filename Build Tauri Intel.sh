#!/bin/bash
set -euo pipefail
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

# On Apple Silicon, use the local Rosetta-compatible environment created for
# the Intel sidecar unless the caller explicitly selected another Python.
if [ -z "${NFPROGRESS_TAURI_PYTHON:-}" ] \
  && [ -x "$SCRIPT_DIR/.venv-tauri-intel/bin/python" ]; then
  export NFPROGRESS_TAURI_PYTHON="$SCRIPT_DIR/.venv-tauri-intel/bin/python"
  export NFPROGRESS_TAURI_PYTHON_ARCH="${NFPROGRESS_TAURI_PYTHON_ARCH:-x86_64}"
fi

"$SCRIPT_DIR/scripts/build-tauri-local.sh" intel
