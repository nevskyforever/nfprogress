#!/bin/bash
# Configure the x86_64 Python environment required for Intel macOS Tauri builds.

configure_tauri_intel_python() {
  local root_dir="$1"
  local venv_dir="$root_dir/.venv-tauri-intel"
  local python_bin="$venv_dir/bin/python"
  local requirements_file="$root_dir/requirements-backend.txt"
  local requirements_marker="$venv_dir/.requirements-backend.sha256"
  local bootstrap_python
  local candidate
  local requirements_hash

  if [ -n "${NFPROGRESS_TAURI_PYTHON:-}" ]; then
    return
  fi

  if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
    return
  fi

  for candidate in "${NFPROGRESS_TAURI_BOOTSTRAP_PYTHON:-}" "$(command -v python3)" /usr/local/bin/python3; do
    if [ -n "$candidate" ] \
      && [ -x "$candidate" ] \
      && /usr/bin/arch -x86_64 "$candidate" -c \
        'import platform, sys; raise SystemExit(platform.machine() != "x86_64" or sys.version_info < (3, 11))' \
        >/dev/null 2>&1; then
      bootstrap_python="$candidate"
      break
    fi
  done

  if [ -z "${bootstrap_python:-}" ]; then
    echo "Не найден Python 3.11+ для x86_64 через Rosetta. Установите Rosetta и универсальный Python 3.11+ либо задайте NFPROGRESS_TAURI_BOOTSTRAP_PYTHON." >&2
    return 1
  fi

  if [ -x "$python_bin" ] \
    && ! /usr/bin/arch -x86_64 "$python_bin" -c \
      'import platform, sys; raise SystemExit(platform.machine() != "x86_64" or sys.version_info < (3, 11))' \
      >/dev/null 2>&1; then
    echo "Пересоздаётся несовместимое Python-окружение для Intel Tauri-сборки..."
    rm -rf -- "$venv_dir"
  fi

  if [ ! -x "$python_bin" ]; then
    echo "Создаётся x86_64 Python-окружение для Intel Tauri-сборки..."
    /usr/bin/arch -x86_64 "$bootstrap_python" -m venv "$venv_dir"
  fi

  requirements_hash="$(shasum -a 256 "$requirements_file" | awk '{print $1}')"
  if [ ! -f "$requirements_marker" ] \
    || [ "$(<"$requirements_marker")" != "$requirements_hash" ] \
    || ! /usr/bin/arch -x86_64 "$python_bin" -m nuitka --version >/dev/null 2>&1; then
    echo "Устанавливаются backend-зависимости для Intel Tauri-сборки..."
    /usr/bin/arch -x86_64 "$python_bin" -m pip install --upgrade pip
    /usr/bin/arch -x86_64 "$python_bin" -m pip install -r "$requirements_file" nuitka
    printf '%s\n' "$requirements_hash" > "$requirements_marker"
  fi

  export NFPROGRESS_TAURI_PYTHON="$python_bin"
  export NFPROGRESS_TAURI_PYTHON_ARCH="${NFPROGRESS_TAURI_PYTHON_ARCH:-x86_64}"
}
