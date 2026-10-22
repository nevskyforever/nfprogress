#!/usr/bin/env python3
"""Validate a release candidate, then atomically update the landing manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


PLATFORMS = {"windows", "macos-arm", "macos-intel"}
ALLOWED_URL_HOSTS = {"github.com", "nfproject.ru", "worta.ru", "www.worta.ru"}
ALLOWED_REDIRECT_HOSTS = ALLOWED_URL_HOSTS | {
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}
DOWNLOAD_FORMATS = {
    "windows": (("windows-x86_64", "windows-x64", "windows-x86-64", "win-x64"), {".exe"}),
    "macos-arm": (("mac-arm", "macos-arm", "mac-arm64", "macos-arm64", "mac-aarch64", "macos-aarch64", "darwin-arm64", "darwin-aarch64"), {".dmg", ".zip"}),
    "macos-intel": (("mac-intel", "macos-intel", "mac-x86_64", "macos-x86_64", "mac-x64", "macos-x64", "darwin-x86_64", "darwin-x64"), {".dmg", ".zip"}),
}
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")


class ReleaseError(Exception):
    """Raised when the candidate manifest is unsafe or incomplete."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise ReleaseError(f"Invalid release version: {value!r}")
    match = VERSION_PATTERN.fullmatch(value)
    if not match:
        raise ReleaseError(f"Invalid release version: {value!r}")
    return tuple(int(part) for part in match.groups())


def _check_download(url: str) -> None:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as error:
        raise ReleaseError(f"Download URL is malformed: {url}") from error
    if parts.scheme != "https" or parts.hostname not in ALLOWED_URL_HOSTS:
        raise ReleaseError(f"Download URL must use HTTPS on an approved host: {url}")
    if parts.username or parts.password or parts.fragment or port not in (None, 443):
        raise ReleaseError(f"Download URL contains unsupported components: {url}")

    marker = "\n__WORTA_RELEASE_CHECK__"
    try:
        result = subprocess.run(
            [
                "curl", "--fail", "--silent", "--show-error", "--location", "--head",
                "--max-time", "20", "--write-out", f"{marker}%{{http_code}}\n%{{url_effective}}\n", url,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=25,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReleaseError(f"Could not verify download URL {url}: {error}") from error
    if result.returncode != 0:
        reason = result.stderr.strip() or f"curl exited with status {result.returncode}"
        raise ReleaseError(f"Could not verify download URL {url}: {reason}")

    headers, separator, metadata = result.stdout.rpartition(marker)
    if not separator:
        raise ReleaseError(f"Could not read the HTTP response for {url}")
    status_text, _, final_url = metadata.partition("\n")
    if not status_text.isdigit() or not 200 <= int(status_text) < 300:
        raise ReleaseError(f"Download URL returned HTTP {status_text or 'unknown'}: {url}")
    final = urlsplit(final_url.strip())
    try:
        final_port = final.port
    except ValueError as error:
        raise ReleaseError(f"Download URL redirected to an invalid URL: {url}") from error
    if final.scheme != "https" or final.hostname not in ALLOWED_REDIRECT_HOSTS or final_port not in (None, 443):
        raise ReleaseError(f"Download URL redirected to an unapproved host: {url}")

    lengths = re.findall(r"(?im)^content-length:\s*(\d+)\s*$", headers)
    if lengths and int(lengths[-1]) <= 0:
        raise ReleaseError(f"Download URL points to an empty file: {url}")


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError(f"Could not read JSON file {path}: {error}") from error
    if not isinstance(value, dict):
        raise ReleaseError(f"Expected a JSON object in {path}")
    return value


def validate_candidate(candidate: dict, current: dict) -> None:
    if candidate.get("schema_version") != 1:
        raise ReleaseError("schema_version must be 1")
    releases = candidate.get("releases")
    if not isinstance(releases, list) or len(releases) != len(PLATFORMS):
        raise ReleaseError("Candidate must contain exactly one entry for every supported platform")

    by_platform: dict[str, dict] = {}
    for release in releases:
        if not isinstance(release, dict):
            raise ReleaseError("Every release entry must be an object")
        platform = release.get("platform")
        status = release.get("status")
        if platform not in PLATFORMS or platform in by_platform:
            raise ReleaseError(f"Unknown or duplicate platform: {platform!r}")
        if status not in {"available", "preparing", "unavailable"}:
            raise ReleaseError(f"Invalid status for {platform}: {status!r}")

        version = release.get("version")
        if version is not None:
            if not isinstance(version, str):
                raise ReleaseError(f"Version must be a string or null for {platform}")
            _version_tuple(version)

        url = release.get("url")
        if status == "available":
            if not version or not isinstance(url, str):
                raise ReleaseError(f"Available platform requires a version and URL: {platform}")
            url_path = unquote(urlsplit(url).path).lower()
            filename = url_path.rsplit("/", 1)[-1]
            architecture_markers, extensions = DOWNLOAD_FORMATS[platform]
            if version not in url_path:
                raise ReleaseError(f"Version must appear in the download URL for {platform}")
            if not any(marker in filename for marker in architecture_markers):
                raise ReleaseError(f"Download filename does not identify the {platform} architecture")
            if Path(filename).suffix not in extensions:
                raise ReleaseError(f"Download file type is not supported for {platform}")
            _check_download(url)
        elif url is not None:
            raise ReleaseError(f"Non-available platform must not have a URL: {platform}")
        elif status == "preparing" and not version:
            raise ReleaseError(f"Preparing platform requires a version: {platform}")
        if "message" in release and (not isinstance(release["message"], str) or len(release["message"]) > 300):
            raise ReleaseError(f"Invalid status message for {platform}")
        by_platform[platform] = release

    if set(by_platform) != PLATFORMS:
        raise ReleaseError("Candidate must include Windows x64, macOS ARM, and macOS Intel")

    old_releases = current.get("releases", [])
    if isinstance(old_releases, list):
        old_by_platform = {
            release.get("platform"): release
            for release in old_releases
            if isinstance(release, dict) and release.get("status") == "available"
        }
        for platform, old_release in old_by_platform.items():
            new_release = by_platform.get(platform)
            if not new_release or new_release.get("status") != "available":
                raise ReleaseError(f"Refusing to remove the verified {platform} release")
            if _version_tuple(new_release["version"]) < _version_tuple(old_release["version"]):
                raise ReleaseError(f"Refusing to replace {platform} with an older version")

    message = candidate.get("message")
    if message is not None and (not isinstance(message, str) or len(message) > 500):
        raise ReleaseError("message must be a string of at most 500 characters")


def atomic_write(path: Path, data: dict) -> None:
    contents = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".releases-", suffix=".tmp", delete=False
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(contents)
            temporary.flush()
            mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
            if hasattr(os, "fchmod"):
                os.fchmod(temporary.fileno(), mode)
            else:
                os.chmod(temporary.name, mode)
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except OSError:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="JSON file with the complete candidate platform list")
    args = parser.parse_args()

    manifest_path = Path(__file__).with_name("releases.json")
    try:
        candidate = _load_json(args.candidate)
        current = _load_json(manifest_path)
        validate_candidate(candidate, current)
        atomic_write(manifest_path, candidate)
    except ReleaseError as error:
        print(f"Release manifest not changed: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Release manifest write failed: {error}", file=sys.stderr)
        return 1

    print(f"Updated {manifest_path} after validating every available installer URL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
