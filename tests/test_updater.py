import hashlib
import io
import logging
import shutil
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

import update_checker
import updater_core
import engine
import updater_main


class _RunningProcess:
    pid = 4321

    def poll(self):
        return None


class _Response:
    def __init__(self, payload: bytes, status: int = 200, content_length=None):
        self._stream = io.BytesIO(payload)
        self._status = status
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def getcode(self):
        return self._status

    def read(self, size=-1):
        return self._stream.read(size)


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="nfprogress-tests-"))
        self.archive = self.temp_dir / "nfprogress-update.zip"
        self.logger = logging.getLogger(f"updater-test-{id(self)}")
        self.logger.addHandler(logging.NullHandler())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_archive(self, files=None):
        files = files or {
            "nfprogress/nfprogress.exe": b"new-main",
            "nfprogress/nfprogress-updater.exe": b"new-updater",
            "nfprogress/updater-runtime/nfprogress-updater.exe": b"runtime-updater",
            "nfprogress/runtime.dll": b"runtime",
        }
        with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_correct_sha256(self):
        expected = self._make_archive()
        updater_core.verify_sha256(self.archive, expected)

    def test_wrong_sha256(self):
        self._make_archive()
        with self.assertRaises(updater_core.UpdateError):
            updater_core.verify_sha256(self.archive, "0" * 64)

    def test_corrupted_zip(self):
        self.archive.write_bytes(b"not a zip")
        with self.assertRaises(updater_core.UpdateError):
            updater_core.inspect_archive(self.archive, self.temp_dir / "extract")

    def test_zip_slip_is_rejected(self):
        self._make_archive({
            "nfprogress/nfprogress.exe": b"main",
            "nfprogress/nfprogress-updater.exe": b"updater",
            "nfprogress/updater-runtime/nfprogress-updater.exe": b"runtime-updater",
            "nfprogress/../../outside.txt": b"bad",
        })
        with self.assertRaises(updater_core.UpdateError):
            updater_core.inspect_archive(self.archive, self.temp_dir / "extract")

    def test_missing_main_executable(self):
        self._make_archive({
            "nfprogress/nfprogress-updater.exe": b"updater",
            "nfprogress/updater-runtime/nfprogress-updater.exe": b"runtime-updater",
        })
        with self.assertRaises(updater_core.UpdateError):
            updater_core.inspect_archive(self.archive, self.temp_dir / "extract")

    def test_insufficient_disk_space(self):
        self._make_archive()
        usage = shutil._ntuple_diskusage(total=100, used=100, free=0)
        with mock.patch("updater_core.shutil.disk_usage", return_value=usage):
            with self.assertRaises(updater_core.UpdateError):
                updater_core.extract_archive_safely(self.archive, self.temp_dir / "extract")

    def test_process_exit_timeout(self):
        with mock.patch("updater_core._pid_exists", return_value=True):
            with self.assertRaises(updater_core.UpdateError):
                updater_core.wait_for_process_exit(123, timeout=0)

    def test_blocked_new_folder_restores_old_version(self):
        expected = self._make_archive()
        app_dir = self.temp_dir / "nfprogress"
        app_dir.mkdir()
        (app_dir / "nfprogress.exe").write_bytes(b"old-main")
        original_replace = Path.replace

        def blocked_replace(path, target):
            if path.name == "nfprogress" and path.parent.name == ".nfprogress-update-staging":
                raise PermissionError("blocked")
            return original_replace(path, target)

        with mock.patch.object(Path, "replace", blocked_replace):
            with self.assertRaises(PermissionError):
                updater_core.install_update(app_dir, self.archive, expected, 0, self.logger)
        self.assertEqual((app_dir / "nfprogress.exe").read_bytes(), b"old-main")

    def test_cannot_rename_current_folder_keeps_old_version(self):
        expected = self._make_archive()
        app_dir = self.temp_dir / "nfprogress"
        app_dir.mkdir()
        (app_dir / "nfprogress.exe").write_bytes(b"old-main")
        original_replace = Path.replace

        def blocked_replace(path, target):
            if path == app_dir:
                raise PermissionError("locked")
            return original_replace(path, target)

        with mock.patch.object(Path, "replace", blocked_replace):
            with self.assertRaises(PermissionError):
                updater_core.install_update(app_dir, self.archive, expected, 0, self.logger)
        self.assertEqual((app_dir / "nfprogress.exe").read_bytes(), b"old-main")

    def test_launch_failure_rolls_back(self):
        expected = self._make_archive()
        app_dir = self.temp_dir / "nfprogress"
        app_dir.mkdir()
        (app_dir / "nfprogress.exe").write_bytes(b"old-main")

        def fail_launch(_executable):
            raise OSError("cannot launch")

        with self.assertRaises(OSError):
            updater_core.install_update(
                app_dir, self.archive, expected, 0, self.logger, launcher=fail_launch
            )
        self.assertEqual((app_dir / "nfprogress.exe").read_bytes(), b"old-main")

    def test_successful_update_launches_new_version(self):
        expected = self._make_archive()
        app_dir = self.temp_dir / "nfprogress"
        app_dir.mkdir()
        (app_dir / "nfprogress.exe").write_bytes(b"old-main")
        launched = []

        def launch(executable):
            launched.append(executable)
            return _RunningProcess()

        with mock.patch("updater_core.STARTUP_CHECK_SECONDS", 0):
            updater_core.install_update(
                app_dir, self.archive, expected, 0, self.logger, launcher=launch
            )
        self.assertEqual((app_dir / "nfprogress.exe").read_bytes(), b"new-main")
        self.assertEqual(launched, [(app_dir / "nfprogress.exe").resolve()])
        self.assertFalse((self.temp_dir / ".nfprogress-backup").exists())

    def test_user_data_outside_app_folder_is_preserved(self):
        expected = self._make_archive()
        app_dir = self.temp_dir / "Programs" / "nfprogress"
        app_dir.mkdir(parents=True)
        (app_dir / "nfprogress.exe").write_bytes(b"old-main")
        user_data = self.temp_dir / "AppData" / "Roaming" / "nfprogress" / "data.pkl"
        user_data.parent.mkdir(parents=True)
        user_data.write_bytes(b"projects")
        with mock.patch("updater_core.STARTUP_CHECK_SECONDS", 0):
            updater_core.install_update(
                app_dir, self.archive, expected, 0, self.logger, launcher=lambda _path: _RunningProcess()
            )
        self.assertEqual(user_data.read_bytes(), b"projects")

    def test_onefile_migration_installs_into_empty_standalone_directory(self):
        expected = self._make_archive()
        app_dir = self.temp_dir / "LocalAppData" / "Programs" / "nfprogress"
        app_dir.parent.mkdir(parents=True)
        with mock.patch("updater_core.STARTUP_CHECK_SECONDS", 0):
            updater_core.install_update(
                app_dir, self.archive, expected, 0, self.logger, launcher=lambda _path: _RunningProcess()
            )
        self.assertTrue((app_dir / "nfprogress.exe").is_file())


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="nfprogress-download-tests-"))
        self.payload = b"zip payload"
        self.release = {
            "version": "9.9",
            "url": "https://example.invalid/update.zip",
            "sha256": hashlib.sha256(self.payload).hexdigest(),
            "size": len(self.payload),
            "entry_point": "nfprogress/nfprogress.exe",
        }
        self.data_patch = mock.patch("update_checker._update_data_dir", return_value=self.temp_dir)
        self.data_patch.start()

    def tearDown(self):
        self.data_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_download_checks_hash_and_uses_predictable_name(self):
        response = _Response(self.payload, content_length=len(self.payload))
        with mock.patch("update_checker.urllib.request.urlopen", return_value=response):
            path = update_checker._download_update_archive(dict(self.release))
        self.assertEqual(path.name, "nfprogress-update.zip")
        self.assertEqual(path.read_bytes(), self.payload)

    def test_no_network_removes_partial_archive(self):
        with mock.patch(
            "update_checker.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            with self.assertRaises(urllib.error.URLError):
                update_checker._download_update_archive(dict(self.release))
        self.assertFalse((self.temp_dir / "updates" / "nfprogress-update.zip").exists())

    def test_http_404_and_500_are_rejected(self):
        for status in (404, 500):
            error = urllib.error.HTTPError(self.release["url"], status, "error", {}, None)
            with self.subTest(status=status):
                with mock.patch("update_checker.urllib.request.urlopen", side_effect=error):
                    with self.assertRaises(urllib.error.HTTPError):
                        update_checker._download_update_archive(dict(self.release))

    def test_download_size_limit(self):
        response = _Response(self.payload + b"extra")
        with mock.patch("update_checker.urllib.request.urlopen", return_value=response):
            with self.assertRaises(RuntimeError):
                update_checker._download_update_archive(dict(self.release))
        self.assertFalse((self.temp_dir / "updates" / "nfprogress-update.zip").exists())

    def test_manifest_without_sha256_is_rejected(self):
        release = dict(self.release)
        release["sha256"] = ""
        with self.assertRaises(ValueError):
            update_checker._validate_windows_release(release)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="nfprogress-migration-tests-"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_windows_user_data_is_copied_without_deleting_source(self):
        profile = self.temp_dir / "profile"
        roaming = self.temp_dir / "roaming"
        legacy = profile / "Documents" / "nfprogress"
        legacy.mkdir(parents=True)
        (legacy / "data.pkl").write_bytes(b"projects")
        (legacy / "gamer.pkl").write_bytes(b"gamer")
        destination = roaming / "nfprogress"
        destination.mkdir(parents=True)
        (destination / "gamer.pkl").write_bytes(b"newer-gamer")

        with mock.patch.object(engine, "SYSTEM", "Windows"), mock.patch.dict(
            "os.environ", {"APPDATA": str(roaming), "USERPROFILE": str(profile)}, clear=False
        ):
            result = engine.get_app_data_dir()

        self.assertEqual(result, destination)
        self.assertEqual((destination / "data.pkl").read_bytes(), b"projects")
        self.assertEqual((destination / "gamer.pkl").read_bytes(), b"newer-gamer")
        self.assertEqual((legacy / "data.pkl").read_bytes(), b"projects")

    def test_migration_shortcut_points_to_standalone_executable(self):
        desktop = self.temp_dir / "Desktop"
        executable = self.temp_dir / "Programs" / "nfprogress" / "nfprogress.exe"
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"MZ")
        with mock.patch("updater_main._desktop_directory", return_value=desktop):
            shortcut = updater_main._create_desktop_shortcut(executable)
        text = shortcut.read_text(encoding="utf-8")
        self.assertIn(executable.resolve().as_uri(), text)
        self.assertTrue(shortcut.is_file())


if __name__ == "__main__":
    unittest.main()
