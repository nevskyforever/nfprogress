import json
import os
import platform
import shutil
import shlex
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

import engine as en


# Замените на адрес JSON-файла на вашем хостинге Spaceweb.
UPDATE_MANIFEST_URL = os.environ.get("NFPROGRESS_UPDATE_URL", "https://nfproject.ru/app/update_manifest.json")

SETTINGS_ORG = "NFProgress"
SETTINGS_APP = "NFProgress"
SKIPPED_VERSION_KEY = "updates/skipped_version"
WINDOWS_UPDATER_ARG = "--nfprogress-updater"


def _debug(message):
    if os.environ.get("NFPROGRESS_UPDATE_DEBUG"):
        print(f"[update_checker] {message}")


def _ssl_context():
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _version_parts(version):
    parts = []
    for part in str(version).split("."):
        number = ""
        for char in part:
            if char.isdigit():
                number += char
            else:
                break
        parts.append(int(number) if number else 0)
    return parts


def _is_newer_version(latest_version, current_version):
    latest = _version_parts(latest_version)
    current = _version_parts(current_version)
    length = max(len(latest), len(current))
    latest.extend([0] * (length - len(latest)))
    current.extend([0] * (length - len(current)))
    return latest > current


def _platform_release_info(manifest):
    system = platform.system()
    if system == "Windows":
        return (
            str(manifest.get("windows_version") or manifest.get("version") or "").strip(),
            _format_download_url(manifest.get("windows_url"), manifest, "windows_version"),
        )
    if system == "Darwin":
        machine = platform.machine().lower()
        if machine in ("arm64", "aarch64"):
            return (
                str(manifest.get("macos_arm_version") or manifest.get("macos_version") or manifest.get("version") or "").strip(),
                _format_download_url(
                manifest.get("macos_arm_url") or manifest.get("macos_url"),
                manifest,
                    "macos_arm_version",
                ),
            )
        return (
            str(manifest.get("macos_intel_version") or manifest.get("macos_version") or manifest.get("version") or "").strip(),
            _format_download_url(
                manifest.get("macos_intel_url") or manifest.get("macos_url"),
                manifest,
                "macos_intel_version",
            ),
        )
    return "", None


def _format_download_url(url, manifest, version_key):
    if not url:
        return None

    version = str(manifest.get(version_key) or manifest.get("version") or "").strip()
    return str(url).replace("{version}", version)


def _is_packaged_app():
    main_module = sys.modules.get("__main__")
    return (
        "__compiled__" in globals()
        or getattr(main_module, "__compiled__", None) is not None
        or bool(getattr(sys, "frozen", False))
    )


def _current_app_target():
    if platform.system() == "Windows":
        if not _is_packaged_app():
            return None

        # Nuitka onefile keeps the original executable path in sys.argv[0].
        # sys.executable can point at the temporary unpacked child process.
        for raw_candidate in (sys.argv[0], sys.executable):
            try:
                candidate = Path(raw_candidate).resolve()
            except OSError:
                continue
            if candidate.suffix.lower() == ".exe" and candidate.exists():
                return candidate
        return None

    if platform.system() == "Darwin":
        executable = Path(sys.executable).resolve()
        candidates = [Path(sys.argv[0]).resolve(), executable]
        for candidate in candidates:
            for parent in (candidate, *candidate.parents):
                if parent.suffix == ".app" and parent.is_dir():
                    return parent
        return None

    return None


def _powershell_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def _shell_literal(value):
    return shlex.quote(str(value))


def _write_text_file(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


def _append_update_log(log_path, message):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} launcher {message}\n")


def _read_update_log_tail(log_path, limit=3000):
    try:
        text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:].strip()


def _windows_creationflags(*names):
    fallback_values = {
        "CREATE_NO_WINDOW": 0x08000000,
        "DETACHED_PROCESS": 0x00000008,
        "CREATE_NEW_PROCESS_GROUP": 0x00000200,
        "CREATE_BREAKAWAY_FROM_JOB": 0x01000000,
    }
    flags = 0
    for name in names:
        flags |= getattr(subprocess, name, fallback_values[name])
    return flags


def _show_windows_message(title, message):
    if platform.system() != "Windows":
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(message), str(title), 0x10)
    except Exception:
        pass


