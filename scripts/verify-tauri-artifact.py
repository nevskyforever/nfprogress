#!/usr/bin/env python3
"""Verify that a packaged Tauri archive was built from the expected revision."""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


REVISION_PATTERN = re.compile(r"^Ревизия сборки: ([0-9a-f]{40})$", re.MULTILINE)


def artifact_revision(archive_path: Path) -> str:
    with zipfile.ZipFile(archive_path) as archive:
        source_files = [
            name for name in archive.namelist() if name.endswith('/SOURCE_CODE.txt')
        ]
        if len(source_files) != 1:
            raise ValueError('В Tauri-архиве должен быть ровно один SOURCE_CODE.txt.')
        source_text = archive.read(source_files[0]).decode('utf-8')
    match = REVISION_PATTERN.search(source_text)
    if match is None:
        raise ValueError('В SOURCE_CODE.txt отсутствует ревизия сборки.')
    return match.group(1)


def main() -> int:
    if len(sys.argv) != 3:
        print(f'Использование: {sys.argv[0]} ARCHIVE EXPECTED_REVISION', file=sys.stderr)
        return 2
    archive_path = Path(sys.argv[1])
    expected_revision = sys.argv[2].lower()
    try:
        actual_revision = artifact_revision(archive_path)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as error:
        print(f'Не удалось проверить ревизию Tauri-архива: {error}', file=sys.stderr)
        return 1
    if actual_revision != expected_revision:
        print(
            f'Tauri-архив собран из {actual_revision}, ожидается {expected_revision}.',
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
