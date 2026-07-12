import json
import os
import platform
import shlex
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

import engine as en


# Замените на адрес JSON-файла на вашем хостинге Spaceweb.
UPDATE_MANIFEST_URL = os.environ.get("NFPROGRESS_UPDATE_URL", "https://nfproject.ru/app/update_manifest.json")

SETTINGS_ORG = "NFProgress"
SETTINGS_APP = "NFProgress"
SKIPPED_VERSION_KEY = "updates/skipped_version"


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


def _current_app_target():
    executable = Path(sys.executable).resolve()

    if platform.system() == "Windows":
        if executable.suffix.lower() == ".exe":
            return executable
        return None

    if platform.system() == "Darwin":
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


def _build_windows_updater_script(download_url, target_path, parent_pid, log_path):
    target_dir = target_path.parent
    target_name = target_path.name
    return f"""$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$downloadUrl = {_powershell_literal(download_url)}
$targetPath = {_powershell_literal(target_path)}
$targetDir = {_powershell_literal(target_dir)}
$targetName = {_powershell_literal(target_name)}
$parentPid = {int(parent_pid)}
$logPath = {_powershell_literal(log_path)}

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
}}
"""


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
    target_path = _current_app_target()
    if target_path is None:
        QMessageBox.warning(
            parent,
            "Обновление приложения",
            "Автообновление доступно только в собранной версии приложения.",
        )
        return False

    temp_dir = Path(tempfile.gettempdir())
    log_path = temp_dir / "nfprogress-update.log"
    parent_pid = os.getpid()

    if platform.system() == "Windows":
        script_path = temp_dir / "nfprogress-update.ps1"
        _write_text_file(script_path, _build_windows_updater_script(download_url, target_path, parent_pid, log_path))
        try:
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as error:
            _debug(f"failed to start Windows updater: {error}")
            QMessageBox.critical(
                parent,
                "Обновление приложения",
                f"Не удалось запустить установщик обновления.\n\n{error}",
            )
            return False
    elif platform.system() == "Darwin":
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
    else:
        QMessageBox.warning(
            parent,
            "Обновление приложения",
            "Автообновление для этой операционной системы пока не поддерживается.",
        )
        return False

    QApplication.quit()
    return True


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
            _start_background_update(download_url, parent)
        elif clicked_button == skip_button:
            settings.setValue(SKIPPED_VERSION_KEY, latest_version)