def _wait_for_windows_process_exit(pid, log_path, timeout=180):
    if pid <= 0:
        return

    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000, False, int(pid))
        if handle:
            try:
                _append_update_log(log_path, f"waiting for parent process {pid}")
                kernel32.WaitForSingleObject(handle, int(timeout * 1000))
                return
            finally:
                kernel32.CloseHandle(handle)
    except Exception as error:
        _append_update_log(log_path, f"OpenProcess wait failed: {error}")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["tasklist.exe", "/FI", f"PID eq {int(pid)}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_windows_creationflags("CREATE_NO_WINDOW"),
        )
        if str(pid) not in (result.stdout or ""):
            return
        time.sleep(0.5)


def _copy_extracted_update(replacement_root, new_exe, target_path, log_path):
    target_dir = target_path.parent
    backup_path = target_path.with_name(target_path.name + ".old")
    if backup_path.exists():
        backup_path.unlink()

    if target_path.exists():
        _append_update_log(log_path, f"moving old exe to {backup_path}")
        target_path.replace(backup_path)

    try:
        _append_update_log(log_path, f"copying update from {replacement_root}")
        for source in replacement_root.iterdir():
            destination = target_dir / source.name
            if source.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)

        if not target_path.exists():
            shutil.copy2(new_exe, target_path)
    except Exception:
        if backup_path.exists() and not target_path.exists():
            backup_path.replace(target_path)
        raise

    if backup_path.exists():
        backup_path.unlink()


