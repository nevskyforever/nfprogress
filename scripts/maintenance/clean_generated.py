#!/usr/bin/env python3
"""Audit known project build outputs; deletion requires --apply.

Run after stopping builds. Main dependencies, user data, Git history and worktrees
are retained. Sizes distinguish apparent bytes from allocated filesystem blocks.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


GENERATED = (
    'frontend/src-tauri/target',
    'frontend/dist',
    '.tauri-build-workspaces/arm/frontend/src-tauri/target',
    '.tauri-build-workspaces/intel/frontend/src-tauri/target',
    '.tauri-build-workspaces/arm/frontend/node_modules',
    '.tauri-build-workspaces/intel/frontend/node_modules',
    'frontend/android/.gradle',
    'frontend/android/build',
    'frontend/android/app/build/generated',
    'frontend/android/app/build/intermediates',
    'frontend/android/app/build/outputs',
    'frontend/android/app/build/tmp',
    'frontend/android/capacitor-cordova-android-plugins/build',
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True)


def repository_root() -> Path:
    root = Path(git(Path(__file__).resolve().parent, 'rev-parse', '--show-toplevel').strip()).resolve()
    if not (root / 'frontend/src-tauri/Cargo.toml').is_file():
        raise ValueError('Not a WORTA repository with a Cargo manifest')
    return root


def size(path: Path) -> tuple[int, int]:
    """Count regular entries without following symlinks or double-counting hardlinks."""
    apparent = allocated = 0
    seen = set()
    for base, dirs, files in os.walk(path, followlinks=False):
        for name in files + dirs:
            entry = Path(base) / name
            info = entry.lstat()
            if entry.is_symlink() or not entry.is_file():
                continue
            key = (info.st_dev, info.st_ino)
            if key in seen:
                continue
            seen.add(key)
            apparent += info.st_size
            allocated += getattr(info, 'st_blocks', (info.st_size + 511) // 512) * 512
    return apparent, allocated


def validate(root: Path, relative: str) -> Path:
    if relative not in GENERATED:
        raise ValueError(f'Not allowlisted: {relative}')
    root = root.resolve()
    path = root / relative
    resolved = path.resolve(strict=True)
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(f'Path escapes repository: {relative}')
    # Even an internal directory alias is ambiguous: only literal output paths.
    if resolved != path or not path.is_dir():
        raise ValueError(f'Symlinked/non-directory output: {relative}')
    tracked = git(root, 'ls-files', '-z').split('\0')
    if any(p and (p == relative or p.startswith(relative + '/') or relative.startswith(p + '/')) for p in tracked):
        raise ValueError(f'Tracked content in/above output: {relative}')
    ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', '--', relative])
    if ignored.returncode != 0:
        raise ValueError(f'Output is not ignored: {relative}')
    for base, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            entry = Path(base) / name
            if name in ('.git', '__pycache__') or name in ('engine.cpython-312.pyc', 'game_data.cpython-312.pyc'):
                raise ValueError(f'Protected/nested repository content: {entry}')
            if entry.is_symlink() and not entry.resolve().is_relative_to(root):
                raise ValueError(f'Symlink escapes repository: {entry}')
    return path


def audit(root: Path) -> tuple[list[tuple[str, int, int]], list[str]]:
    candidates = []
    problems = []
    for relative in GENERATED:
        path = root / relative
        if not path.exists() and not path.is_symlink():
            continue
        try:
            path = validate(root, relative)
            apparent, allocated = size(path)
            candidates.append((relative, apparent, allocated))
            warning = ' STRONG WARNING >5 GB' if apparent > 5_000_000_000 else ' WARNING >1 GB' if apparent > 1_000_000_000 else ''
            print(f'SAFE {relative}: apparent={apparent} allocated={allocated} bytes{warning}')
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            problems.append(str(error))
            print(f'REFUSED {relative}: {error}', file=sys.stderr)
    return candidates, problems


def worktree_report(root: Path) -> None:
    print('Registered worktrees (report only; never removed):')
    for line in git(root, 'worktree', 'list', '--porcelain').splitlines():
        if not line.startswith('worktree '):
            continue
        path = Path(line[9:])
        if not path.is_dir():
            print(f'  {path}: MISSING; registration retained')
            continue
        usage = subprocess.check_output(['du', '-sk', str(path)], text=True).split()[0]
        status = git(path, 'status', '--porcelain=v1')
        head = git(path, 'rev-parse', 'HEAD').strip()
        branch = git(path, 'branch', '--show-current').strip() or 'detached'
        print(f'  {path}: allocated={int(usage) * 1024} bytes branch={branch} HEAD={head} {"DIRTY" if status else "CLEAN"}; retained (age alone does not prove stale)')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Delete validated generated outputs in this worktree only; stop builds first')
    args = parser.parse_args()
    try:
        root = repository_root()
        print(f'Repository: {root}; mode: {"APPLY" if args.apply else "DRY RUN"}')
        worktree_report(root)
        candidates, problems = audit(root)
        print(f'Total potential: apparent={sum(p[1] for p in candidates)} allocated={sum(p[2] for p in candidates)} bytes')
        if problems:
            print('Ambiguous output found; nothing deleted.', file=sys.stderr)
            return 1
        if args.apply:
            # Revalidate the complete plan before any deletion, then each path.
            for relative, _, _ in candidates:
                validate(root, relative)
            for relative, apparent, allocated in candidates:
                path = validate(root, relative)
                shutil.rmtree(path)
                print(f'DELETED {relative}: before apparent={apparent} allocated={allocated}; after=0 bytes')
            print(f'Total removed: apparent={sum(p[1] for p in candidates)} allocated={sum(p[2] for p in candidates)} bytes (APFS snapshots/clones may delay physical recovery)')
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'Cleanup failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
