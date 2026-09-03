"""Explicitly rebuild the SQLite shadow mirror from legacy PKL files."""

from __future__ import annotations

import argparse
import sys

from nfprogress.core.sqlite import SQLiteMirrorRepository
from nfprogress.core.storage import PickleRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, help='explicit NFProgress data root')
    args = parser.parse_args(argv)
    repository = PickleRepository(args.data_dir)
    repository.create_backup()
    try:
        repository.synchronize_shadow()
    except Exception as error:
        print(f'SQLite rebuild failed: {error}', file=sys.stderr)
        return 1
    print(f'SQLite mirror rebuilt: {SQLiteMirrorRepository(repository.base_dir).path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
