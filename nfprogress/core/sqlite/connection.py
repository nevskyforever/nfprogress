"""SQLite connection helpers for the shadow mirror."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from nfprogress.core.sqlite.schema import apply_migrations


def database_path(data_root: str | Path) -> Path:
    return Path(data_root).expanduser().resolve() / 'nfprogress.db'


def open_database(data_root: str | Path) -> sqlite3.Connection:
    path = database_path(data_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        apply_migrations(connection)
    except Exception:
        connection.close()
        raise
    return connection
