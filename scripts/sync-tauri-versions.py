#!/usr/bin/env python3
"""Synchronize Tauri package versions from the canonical engine version."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'engine.py'
TAURI_CONFIG = ROOT / 'frontend' / 'src-tauri' / 'tauri.conf.json'
CARGO_TOML = ROOT / 'frontend' / 'src-tauri' / 'Cargo.toml'
CARGO_LOCK = ROOT / 'frontend' / 'src-tauri' / 'Cargo.lock'
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


def synchronize(version: str) -> None:
    config = json.loads(TAURI_CONFIG.read_text(encoding='utf-8'))
    config['version'] = version
    TAURI_CONFIG.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    cargo = CARGO_TOML.read_text(encoding='utf-8')
    cargo, count = re.subn(
        r'(?m)^(version\s*=\s*)"[^"]+"$',
        rf'\g<1>"{version}"',
        cargo,
        count=1,
    )
    if count != 1:
        raise ValueError(f'Could not find the package version in {CARGO_TOML}.')
    CARGO_TOML.write_text(cargo, encoding='utf-8')

    lock = CARGO_LOCK.read_text(encoding='utf-8')
    lock, count = re.subn(
        r'(?ms)(\[\[package\]\]\s+name = "nfprogress-desktop"\s+version = )"[^"]+"',
        rf'\g<1>"{version}"',
        lock,
        count=1,
    )
    if count != 1:
        raise ValueError(f'Could not find nfprogress-desktop in {CARGO_LOCK}.')
    CARGO_LOCK.write_text(lock, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version-only', action='store_true')
    args = parser.parse_args()
    version = read_engine_version()
    if not args.version_only:
        synchronize(version)
        print(f'Synchronized Tauri files to {version}.')
    print(version)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
