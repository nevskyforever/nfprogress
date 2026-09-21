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
    assert not {'payload', 'payload_json', 'content', 'content_json', 'ciphertext', 'blob'} & columns
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


def test_c9_upgrade_from_populated_schema_7_preserves_authoritative_data():
    connection = sqlite3.connect(':memory:')
    assert apply_migrations(connection) == 8
    connection.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('p','Project',0,'symbols','активен','{}')")
    connection.execute("INSERT INTO project_order(project_id,position) VALUES('p',0)")
    connection.execute("""INSERT INTO documents(
        id,scope_key,project_id,stage_id,title,content_json,content_format,extensions_json
    ) VALUES('d','project:p','p',NULL,'Document','{}','json','{}')""")
    connection.execute("INSERT INTO settings(key,value_json) VALUES('theme','\"dark\"')")
    connection.execute("INSERT INTO domain_events(event_id,event_type,project_id,context_json,created_at) VALUES('game-7','Game','p','{\"keep\": true}','2026-09-21T00:00:00Z')")
    connection.execute("INSERT INTO application_metadata(key,value,updated_at) VALUES('data_last_written_by_version','6.0.0','now')")
    connection.execute('DROP TABLE cloud_sync_outbox')
    connection.execute('DROP TABLE cloud_sync_state')
    connection.execute('UPDATE schema_info SET schema_version=7')
    connection.commit()

    assert apply_migrations(connection) == 8
    assert connection.execute("SELECT name FROM projects WHERE id='p'").fetchone()[0] == 'Project'
    assert connection.execute("SELECT title FROM documents WHERE id='d'").fetchone()[0] == 'Document'
    assert connection.execute("SELECT value_json FROM settings WHERE key='theme'").fetchone()[0] == '"dark"'
    assert connection.execute("SELECT context_json FROM domain_events WHERE event_id='game-7'").fetchone()[0] == '{"keep": true}'
    assert connection.execute("SELECT value FROM application_metadata WHERE key='data_last_written_by_version'").fetchone()[0] == '6.0.0'
    assert connection.execute('SELECT schema_version FROM schema_info').fetchone()[0] == 8
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'cloud_sync_state', 'cloud_sync_outbox'} <= tables
