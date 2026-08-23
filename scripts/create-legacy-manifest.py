#!/usr/bin/env python3
"""Create the flat legacy manifest consumed by older nfprogress builds."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    source = Path("update_manifest.json")
    manifest = json.loads(source.read_text(encoding="utf-8"))
    legacy = {
        "version": str(manifest.get("version", "")).strip(),
        "notes": str(manifest.get("notes", "")).strip(),
    }
    for platform in ("windows", "macos_arm", "macos_intel"):
        section = manifest.get(platform)
        version = str(manifest.get(f"{platform}_version", "")).strip()
        url = manifest.get(f"{platform}_url")
        if isinstance(section, dict):
            version = str(section.get("version") or version).strip()
            url = section.get("url") or url
        if version and url:
            legacy[f"{platform}_version"] = version
            legacy[f"{platform}_url"] = url
    Path("update_manifest_legacy.json").write_text(
        json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Created update_manifest_legacy.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
