"""Versioned SQLite schema and migration runner."""

from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).with_name('migrations')
CURRENT_SCHEMA_VERSION = 4


def apply_migrations(connection: sqlite3.Connection) -> int:
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute(
        'CREATE TABLE IF NOT EXISTS schema_info '
        '(schema_version INTEGER NOT NULL)',
    )
    rows = connection.execute(
        'SELECT schema_version FROM schema_info',
    ).fetchall()
    if len(rows) > 1:
        raise RuntimeError('schema_info contains more than one schema version')
    version = int(rows[0][0]) if rows else 0
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f'unsupported future SQLite schema version: {version}')
    for next_version in range(version + 1, CURRENT_SCHEMA_VERSION + 1):
        migration = MIGRATIONS_DIR / {
            1: '001_initial.sql',
            2: '002_storage_ownership.sql',
            3: '003_project_order.sql',
            4: '004_projects_authority.sql',
        }[next_version]
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
    connection.execute(
        'CREATE TABLE IF NOT EXISTS domain_events ('
        'event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, '
        'project_id TEXT NOT NULL, '
        'stage_id TEXT, progress_id TEXT, effective_date TEXT, '
        'delta_symbols REAL, context_json TEXT NOT NULL, created_at TEXT NOT NULL, '
        'processed_at TEXT, consumer TEXT NOT NULL DEFAULT \'game\', '
        'version INTEGER NOT NULL DEFAULT 1)'
    )
    connection.execute(
        'CREATE INDEX IF NOT EXISTS idx_domain_events_pending '
        'ON domain_events(consumer, processed_at, created_at)'
    )
    return CURRENT_SCHEMA_VERSION
