import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCRIPT = PROJECT_ROOT / "scripts" / "update-release-manifest.py"


def test_windows_manifest_contains_installer_metadata(tmp_path):
    archive = tmp_path / "nfprogress-windows-9.1.zip"
    installer = tmp_path / "nfprogress-setup-9.1.exe"
    archive.write_bytes(b"standalone archive")
    installer.write_bytes(b"MZ installer")
    (tmp_path / "update_manifest.json").write_text(
        json.dumps(
            {
                "version": "9.0",
                "macos_arm": {
                    "version": "9.0",
                    "url": "https://nfproject.ru/app/nfprogress-mac-arm-9.0.zip",
                },
                "macos_intel": {
                    "version": "9.0",
                    "url": "https://nfproject.ru/app/nfprogress-mac-intel-9.0.zip",
                },
            }
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["RELEASE_NOTES"] = "Installer test"

    result = subprocess.run(
        [
            sys.executable,
            str(MANIFEST_SCRIPT),
            "9.1",
            "windows",
            str(archive),
            str(installer),
        ],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "update_manifest.json").read_text(encoding="utf-8"))
    windows = manifest["windows"]
    assert windows["url"].endswith("nfprogress-windows-9.1.zip")
    assert windows["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert windows["size"] == archive.stat().st_size
    assert windows["entry_point"] == "nfprogress/nfprogress.exe"
    assert windows["installer_url"].endswith("nfprogress-setup-9.1.exe")
    assert windows["installer_sha256"] == hashlib.sha256(installer.read_bytes()).hexdigest()
    assert windows["installer_size"] == installer.stat().st_size
    assert manifest["macos_arm"]["version"] == "9.0"
    assert manifest["windows_version"] == "9.1"
    assert manifest["windows_url"] == windows["url"]
    assert manifest["macos_arm_version"] == "9.0"
    assert manifest["macos_arm_url"] == manifest["macos_arm"]["url"]
    assert manifest["macos_intel_version"] == "9.0"
    assert manifest["macos_intel_url"] == manifest["macos_intel"]["url"]


def test_macos_manifest_update_preserves_windows_installer_metadata(tmp_path):
    windows = {
        "version": "9.1",
        "url": "https://nfproject.ru/app/nfprogress-windows-9.1.zip",
        "sha256": "1" * 64,
        "size": 100,
        "entry_point": "nfprogress/nfprogress.exe",
        "installer_url": "https://nfproject.ru/app/nfprogress-setup-9.1.exe",
        "installer_sha256": "2" * 64,
        "installer_size": 200,
    }
    (tmp_path / "update_manifest.json").write_text(
        json.dumps({"version": "9.1", "windows": windows}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT), "9.2", "macos_arm"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "update_manifest.json").read_text(encoding="utf-8"))
    assert manifest["windows"] == windows
    assert manifest["macos_arm"] == {
        "version": "9.2",
        "url": "https://nfproject.ru/app/nfprogress-mac-arm-9.2.zip",
    }
    assert manifest["windows_version"] == "9.1"
    assert manifest["windows_url"] == windows["url"]
    assert manifest["macos_arm_version"] == "9.2"
    assert manifest["macos_arm_url"] == manifest["macos_arm"]["url"]
