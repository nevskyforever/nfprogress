#!/usr/bin/env python3
import json
from pathlib import Path


PLATFORM_KEYS = {
    "windows": ("windows_version", "windows_url"),
    "macos_arm": ("macos_arm_version", "macos_arm_url"),
    "macos_intel": ("macos_intel_version", "macos_intel_url"),
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

    platform_versions = {
        platform: str((manifest.get(platform) or {}).get("version") or manifest.get(version_key, "")).strip()
        for platform, (version_key, _) in PLATFORM_KEYS.items()
    }
    versions = [version for version in platform_versions.values() if version]
    if not versions:
        raise SystemExit("No platform versions found in update_manifest.json")

    legacy_version = max(versions, key=_version_sort_key)
    legacy_manifest = {
        "version": legacy_version,
        "notes": str(manifest.get("notes", "")).strip(),
    }
    for platform, (version_key, url_key) in PLATFORM_KEYS.items():
        section = manifest.get(platform)
        if isinstance(section, dict) and section.get("url"):
            legacy_manifest[version_key] = platform_versions[platform]
            legacy_manifest[url_key] = section["url"]

    Path("update_manifest_legacy.json").write_text(
        json.dumps(legacy_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created update_manifest_legacy.json for legacy version {legacy_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
