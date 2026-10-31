"""Run only in a child pytest process with an externally protected sentinel."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest


def test_import_and_outside_database_rejected(tmp_path: Path) -> None:
    import conftest
    from backend.app.main import app

    profile = Path(os.environ['NFPROGRESS_DATA_DIR']).parent
    print(f'ISOLATED_PROFILE={profile}')
    assert app.state.services.repository.base_dir == profile / 'app'
    assert tmp_path.is_relative_to(profile)
    with sqlite3.connect(tmp_path / 'allowed.db') as db:
        db.execute('CREATE TABLE example (id INTEGER)')
    with sqlite3.connect('file::memory:?cache=shared', uri=True) as db:
        db.execute('CREATE TABLE ephemeral (id INTEGER)')

    sentinel = Path(os.environ['WORTA_ISOLATION_SENTINEL'])
    assert not sentinel.is_relative_to(profile)
    with pytest.raises(PermissionError, match='outside the temporary profile'):
        sqlite3.connect(sentinel)
    with pytest.raises(PermissionError, match='outside the temporary profile'):
        sqlite3.connect(f'{sentinel.as_uri()}?mode=ro', uri=True)
    with pytest.raises(PermissionError, match='outside the temporary profile'):
        sqlite3.connect('file::memory:escape.db?mode=rwc', uri=True)
    with pytest.raises(PermissionError, match='outside the temporary profile'):
        sentinel.open('rb')
    with pytest.raises(PermissionError, match='outside the temporary profile'):
        sentinel.open('wb')
    if os.name != 'nt':
        link = tmp_path / 'linked.db'
        link.symlink_to(sentinel)
        with pytest.raises(PermissionError, match='outside the temporary profile'):
            sqlite3.connect(link)
    assert conftest._violations == (6 if os.name != 'nt' else 5)
    conftest._violations = 0


def test_caught_outside_database_attempt() -> None:
    sentinel = Path(os.environ['WORTA_ISOLATION_SENTINEL'])
    with pytest.raises(PermissionError, match='outside the temporary profile'):
        sqlite3.connect(sentinel)
