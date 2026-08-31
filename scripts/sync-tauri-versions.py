#!/usr/bin/env python3
"""Synchronize Tauri package versions from the canonical engine version."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'engine.py'
DEFAULT_FRONTEND_DIR = ROOT / 'frontend'
ENGINE_VERSION = re.compile(r"^version\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
SEMVER = re.compile(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?([+-][0-9A-Za-z.-]+)?$')


def canonical_version(raw: str) -> str:
    match = SEMVER.fullmatch(raw.strip().lstrip('v'))
    if not match:
        raise ValueError(f'engine.version is not a supported semantic version: {raw!r}')
    major, minor, patch, suffix = match.groups()
    return f'{major}.{minor or "0"}.{patch or "0"}{suffix or ""}'


def read_engine_version() -> str:
    match = ENGINE_VERSION.search(ENGINE.read_text(encoding='utf-8'))
    if not match:
        raise ValueError(f'Could not find version in {ENGINE}.')
    return canonical_version(match.group(1))


def synchronize(version: str, frontend_dir: Path = DEFAULT_FRONTEND_DIR) -> None:
    tauri_dir = frontend_dir / 'src-tauri'
    tauri_config = tauri_dir / 'tauri.conf.json'
    cargo_toml = tauri_dir / 'Cargo.toml'
    cargo_lock = tauri_dir / 'Cargo.lock'

    config = json.loads(tauri_config.read_text(encoding='utf-8'))
    config['version'] = version
    tauri_config.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    cargo = cargo_toml.read_text(encoding='utf-8')
    cargo, count = re.subn(
        r'(?m)^(version\s*=\s*)"[^"]+"$',
        rf'\g<1>"{version}"',
        cargo,
        count=1,
    )
    if count != 1:
        raise ValueError(f'Could not find the package version in {cargo_toml}.')
    cargo_toml.write_text(cargo, encoding='utf-8')

    lock = cargo_lock.read_text(encoding='utf-8')
    lock, count = re.subn(
        r'(?ms)(\[\[package\]\]\s+name = "nfprogress-desktop"\s+version = )"[^"]+"',
        rf'\g<1>"{version}"',
        lock,
        count=1,
    )
    if count != 1:
        raise ValueError(f'Could not find nfprogress-desktop in {cargo_lock}.')
    cargo_lock.write_text(lock, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version-only', action='store_true')
    parser.add_argument(
        '--frontend-dir',
        type=Path,
        default=DEFAULT_FRONTEND_DIR,
        help='Frontend directory whose Tauri metadata should be synchronized.',
    )
    args = parser.parse_args()
    version = read_engine_version()
    if not args.version_only:
        synchronize(version, args.frontend_dir.resolve())
        print(f'Synchronized Tauri files to {version}.')
    print(version)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
