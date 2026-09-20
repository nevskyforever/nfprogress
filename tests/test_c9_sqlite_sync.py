from __future__ import annotations

import sqlite3

from nfprogress.core.sqlite.schema import CURRENT_SCHEMA_VERSION, apply_migrations


def test_c9_sqlite_sync_migration_is_metadata_only_and_preserves_domain_events():
    connection = sqlite3.connect(':memory:')
    connection.execute("""CREATE TABLE domain_events (
        event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, project_id TEXT NOT NULL,
        stage_id TEXT, progress_id TEXT, effective_date TEXT, delta_symbols REAL,
        context_json TEXT NOT NULL, created_at TEXT NOT NULL, processed_at TEXT,
        consumer TEXT NOT NULL DEFAULT 'game', version INTEGER NOT NULL DEFAULT 1
    )""")
    connection.execute("INSERT INTO domain_events(event_id,event_type,project_id,context_json,created_at) VALUES ('game-1','Game','p','{\"coins\": 1}','2026-09-21T00:00:00Z')")
    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION == 8
    assert connection.execute("SELECT context_json FROM domain_events WHERE event_id='game-1'").fetchone()[0] == '{"coins": 1}'
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'cloud_sync_state', 'cloud_sync_outbox'} <= tables
    columns = {row[1] for row in connection.execute('PRAGMA table_info(cloud_sync_outbox)')}
    assert not {'payload', 'content', 'ciphertext'} & columns
    connection.execute("""INSERT INTO cloud_sync_outbox(
        event_id, account_id, device_id, project_id, entity_id, entity_type,
        operation, revision, updated_at, deleted_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        '123e4567-e89b-42d3-a456-426614174000', 'account',
        '123e4567-e89b-42d3-a456-426614174001', 'project', 'deleted-note', 'note',
        'delete', 1, '2026-09-21T00:00:00Z', '2026-09-21T00:00:00Z', '2026-09-21T00:00:00Z',
    ))
    connection.commit()
    assert connection.execute('SELECT count(*) FROM cloud_sync_outbox').fetchone()[0] == 1
    assert apply_migrations(connection) == 8
