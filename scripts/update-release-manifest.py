#!/usr/bin/env python3
import hashlib
import json
import os
import sys
from pathlib import Path


PLATFORMS = {
    "windows": ("nfprogress-windows-{version}.zip", "nfprogress/nfprogress.exe"),
    "macos_arm": ("nfprogress-mac-arm-{version}.zip", None),
    "macos_intel": ("nfprogress-mac-intel-{version}.zip", None),
}


def _version_sort_key(version):
    return [int("".join(char for char in part if char.isdigit()) or 0) for part in str(version).split(".")]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _migrate_legacy_sections(manifest: dict) -> None:
    for platform in PLATFORMS:
        version = str(manifest.get(f"{platform}_version") or manifest.get("version") or "").strip()
        url = manifest.get(f"{platform}_url")
        if version and url and not isinstance(manifest.get(platform), dict):
            manifest[platform] = {"version": version, "url": url}


def main() -> int:
    if len(sys.argv) not in (3, 4, 5):
        print(
            "Usage: update-release-manifest.py VERSION PLATFORM [ARTIFACT] [INSTALLER]",
            file=sys.stderr,
        )
        print(f"Platforms: {', '.join(PLATFORMS)}", file=sys.stderr)
        return 2

    version = sys.argv[1].strip()
    platform = sys.argv[2].strip()
    if not version or platform not in PLATFORMS:
        print("Version is empty or platform is unknown.", file=sys.stderr)
        return 2

    filename_template, entry_point = PLATFORMS[platform]
    filename = filename_template.format(version=version)
    artifact = Path(sys.argv[3]) if len(sys.argv) >= 4 else None
    installer = Path(sys.argv[4]) if len(sys.argv) == 5 else None
    if platform == "windows" and artifact is None:
        print("Windows manifest requires the ZIP artifact path for SHA-256 and size.", file=sys.stderr)
        return 2
    if artifact is not None and not artifact.is_file():
        print(f"Artifact not found: {artifact}", file=sys.stderr)
        return 2
    if installer is not None and platform != "windows":
        print("Installer metadata is supported only for Windows.", file=sys.stderr)
        return 2
    if installer is not None and not installer.is_file():
        print(f"Installer not found: {installer}", file=sys.stderr)
        return 2

    manifest_path = Path("update_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    _migrate_legacy_sections(manifest)
    section = {
        "version": version,
        "url": f"https://nfproject.ru/app/{filename}",
    }
    if artifact is not None:
        section["sha256"] = _sha256(artifact)
        section["size"] = artifact.stat().st_size
    if entry_point:
        section["entry_point"] = entry_point
    if installer is not None:
        section["installer_url"] = (
            f"https://nfproject.ru/app/nfprogress-setup-{version}.exe"
        )
        section["installer_sha256"] = _sha256(installer)
        section["installer_size"] = installer.stat().st_size
    manifest[platform] = section

    for key in list(manifest):
        if key.endswith("_url") or key.endswith("_version"):
            del manifest[key]
    versions = [str(value.get("version", "")) for value in manifest.values() if isinstance(value, dict)]
    versions = [item for item in versions if item]
    manifest["version"] = max(versions, key=_version_sort_key) if versions else version
    release_notes = os.environ.get("RELEASE_NOTES", "").strip()
    if release_notes:
        manifest["notes"] = release_notes
    else:
        manifest.setdefault("notes", "Исправлены ошибки и улучшена стабильность.")

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {manifest_path}: {platform}={version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