def _run_windows_updater(download_url, target_path, parent_pid, log_path):
    target_path = Path(target_path)
    log_path = Path(log_path)
    target_dir = target_path.parent
    work_dir = Path(tempfile.mkdtemp(prefix="nfprogress-update-"))
    zip_path = work_dir / "update.zip"
    extract_dir = work_dir / "extract"

    try:
        _append_update_log(log_path, "exe updater started")
        _append_update_log(log_path, f"target={target_path}")
        _wait_for_windows_process_exit(int(parent_pid), log_path)
        time.sleep(0.7)

        _append_update_log(log_path, f"downloading {download_url}")
        request = urllib.request.Request(download_url, headers={"User-Agent": f"NFProgress/{en.version}"})
        with urllib.request.urlopen(request, timeout=60, context=_ssl_context()) as response:
            with open(zip_path, "wb") as output:
                shutil.copyfileobj(response, output)

        _append_update_log(log_path, f"extracting {zip_path}")
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)

        new_exe = next(extract_dir.rglob(target_path.name), None)
        if new_exe is None:
            new_exe = next(extract_dir.rglob("*.exe"), None)
        if new_exe is None:
            raise RuntimeError("В архиве обновления не найден .exe файл.")

        _copy_extracted_update(new_exe.parent, new_exe, target_path, log_path)
        _append_update_log(log_path, "update installed")

        subprocess.Popen(
            [str(target_path)],
            cwd=str(target_dir),
            creationflags=_windows_creationflags(
                "DETACHED_PROCESS",
                "CREATE_NEW_PROCESS_GROUP",
                "CREATE_BREAKAWAY_FROM_JOB",
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        _append_update_log(log_path, "application restarted")
        return 0
    except Exception as error:
        _append_update_log(log_path, f"failed: {error}")
        _show_windows_message(
            "NFProgress",
            f"Не удалось установить обновление.\n\n{error}\n\nПодробности: {log_path}",
        )
        return 1
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def run_windows_updater_from_argv(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if platform.system() != "Windows" or len(argv) < 6 or argv[1] != WINDOWS_UPDATER_ARG:
        return None

    _, _, download_url, target_path, parent_pid, log_path = argv[:6]
    return _run_windows_updater(download_url, target_path, int(parent_pid), log_path)


def _format_process_output(result):
    parts = [f"exit={result.returncode}"]
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if stdout:
        parts.append(f"stdout={stdout}")
    if stderr:
        parts.append(f"stderr={stderr}")
    return "; ".join(parts)


def _wait_for_windows_updater_start(log_path, marker="updater started", timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        log_tail = _read_update_log_tail(log_path)
        if marker in log_tail:
            return True
        time.sleep(0.2)
    return False


def _build_windows_updater_script(download_url, target_path, parent_pid, log_path, task_name=None):
    target_dir = target_path.parent
    target_name = target_path.name
    task_name_literal = _powershell_literal(task_name or "")
    return f"""$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$downloadUrl = {_powershell_literal(download_url)}
$targetPath = {_powershell_literal(target_path)}
$targetDir = {_powershell_literal(target_dir)}
$targetName = {_powershell_literal(target_name)}
$parentPid = {int(parent_pid)}
$logPath = {_powershell_literal(log_path)}
$taskName = {task_name_literal}

function Write-UpdateLog([string]$Message) {{
    Add-Content -Path $logPath -Value ("{{0}} {{1}}" -f (Get-Date -Format o), $Message)
}}

try {{
    Write-UpdateLog "updater started"
    Write-UpdateLog "waiting for application process $parentPid"
    Wait-Process -Id $parentPid -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 700

    $workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("nfprogress-update-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    $zipPath = Join-Path $workDir "update.zip"
    $extractDir = Join-Path $workDir "extract"

    Write-UpdateLog "downloading $downloadUrl"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
    Write-UpdateLog "extracting $zipPath"
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

    $newExe = Get-ChildItem -Path $extractDir -Filter $targetName -Recurse -File | Select-Object -First 1
    if (-not $newExe) {{
        $newExe = Get-ChildItem -Path $extractDir -Filter "*.exe" -Recurse -File | Select-Object -First 1
    }}
    if (-not $newExe) {{
        throw "В архиве обновления не найден .exe файл."
    }}

    $replacementRoot = $newExe.Directory.FullName
    Write-UpdateLog "replacement root $replacementRoot"

    $backupPath = "$targetPath.old"
    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $targetPath) {{
        Move-Item -LiteralPath $targetPath -Destination $backupPath -Force
    }}
    try {{
        Copy-Item -Path (Join-Path $replacementRoot "*") -Destination $targetDir -Recurse -Force
        if (-not (Test-Path -LiteralPath $targetPath)) {{
            Copy-Item -LiteralPath $newExe.FullName -Destination $targetPath -Force
        }}
    }} catch {{
        if (Test-Path -LiteralPath $backupPath) {{
            Move-Item -LiteralPath $backupPath -Destination $targetPath -Force
        }}
        throw
    }}

    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    Write-UpdateLog "updated $targetPath"
    Start-Process -FilePath $targetPath -WorkingDirectory $targetDir
}} catch {{
    Write-UpdateLog ("failed: " + $_.Exception.Message)
    Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue
    [System.Windows.MessageBox]::Show("Не удалось установить обновление.`n`n$($_.Exception.Message)`n`nПодробности: $logPath", "NFProgress") | Out-Null
}} finally {{
    if ($taskName) {{
        schtasks.exe /Delete /TN $taskName /F | Out-Null
    }}
}}
"""


def _windows_powershell_executable():
    system_root = os.environ.get("SystemRoot")
    if system_root:
        powershell = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if powershell.exists():
            return str(powershell)
    return "powershell.exe"


def _start_windows_updater_with_task_scheduler(script_path, task_name, log_path):
    powershell = _windows_powershell_executable()
    task_action = f'"{powershell}" -NoProfile -ExecutionPolicy Bypass -File "{script_path}"'
    start_time = time.strftime("%H:%M", time.localtime(time.time() + 60))
    create_command = [
        "schtasks.exe",
        "/Create",
        "/TN",
        task_name,
        "/TR",
        task_action,
        "/SC",
        "ONCE",
        "/ST",
        start_time,
        "/F",
    ]
    run_command = ["schtasks.exe", "/Run", "/TN", task_name]

    _append_update_log(log_path, f"creating scheduled task {task_name}")
    create_result = subprocess.run(
        create_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_windows_creationflags("CREATE_NO_WINDOW"),
    )
    if create_result.returncode != 0:
        details = _format_process_output(create_result)
        _append_update_log(log_path, f"scheduled task create failed: {details}")
        raise RuntimeError(details)
    _append_update_log(log_path, f"scheduled task create ok: {_format_process_output(create_result)}")

    _append_update_log(log_path, f"running scheduled task {task_name}")
    run_result = subprocess.run(
        run_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_windows_creationflags("CREATE_NO_WINDOW"),
    )
    if run_result.returncode != 0:
        details = _format_process_output(run_result)
        _append_update_log(log_path, f"scheduled task run failed: {details}")
        subprocess.run(
            ["schtasks.exe", "/Delete", "/TN", task_name, "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_windows_creationflags("CREATE_NO_WINDOW"),
        )
        raise RuntimeError(details)
    _append_update_log(log_path, f"scheduled task run ok: {_format_process_output(run_result)}")
    if not _wait_for_windows_updater_start(log_path):
        details = _read_update_log_tail(log_path)
        raise RuntimeError(f"scheduled task started but updater did not write startup marker. Log:\n{details}")


def _start_windows_updater_direct(script_path, log_path):
    command = [
        _windows_powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]
    flags = _windows_creationflags(
        "CREATE_NO_WINDOW",
        "DETACHED_PROCESS",
        "CREATE_NEW_PROCESS_GROUP",
        "CREATE_BREAKAWAY_FROM_JOB",
    )
    _append_update_log(log_path, "starting PowerShell directly with breakaway")
    try:
        process = subprocess.Popen(
            command,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
    except OSError as error:
        _append_update_log(log_path, f"PowerShell breakaway start failed: {error}")
        process = subprocess.Popen(
            command,
            creationflags=_windows_creationflags(
                "CREATE_NO_WINDOW",
                "DETACHED_PROCESS",
                "CREATE_NEW_PROCESS_GROUP",
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
    if not _wait_for_windows_updater_start(log_path):
        log_tail = _read_update_log_tail(log_path)
        return_code = process.poll()
        details = "PowerShell не записал стартовую строку в лог."
        if return_code is not None:
            details += f" Процесс завершился с кодом {return_code}."
        if log_tail:
            details += f"\n\nЛог:\n{log_tail}"
        raise RuntimeError(details)


def _start_windows_exe_updater(download_url, target_path, parent_pid, log_path, wait_for_start=True):
    updater_path = Path(tempfile.gettempdir()) / f"nfprogress-updater-{uuid.uuid4().hex}.exe"
    shutil.copy2(target_path, updater_path)
    _append_update_log(log_path, f"copied updater exe to {updater_path}")

    process = subprocess.Popen(
        [
            str(updater_path),
            WINDOWS_UPDATER_ARG,
            str(download_url),
            str(target_path),
            str(parent_pid),
            str(log_path),
        ],
        cwd=str(target_path.parent),
        creationflags=_windows_creationflags(
            "DETACHED_PROCESS",
            "CREATE_NEW_PROCESS_GROUP",
            "CREATE_BREAKAWAY_FROM_JOB",
        ),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )

    if not wait_for_start:
        return

    if not _wait_for_windows_updater_start(log_path, marker="exe updater started"):
        log_tail = _read_update_log_tail(log_path)
        return_code = process.poll()
        details = "Updater-exe не записал стартовую строку в лог."
        if return_code is not None:
            details += f" Процесс завершился с кодом {return_code}."
        if log_tail:
            details += f"\n\nЛог:\n{log_tail}"
        raise RuntimeError(details)


def _build_macos_updater_script(download_url, target_path, parent_pid, log_path):
    target_dir = target_path.parent
    target_name = target_path.name
    return f"""#!/bin/sh
set -u

DOWNLOAD_URL={_shell_literal(download_url)}
TARGET_PATH={_shell_literal(target_path)}
TARGET_DIR={_shell_literal(target_dir)}
TARGET_NAME={_shell_literal(target_name)}
PARENT_PID={int(parent_pid)}
LOG_PATH={_shell_literal(log_path)}

log() {{
    printf '%s %s\\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" >> "$LOG_PATH"
}}

fail() {{
    log "failed: $1"
    if [ -n "${{MOUNT_POINT:-}}" ]; then
        hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 || true
    fi
    osascript -e 'display alert "NFProgress" message "Не удалось установить обновление. Подробности: '"$LOG_PATH"'"' >/dev/null 2>&1 || true
    exit 1
}}

log "waiting for application process $PARENT_PID"
while kill -0 "$PARENT_PID" >/dev/null 2>&1; do
    sleep 0.5
done
sleep 1

WORK_DIR=$(mktemp -d "${{TMPDIR:-/tmp/}}nfprogress-update.XXXXXX") || fail "Не удалось создать временную папку."
ZIP_PATH="$WORK_DIR/update.zip"
EXTRACT_DIR="$WORK_DIR/extract"
mkdir -p "$EXTRACT_DIR" || fail "Не удалось создать папку распаковки."

log "downloading $DOWNLOAD_URL"
curl -fL --connect-timeout 20 --retry 2 -o "$ZIP_PATH" "$DOWNLOAD_URL" || fail "Не удалось скачать архив обновления."
ditto -x -k "$ZIP_PATH" "$EXTRACT_DIR" || unzip -q "$ZIP_PATH" -d "$EXTRACT_DIR" || fail "Не удалось распаковать zip-архив."

NEW_APP=$(find "$EXTRACT_DIR" -maxdepth 4 -name "$TARGET_NAME" -type d -print -quit)
if [ -z "$NEW_APP" ]; then
    NEW_APP=$(find "$EXTRACT_DIR" -maxdepth 4 -name "*.app" -type d -print -quit)
fi

if [ -z "$NEW_APP" ]; then
    DMG_PATH=$(find "$EXTRACT_DIR" -maxdepth 3 -name "*.dmg" -type f -print -quit)
    if [ -n "$DMG_PATH" ]; then
        MOUNT_OUTPUT=$(hdiutil attach "$DMG_PATH" -nobrowse -readonly 2>>"$LOG_PATH") || fail "Не удалось смонтировать dmg."
        MOUNT_POINT=$(printf '%s\\n' "$MOUNT_OUTPUT" | awk '/\\/Volumes\\// {{print substr($0, index($0, "/Volumes/")); exit}}')
        [ -n "$MOUNT_POINT" ] || fail "Не удалось определить точку монтирования dmg."
        NEW_APP=$(find "$MOUNT_POINT" -maxdepth 2 -name "$TARGET_NAME" -type d -print -quit)
        if [ -z "$NEW_APP" ]; then
            NEW_APP=$(find "$MOUNT_POINT" -maxdepth 2 -name "*.app" -type d -print -quit)
        fi
    fi
fi

[ -n "$NEW_APP" ] || fail "В архиве обновления не найден .app."

BACKUP_PATH="$TARGET_PATH.old"
rm -rf "$BACKUP_PATH"
if [ -d "$TARGET_PATH" ]; then
    mv "$TARGET_PATH" "$BACKUP_PATH" || fail "Не удалось убрать старое приложение."
fi
ditto "$NEW_APP" "$TARGET_PATH" || {{
    rm -rf "$TARGET_PATH"
    if [ -d "$BACKUP_PATH" ]; then
        mv "$BACKUP_PATH" "$TARGET_PATH"
    fi
    fail "Не удалось скопировать новую версию."
}}
rm -rf "$BACKUP_PATH"

if [ -n "${{MOUNT_POINT:-}}" ]; then
    hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 || true
fi
rm -rf "$WORK_DIR"

log "updated $TARGET_PATH"
open "$TARGET_PATH"
"""


def _start_background_update(download_url, parent):
    success, message, severity = _launch_background_update(download_url)
    if success:
        QApplication.quit()
        return True

    if severity == "critical":
        QMessageBox.critical(parent, "Обновление приложения", message)
    else:
        QMessageBox.warning(parent, "Обновление приложения", message)
    return False


def _launch_background_update(download_url):
    target_path = _current_app_target()
    if target_path is None:
        return False, "Автообновление доступно только в собранной версии приложения.", "warning"

    temp_dir = Path(tempfile.gettempdir())
    log_path = temp_dir / "nfprogress-update.log"
    parent_pid = os.getpid()

    if platform.system() == "Windows":
        try:
            log_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
        try:
            _start_windows_exe_updater(download_url, target_path, parent_pid, log_path, wait_for_start=False)
        except Exception as error:
            _debug(f"failed to start Windows exe updater: {error}")
            return (
                False,
                f"Не удалось запустить установщик обновления.\n\n{error}\n\nЛог: {log_path}",
                "critical",
            )
    elif platform.system() == "Darwin":
        try:
            script_path = temp_dir / "nfprogress-update.sh"
            _write_text_file(script_path, _build_macos_updater_script(download_url, target_path, parent_pid, log_path))
            script_path.chmod(0o700)
            subprocess.Popen(
                ["/bin/sh", str(script_path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as error:
            _debug(f"failed to start macOS updater: {error}")
            return (
                False,
                f"Не удалось запустить установщик обновления.\n\n{error}\n\nЛог: {log_path}",
                "critical",
            )
    else:
        return False, "Автообновление для этой операционной системы пока не поддерживается.", "warning"

    return True, "", "success"


class UpdateLaunchWorker(QObject):
    finished = Signal(bool, str, str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    @Slot()
    def run(self):
        success, message, severity = _launch_background_update(self.download_url)
        self.finished.emit(success, message, severity)


class UpdateCheckWorker(QObject):
    finished = Signal(dict)
    failed = Signal()

    def run(self):
        if not UPDATE_MANIFEST_URL:
            _debug("manifest URL is empty")
            self.failed.emit()
            return

        try:
            _debug(f"requesting {UPDATE_MANIFEST_URL}")
            request = urllib.request.Request(
                UPDATE_MANIFEST_URL,
                headers={"User-Agent": f"NFProgress/{en.version}"},
            )
            with urllib.request.urlopen(request, timeout=6, context=_ssl_context()) as response:
                payload = response.read().decode("utf-8")
            manifest = json.loads(payload)
        except Exception as error:
            _debug(f"manifest request failed: {error}")
            self.failed.emit()
            return

        self.finished.emit(manifest)


class UpdateChecker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._dialog_parent = None
        self._launch_thread = None
        self._launch_worker = None
        self._launch_parent = None

    def check_for_updates(self, parent=None):
        if self._thread is not None:
            return

        self._dialog_parent = parent
        self._thread = QThread(self)
        self._worker = UpdateCheckWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._thread.start()

    @Slot(dict)
    def _on_worker_finished(self, manifest):
        parent = self._dialog_parent
        self._cleanup_worker()
        self._handle_manifest(manifest, parent)

    @Slot()
    def _on_worker_failed(self):
        self._cleanup_worker()

    def shutdown(self):
        self._cleanup_worker()
        self._cleanup_launch_worker()

    def _cleanup_worker(self):
        if self._thread is None:
            return

        thread = self._thread
        worker = self._worker
        self._worker = None
        self._thread = None
        self._dialog_parent = None

        worker.deleteLater()
        thread.quit()
        thread.wait()
        thread.deleteLater()

    def _start_update_install(self, download_url, parent):
        if self._launch_thread is not None:
            return

        self._launch_parent = parent
        self._launch_thread = QThread(self)
        self._launch_worker = UpdateLaunchWorker(download_url)
        self._launch_worker.moveToThread(self._launch_thread)

        self._launch_thread.started.connect(self._launch_worker.run)
        self._launch_worker.finished.connect(self._on_update_launch_finished)
        self._launch_thread.start()

    @Slot(bool, str, str)
    def _on_update_launch_finished(self, success, message, severity):
        parent = self._launch_parent
        self._cleanup_launch_worker()

        if success:
            QApplication.quit()
            return

        if severity == "critical":
            QMessageBox.critical(parent, "Обновление приложения", message)
        else:
            QMessageBox.warning(parent, "Обновление приложения", message)

    def _cleanup_launch_worker(self):
        if self._launch_thread is None:
            return

        thread = self._launch_thread
        worker = self._launch_worker
        self._launch_worker = None
        self._launch_thread = None
        self._launch_parent = None

        worker.deleteLater()
        thread.quit()
        thread.wait()
        thread.deleteLater()

    def _handle_manifest(self, manifest, parent):
        latest_version, download_url = _platform_release_info(manifest)
        if not latest_version:
            _debug("manifest has no version for this platform")
            return

        if not _is_newer_version(latest_version, en.version):
            _debug(f"no update: current={en.version}, latest={latest_version}")
            return

        if not download_url:
            _debug("manifest has no download URL for this platform")
            return

        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        skipped_version = settings.value(SKIPPED_VERSION_KEY, "")
        if skipped_version == latest_version:
            _debug(f"version {latest_version} was skipped")
            return

        _debug(f"showing update dialog for {latest_version}: {download_url}")
        self._show_update_dialog(parent, manifest, latest_version, download_url, settings)

    def _show_update_dialog(self, parent, manifest, latest_version, download_url, settings):
        notes = str(manifest.get("notes", "")).strip()
        message = f"Доступна новая версия {latest_version}."
        if notes:
            message += f"\n\n{notes}"
        message += "\n\nПосле нажатия «Обновить» приложение закроется, скачает обновление в фоне и запустится снова."

        dialog = QMessageBox(parent)
        dialog.setWindowTitle("Обновление приложения")
        dialog.setIcon(QMessageBox.Information)
        dialog.setText(message)

        update_button = dialog.addButton("Обновить", QMessageBox.AcceptRole)
        skip_button = dialog.addButton("Пропустить эту версию", QMessageBox.RejectRole)
        dialog.addButton("Позже", QMessageBox.DestructiveRole)

        dialog.exec()
        clicked_button = dialog.clickedButton()

        if clicked_button == update_button:
            self._start_update_install(download_url, parent)
        elif clicked_button == skip_button:
            settings.setValue(SKIPPED_VERSION_KEY, latest_version)
