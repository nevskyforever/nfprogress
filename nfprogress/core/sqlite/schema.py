"""Versioned SQLite schema and migration runner."""

from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).with_name('migrations')
CURRENT_SCHEMA_VERSION = 2


def apply_migrations(connection: sqlite3.Connection) -> int:
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute(
        'CREATE TABLE IF NOT EXISTS schema_info '
        '(schema_version INTEGER NOT NULL)',
    )
    row = connection.execute(
        'SELECT schema_version FROM schema_info LIMIT 1',
    ).fetchone()
    version = int(row[0]) if row else 0
    for next_version in range(version + 1, CURRENT_SCHEMA_VERSION + 1):
        migration = MIGRATIONS_DIR / (
            '001_initial.sql' if next_version == 1 else f'{next_version:03d}_storage_ownership.sql'
        )
        sql = migration.read_text(encoding='utf-8')
        # executescript is wrapped explicitly because its implicit transaction
        # handling otherwise commits before running the script.
        connection.executescript(
            'BEGIN;\n'
            f'{sql}\n'
            'DELETE FROM schema_info;\n'
            f'INSERT INTO schema_info(schema_version) VALUES ({next_version});\n'
            'COMMIT;\n',
        )
    return CURRENT_SCHEMA_VERSION
