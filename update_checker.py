import hashlib
import json
import logging
import os
import platform
import shlex
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

import engine as en


UPDATE_MANIFEST_URL = os.environ.get("NFPROGRESS_UPDATE_URL", "https://nfproject.ru/app/update_manifest.json")
SETTINGS_ORG = "NFProgress"
SETTINGS_APP = "NFProgress"
SKIPPED_VERSION_KEY = "updates/skipped_version"
UPDATE_ARCHIVE_NAME = "nfprogress-update.zip"
UPDATER_EXECUTABLE = "nfprogress-updater.exe"
UPDATER_RUNTIME_DIR = "updater-runtime"
MAX_DOWNLOAD_SIZE = 1024 * 1024 * 1024


def _update_data_dir() -> Path:
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base_dir = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base_dir / "nfprogress"
    return Path(tempfile.gettempdir()) / "nfprogress"


def _update_log_path() -> Path:
    return _update_data_dir() / "logs" / "update.log"


def _logger() -> logging.Logger:
    logger = logging.getLogger("nfprogress.update_checker")
    if logger.handlers:
        return logger
    log_path = _update_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def _debug(message: str) -> None:
    _logger().info(message)
    if os.environ.get("NFPROGRESS_UPDATE_DEBUG"):
        print(f"[update_checker] {message}")


def _ssl_context():
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _uncached_manifest_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("_", str(int(time.time()))))
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))


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


def _format_download_url(url, version):
    if not url:
        return None
    return str(url).replace("{version}", str(version))


def _platform_release_info(manifest: dict) -> dict:
    system = platform.system()
    common_version = str(manifest.get("version") or "").strip()
    if system == "Windows":
        windows = manifest.get("windows")
        if isinstance(windows, dict):
            version = str(windows.get("version") or common_version).strip()
            return {
                "version": version,
                "url": _format_download_url(windows.get("url"), version),
                "sha256": str(windows.get("sha256") or "").strip().lower(),
                "size": windows.get("size"),
                "entry_point": str(windows.get("entry_point") or "").strip(),
                "secure_manifest": True,
            }

        version = str(manifest.get("windows_version") or common_version).strip()
        return {
            "version": version,
            "url": _format_download_url(manifest.get("windows_url"), version),
            "sha256": "",
            "size": None,
            "entry_point": "",
            "secure_manifest": False,
        }

    if system == "Darwin":
        machine = platform.machine().lower()
        if machine in ("arm64", "aarch64"):
            key = "macos_arm"
            legacy_version_key = "macos_arm_version"
            legacy_url_key = "macos_arm_url"
        else:
            key = "macos_intel"
            legacy_version_key = "macos_intel_version"
            legacy_url_key = "macos_intel_url"
        section = manifest.get(key)
        if isinstance(section, dict):
            version = str(section.get("version") or common_version).strip()
            url = section.get("url")
        else:
            version = str(manifest.get(legacy_version_key) or common_version).strip()
            url = manifest.get(legacy_url_key)
        return {"version": version, "url": _format_download_url(url, version)}
    return {"version": "", "url": None}


def _validate_windows_release(release: dict) -> None:
    missing = []
    for key in ("version", "url", "sha256", "size", "entry_point"):
        if release.get(key) in (None, ""):
            missing.append(key)
    if missing:
        raise ValueError(f"В манифесте отсутствуют обязательные поля Windows: {', '.join(missing)}.")
    sha256 = str(release["sha256"]).lower()
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        raise ValueError("Поле windows.sha256 должно содержать полный SHA-256.")
    try:
        size = int(release["size"])
    except (TypeError, ValueError) as error:
        raise ValueError("Поле windows.size должно быть целым числом.") from error
    if size <= 0 or size > MAX_DOWNLOAD_SIZE:
        raise ValueError(f"Размер Windows-архива вне допустимого диапазона: {size} байт.")
    if str(release["entry_point"]).replace("\\", "/") != "nfprogress/nfprogress.exe":
        raise ValueError("Поле windows.entry_point должно быть равно nfprogress/nfprogress.exe.")
    parsed_url = urllib.parse.urlsplit(str(release["url"]))
    if parsed_url.scheme.lower() != "https" or not parsed_url.netloc:
        raise ValueError("Поле windows.url должно содержать абсолютный HTTPS-адрес.")
    release["size"] = size


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
        for candidate in (Path(sys.argv[0]).resolve(), executable):
            for parent in (candidate, *candidate.parents):
                if parent.suffix == ".app" and parent.is_dir():
                    return parent
    return None


