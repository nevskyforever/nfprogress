import json
import os
import platform
import ssl
import urllib.request

from PySide6.QtCore import QObject, QSettings, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

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
            QDesktopServices.openUrl(QUrl(download_url))
        elif clicked_button == skip_button:
            settings.setValue(SKIPPED_VERSION_KEY, latest_version)
