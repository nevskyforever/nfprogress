#!/bin/bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_SOURCE")" && pwd -P)"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Релиз обеих версий macOS должен запускаться на macOS."
  exit 2
fi

open_release_terminal() {
  local launcher_path="$1"
  local terminal_command

  printf -v terminal_command \
    'cd %q && %q %q; status=$?; printf "\\nЗавершено. Нажмите любую клавишу, чтобы закрыть окно…\\n"; read -n 1 -s -r; exit "$status"' \
    "$SCRIPT_DIR" "/bin/bash" "$launcher_path"

  osascript - "$terminal_command" <<'APPLESCRIPT'
on run argv
    set terminalCommand to item 1 of argv
    tell application "Terminal"
        activate
        do script terminalCommand
    end tell
end run
APPLESCRIPT
}

open_release_terminal "$SCRIPT_DIR/Release Tauri ARM.sh"
open_release_terminal "$SCRIPT_DIR/Release Tauri Intel.sh"

echo "ARM- и Intel-релизы запущены в отдельных окнах Terminal."
