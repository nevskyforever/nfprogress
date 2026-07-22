#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


PLATFORM_KEYS = {
    "windows": ("windows_version", "windows_url", "nfprogress-windows-{version}.zip"),
    "macos_arm": ("macos_arm_version", "macos_arm_url", "nfprogress-mac-arm-{version}.zip"),
    "macos_intel": ("macos_intel_version", "macos_intel_url", "nfprogress-mac-intel-{version}.zip"),
}


def _seed_platform_versions(manifest):
    legacy_version = str(manifest.get("version", "")).strip()
    if not legacy_version:
        return

    for version_key, _, _ in PLATFORM_KEYS.values():
        manifest.setdefault(version_key, legacy_version)


def _sync_legacy_version(manifest):
    versions = [
        str(manifest.get(version_key, "")).strip()
        for version_key, _, _ in PLATFORM_KEYS.values()
    ]
    versions = [version for version in versions if version]
    if versions:
        manifest["version"] = max(versions, key=_version_sort_key)


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
    if len(sys.argv) != 3:
        print("Usage: update-release-manifest.py VERSION PLATFORM", file=sys.stderr)
        print(f"Platforms: {', '.join(PLATFORM_KEYS)}", file=sys.stderr)
        return 2

    version = sys.argv[1].strip()
    if not version:
        print("Version is empty.", file=sys.stderr)
        return 2

    platform = sys.argv[2].strip()
    if platform not in PLATFORM_KEYS:
        print(f"Unknown platform: {platform}", file=sys.stderr)
        print(f"Platforms: {', '.join(PLATFORM_KEYS)}", file=sys.stderr)
        return 2

    manifest_path = Path("update_manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {}

    _seed_platform_versions(manifest)

    version_key, url_key, filename_template = PLATFORM_KEYS[platform]
    manifest[version_key] = version
    manifest[url_key] = f"https://nfproject.ru/app/{filename_template.format(version=version)}"
    release_notes = os.environ.get("RELEASE_NOTES", "").strip()
    if release_notes:
        manifest["notes"] = release_notes
    else:
        manifest.setdefault("notes", "Исправлены ошибки и улучшена стабильность.")
    _sync_legacy_version(manifest)

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {manifest_path}: {platform}={version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
