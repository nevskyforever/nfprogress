from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARGO_MANIFEST = ROOT / 'frontend' / 'src-tauri' / 'Cargo.toml'
TARGET_DIRECTORY = CARGO_MANIFEST.parent / 'target'


def main() -> None:
    completed = subprocess.run(
        [
            'cargo', 'test', '--manifest-path', str(CARGO_MANIFEST),
            '--lib', 'c15_headless_native_bridge', '--no-run',
            '--message-format=json-render-diagnostics',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        raise SystemExit(completed.returncode)

    artifacts = []
    for line in completed.stdout.splitlines():
        message = json.loads(line)
        if message.get('reason') != 'compiler-artifact':
            continue
        target = message.get('target', {})
        profile = message.get('profile', {})
        executable = message.get('executable')
        if (target.get('name') == 'nfprogress_desktop_lib'
                and 'rlib' in target.get('kind', [])
                and profile.get('test') is True
                and executable):
            artifacts.append(Path(executable).resolve(strict=True))

    if len(artifacts) != 1:
        raise SystemExit(
            f'expected one nfprogress_desktop_lib test executable, found {len(artifacts)}'
        )
    binary = artifacts[0]
    target_directory = TARGET_DIRECTORY.resolve(strict=True)
    if (not binary.is_relative_to(target_directory)
            or not binary.name.startswith('nfprogress_desktop_lib-')
            or not os.access(binary, os.X_OK)):
        raise SystemExit(f'Cargo reported an invalid native bridge executable: {binary}')

    github_env = os.environ.get('GITHUB_ENV')
    if not github_env:
        raise SystemExit('GITHUB_ENV is required to expose the prepared native bridge to later CI steps')
    with Path(github_env).open('a', encoding='utf-8') as environment_file:
        environment_file.write(f'NFPROGRESS_C15_NATIVE_BRIDGE_BIN={binary}\n')
    print(f'Prepared exact native bridge test executable: {binary}')


if __name__ == '__main__':
    main()
