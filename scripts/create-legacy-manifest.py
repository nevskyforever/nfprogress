#!/usr/bin/env python3
import json
from pathlib import Path


PLATFORM_KEYS = {
    "windows": ("windows_version", "windows_url", "nfprogress-windows-{version}.zip"),
    "macos_arm": ("macos_arm_version", "macos_arm_url", "nfprogress-mac-arm-{version}.zip"),
    "macos_intel": ("macos_intel_version", "macos_intel_url", "nfprogress-mac-intel-{version}.zip"),
}


def _version_sort_key(version):
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


def main() -> int:
    manifest_path = Path("update_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    versions = [
        str(manifest.get(version_key, "")).strip()
        for version_key, _, _ in PLATFORM_KEYS.values()
    ]
    versions = [version for version in versions if version]
    if not versions:
        raise SystemExit("No platform versions found in update_manifest.json")

    legacy_version = min(versions, key=_version_sort_key)
    legacy_manifest = {
        "version": legacy_version,
        "windows_url": f"https://nfproject.ru/app/nfprogress-windows-{legacy_version}.zip",
        "macos_arm_url": f"https://nfproject.ru/app/nfprogress-mac-arm-{legacy_version}.zip",
        "macos_intel_url": f"https://nfproject.ru/app/nfprogress-mac-intel-{legacy_version}.zip",
        "notes": str(manifest.get("notes", "")).strip(),
    }

    Path("update_manifest_legacy.json").write_text(
        json.dumps(legacy_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created update_manifest_legacy.json for legacy version {legacy_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