def _windows_programs_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base_dir = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base_dir / "Programs" / "nfprogress"


def _resource_roots(current_executable: Path) -> list[Path]:
    roots = [current_executable.parent, Path(__file__).resolve().parent]
    unique = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _find_updater_runtime(current_executable: Path) -> Path:
    for root in _resource_roots(current_executable):
        runtime = root / UPDATER_RUNTIME_DIR
        if (runtime / UPDATER_EXECUTABLE).is_file():
            return runtime
    raise FileNotFoundError(f"Не найден постоянный {UPDATER_RUNTIME_DIR}/{UPDATER_EXECUTABLE}.")


def _is_standalone_install(current_executable: Path) -> bool:
    try:
        _find_updater_runtime(current_executable)
    except FileNotFoundError:
        return False
    try:
        return current_executable.parent.resolve() == _windows_programs_dir().resolve()
    except OSError:
        return False


def _prepare_permanent_updater(current_executable: Path) -> Path:
    source_dir = _find_updater_runtime(current_executable)
    updater_dir = _update_data_dir() / "updater"
    staging_dir = _update_data_dir() / "updater.new"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, staging_dir)
    if updater_dir.exists():
        shutil.rmtree(updater_dir)
    staging_dir.replace(updater_dir)
    updater_path = updater_dir / UPDATER_EXECUTABLE
    if not updater_path.is_file():
        raise FileNotFoundError(f"Не удалось подготовить {updater_path}.")
    return updater_path


