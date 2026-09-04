"""Build the migration-only helper as a standalone PyInstaller executable.

This artifact is separate from the Tauri bundle and is never launched by the
normal desktop startup path.  The script intentionally builds only for the
host interpreter; release engineering must repeat it on macOS Intel and
Windows before publishing.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/migration-helper"))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    output = args.output.expanduser().resolve()
    work = output.parent / f".{output.name}-build"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(output, ignore_errors=True)
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", output.name, "--distpath", str(output.parent), "--workpath", str(work),
        "--specpath", str(work), "--paths", str(root),
        "--hidden-import", "engine", "--hidden-import", "game", "--hidden-import", "game_data",
        "--collect-submodules", "nfprogress.core", str(root / "nfprogress" / "migration_helper.py"),
    ]
    for migration in sorted((root / "nfprogress" / "core" / "sqlite" / "migrations").glob("*.sql")):
        command.extend(["--add-data", f"{migration}{os.pathsep}nfprogress/core/sqlite/migrations"])
    completed = subprocess.run(command, cwd=root, check=False)
    shutil.rmtree(work, ignore_errors=True)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
