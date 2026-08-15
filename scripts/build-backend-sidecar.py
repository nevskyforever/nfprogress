#!/usr/bin/env python3
"""Build the Tauri Python backend as a target-triple named Nuitka sidecar."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINARIES = ROOT / 'frontend' / 'src-tauri' / 'binaries'
SUPPORTED_TARGETS = {
    'aarch64-apple-darwin',
    'x86_64-apple-darwin',
    'x86_64-pc-windows-msvc',
}


def _host_target() -> str:
    rustc = shutil.which('rustc') or str(Path.home() / '.cargo' / 'bin' / 'rustc')
    result = subprocess.run(
        [rustc, '-vV'],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith('host: '):
            return line.removeprefix('host: ').strip()
    raise RuntimeError('rustc did not report its host target')


def _validate_target(target: str) -> None:
    if target not in SUPPORTED_TARGETS:
        choices = ', '.join(sorted(SUPPORTED_TARGETS))
        raise SystemExit(f'Unsupported Tauri target {target!r}. Expected one of: {choices}.')
    system = platform.system()
    if target.endswith('apple-darwin') and system != 'Darwin':
        raise SystemExit('A macOS sidecar must be built on macOS.')
    if target.endswith('windows-msvc') and system != 'Windows':
        raise SystemExit('The Windows sidecar must be built on Windows.')


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', default=None, help='Rust target triple; defaults to rustc host.')
    return parser


def main(argv: list[str] | None = None) -> int:
    target = _parser().parse_args(argv).target or _host_target()
    _validate_target(target)
    BINARIES.mkdir(parents=True, exist_ok=True)
    executable_name = f'nfprogress-backend-{target}'
    if target.endswith('windows-msvc'):
        executable_name += '.exe'

    command = [
        sys.executable,
        '-m',
        'nuitka',
        '--onefile',
        '--assume-yes-for-downloads',
        '--remove-output',
        f'--output-dir={BINARIES}',
        f'--output-filename={executable_name}',
        '--include-package=backend',
        '--include-package=nfprogress',
        '--include-package=uvicorn',
        '--nofollow-import-to=PySide6',
        '--python-flag=-O',
    ]
    if target == 'x86_64-apple-darwin':
        command.append('--macos-target-arch=x86_64')
    command.append(str(ROOT / 'backend_sidecar.py'))
    subprocess.run(command, cwd=ROOT, check=True)

    output = BINARIES / executable_name
    if not output.is_file():
        raise SystemExit(f'Nuitka completed without the expected sidecar: {output}')
    print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