def _download_update_archive(release: dict, progress_callback=None) -> Path:
    _validate_windows_release(release)
    archive_path = _update_data_dir() / "updates" / UPDATE_ARCHIVE_NAME
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.unlink(missing_ok=True)
    expected_size = int(release["size"])
    digest = hashlib.sha256()
    downloaded = 0
    request = urllib.request.Request(
        release["url"],
        headers={"User-Agent": f"NFProgress/{en.version}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30, context=_ssl_context()) as response:
            status = response.getcode()
            if status is not None and not 200 <= status < 300:
                raise RuntimeError(f"Сервер вернул HTTP {status}.")
            content_length = response.headers.get("Content-Length")
            if content_length:
                announced_size = int(content_length)
                if announced_size > MAX_DOWNLOAD_SIZE or announced_size > expected_size:
                    raise RuntimeError("Сервер объявил размер файла больше разрешённого манифестом.")

            with archive_path.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > expected_size or downloaded > MAX_DOWNLOAD_SIZE:
                        raise RuntimeError("Загрузка превышает допустимый размер.")
                    output.write(chunk)
                    digest.update(chunk)
                    if progress_callback:
                        progress_callback(downloaded, expected_size)
                output.flush()
                os.fsync(output.fileno())

        if downloaded != expected_size:
            raise RuntimeError(
                f"Размер скачанного файла не совпадает: ожидалось {expected_size}, получено {downloaded}."
            )
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != release["sha256"]:
            raise RuntimeError(
                f"SHA-256 скачанного архива не совпадает: ожидался {release['sha256']}, "
                f"получен {actual_sha256}."
            )
        _debug(f"Архив обновления проверен: {archive_path}, {downloaded} байт")
        return archive_path
    except Exception:
        archive_path.unlink(missing_ok=True)
        _logger().exception("Ошибка загрузки обновления")
        raise


def _launch_windows_updater(release: dict, archive_path: Path) -> tuple[bool, str]:
    current_executable = _current_app_target()
    if current_executable is None:
        raise RuntimeError("Автообновление доступно только в собранной версии приложения.")
    updater_path = _prepare_permanent_updater(current_executable)
    migrating = not _is_standalone_install(current_executable)
    app_dir = _windows_programs_dir() if migrating else current_executable.parent
    app_dir.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(updater_path),
        "--app-dir", str(app_dir),
        "--archive", str(archive_path),
        "--sha256", str(release["sha256"]),
        "--pid", str(os.getpid()),
        "--current-version", str(en.version),
        "--new-version", str(release["version"]),
    ]
    if migrating:
        command.extend(["--legacy-executable", str(current_executable)])
        command.append("--create-shortcut")
    subprocess.Popen(command, cwd=str(updater_path.parent))
    _debug(f"Запущен постоянный updater: {updater_path}; app_dir={app_dir}")
    return migrating, str(app_dir)


def _shell_literal(value):
    return shlex.quote(str(value))


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


def _launch_macos_update(download_url):
    target_path = _current_app_target()
    if target_path is None:
        raise RuntimeError("Автообновление доступно только в собранной версии приложения.")
    update_dir = _update_data_dir()
    update_dir.mkdir(parents=True, exist_ok=True)
    script_path = update_dir / "nfprogress-update.sh"
    log_path = _update_log_path()
    script_path.write_text(
        _build_macos_updater_script(download_url, target_path, os.getpid(), log_path),
        encoding="utf-8",
        newline="\n",
    )
    script_path.chmod(0o700)
    subprocess.Popen(
        ["/bin/sh", str(script_path)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


class UpdateDownloadWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, release):
        super().__init__()
        self.release = release

    @Slot()
    def run(self):
        try:
            archive_path = _download_update_archive(self.release, self.progress.emit)
        except urllib.error.HTTPError as error:
            self.failed.emit(f"Сервер вернул HTTP {error.code} при загрузке обновления.")
        except urllib.error.URLError as error:
            self.failed.emit(f"Не удалось подключиться к серверу обновлений: {error.reason}")
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.finished.emit(str(archive_path))


class UpdateCheckWorker(QObject):
    finished = Signal(dict)
    failed = Signal()

    @Slot()
    def run(self):
        if not UPDATE_MANIFEST_URL:
            self.failed.emit()
            return
        try:
            request = urllib.request.Request(
                _uncached_manifest_url(UPDATE_MANIFEST_URL),
                headers={
                    "User-Agent": f"NFProgress/{en.version}",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            with urllib.request.urlopen(request, timeout=10, context=_ssl_context()) as response:
                status = response.getcode()
                if status is not None and not 200 <= status < 300:
                    raise RuntimeError(f"HTTP {status}")
                payload = response.read(1024 * 1024 + 1)
            if len(payload) > 1024 * 1024:
                raise ValueError("Манифест слишком большой.")
            manifest = json.loads(payload.decode("utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("Корень манифеста должен быть объектом.")
        except Exception:
            _logger().exception("Не удалось получить манифест обновления")
            self.failed.emit()
            return
        self.finished.emit(manifest)


class UpdateChecker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._dialog_parent = None
        self._download_thread = None
        self._download_worker = None
        self._download_release = None
        self._progress_dialog = None

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
        self._cleanup_check_worker()
        self._handle_manifest(manifest, parent)

    @Slot()
    def _on_worker_failed(self):
        self._cleanup_check_worker()

    def _cleanup_check_worker(self):
        if self._thread is None:
            return
        thread, worker = self._thread, self._worker
        self._thread = self._worker = self._dialog_parent = None
        worker.deleteLater()
        thread.quit()
        thread.wait()
        thread.deleteLater()

    def shutdown(self):
        self._cleanup_check_worker()
        self._cleanup_download_worker()

    def _handle_manifest(self, manifest, parent):
        release = _platform_release_info(manifest)
        latest_version = release.get("version")
        current_target = _current_app_target()
        migration_needed = (
            platform.system() == "Windows"
            and current_target is not None
            and not _is_standalone_install(current_target)
        )
        if not latest_version or (
            not _is_newer_version(latest_version, en.version) and not migration_needed
        ):
            return
        if not release.get("url"):
            _debug("В манифесте отсутствует URL обновления для текущей платформы")
            return

        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        if settings.value(SKIPPED_VERSION_KEY, "") == latest_version and not migration_needed:
            return

        if platform.system() == "Windows":
            try:
                _validate_windows_release(release)
            except ValueError as error:
                QMessageBox.warning(
                    parent,
                    "Обновление приложения",
                    f"Автоматическое обновление отменено.\n\n{error}\n\n"
                    "Архив без корректного SHA-256 устанавливаться не будет.",
                )
                return
        self._show_update_dialog(parent, manifest, release, settings)

    def _show_update_dialog(self, parent, manifest, release, settings):
        latest_version = release["version"]
        notes = str(manifest.get("notes", "")).strip()
        message = f"Доступна новая версия {latest_version}."
        if notes:
            message += f"\n\n{notes}"
        if platform.system() == "Windows" and (_current_app_target() is not None):
            if not _is_standalone_install(_current_app_target()):
                message += (
                    "\n\nФормат установки изменился. Новая версия будет установлена в "
                    f"{_windows_programs_dir()}. Старый EXE автоматически удаляться не будет."
                )
        message += "\n\nАрхив будет скачан и проверен перед закрытием приложения."

        dialog = QMessageBox(parent)
        dialog.setWindowTitle("Обновление приложения")
        dialog.setIcon(QMessageBox.Information)
        dialog.setText(message)
        update_button = dialog.addButton("Обновить", QMessageBox.AcceptRole)
        skip_button = dialog.addButton("Пропустить эту версию", QMessageBox.RejectRole)
        dialog.addButton("Позже", QMessageBox.DestructiveRole)
        dialog.exec()
        if dialog.clickedButton() == update_button:
            if platform.system() == "Windows":
                self._start_windows_download(release, parent)
            else:
                try:
                    _launch_macos_update(release["url"])
                except Exception as error:
                    QMessageBox.critical(parent, "Обновление приложения", str(error))
                else:
                    QApplication.quit()
        elif dialog.clickedButton() == skip_button:
            settings.setValue(SKIPPED_VERSION_KEY, latest_version)

    def _start_windows_download(self, release, parent):
        if self._download_thread is not None:
            return
        self._dialog_parent = parent
        self._download_release = release
        self._progress_dialog = QProgressDialog("Скачивание и проверка обновления…", "", 0, 100, parent)
        self._progress_dialog.setWindowTitle("Обновление NFProgress")
        self._progress_dialog.setCancelButton(None)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setValue(0)
        self._download_thread = QThread(self)
        self._download_worker = UpdateDownloadWorker(release)
        self._download_worker.moveToThread(self._download_thread)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_thread.start()

    @Slot(int, int)
    def _on_download_progress(self, downloaded, total):
        if self._progress_dialog is not None and total > 0:
            self._progress_dialog.setValue(min(100, int(downloaded * 100 / total)))

    @Slot(str)
    def _on_download_finished(self, archive_path):
        parent = self._dialog_parent
        release = self._download_release
        self._cleanup_download_worker()
        try:
            migrating, app_dir = _launch_windows_updater(release, Path(archive_path))
        except Exception as error:
            _logger().exception("Не удалось запустить updater")
            QMessageBox.critical(
                parent,
                "Обновление приложения",
                f"Не удалось запустить updater.\n\n{error}\n\nЛог: {_update_log_path()}",
            )
            return
        if migrating:
            _debug(f"Запущена миграция standalone в {app_dir}")
        QApplication.quit()

    @Slot(str)
    def _on_download_failed(self, message):
        parent = self._dialog_parent
        self._cleanup_download_worker()
        QMessageBox.critical(
            parent,
            "Обновление приложения",
            f"Обновление не скачано и не будет установлено.\n\n{message}\n\nЛог: {_update_log_path()}",
        )

    def _cleanup_download_worker(self):
        if self._download_thread is None:
            return
        thread, worker = self._download_thread, self._download_worker
        dialog = self._progress_dialog
        self._download_thread = self._download_worker = None
        self._download_release = self._progress_dialog = self._dialog_parent = None
        if dialog is not None:
            dialog.close()
            dialog.deleteLater()
        worker.deleteLater()
        thread.quit()
        thread.wait()
        thread.deleteLater()
