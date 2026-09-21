from __future__ import annotations

import sqlite3

from nfprogress.core.sqlite.connection import configure_application_metadata
from nfprogress.core.sqlite.schema import (
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS_DIR,
    apply_migrations,
)


UUID_1 = '123e4567-e89b-42d3-a456-426614174000'
UUID_2 = '123e4567-e89b-42d3-a456-426614174001'


def _create_v8_database() -> sqlite3.Connection:
    connection = sqlite3.connect(':memory:')
    for version in range(1, 9):
        filenames = {
            1: '001_initial.sql', 2: '002_storage_ownership.sql',
            3: '003_project_order.sql', 4: '004_projects_authority.sql',
            5: '005_game_authority.sql', 6: '006_documents_authority.sql',
            7: '007_application_metadata.sql', 8: '008_cloud_sync_protocol.sql',
        }
        connection.executescript((MIGRATIONS_DIR / filenames[version]).read_text())
    connection.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    connection.execute('INSERT INTO schema_info VALUES(8)')
    return connection


def _insert_inbox(connection: sqlite3.Connection, *, account: str = 'account',
                  event_id: str = UUID_1, sequence: int = 1,
                  operation: str = 'upsert', deleted_at: str | None = None,
                  state: str = 'received') -> None:
    connection.execute("""INSERT INTO cloud_sync_inbox(
        account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,
        operation,sync_revision,updated_at,deleted_at,state,received_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        account, event_id, sequence, UUID_2, 'project', 'entity', 'note', operation,
        1, '2026-09-21T00:00:00Z', deleted_at, state, '2026-09-21T00:00:00Z',
    ))


def test_c15_sqlite_sync_substrate_fresh_schema_is_metadata_only():
    connection = sqlite3.connect(':memory:')
    connection.execute("""CREATE TABLE domain_events (
        event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, project_id TEXT NOT NULL,
        stage_id TEXT, progress_id TEXT, effective_date TEXT, delta_symbols REAL,
        context_json TEXT NOT NULL, created_at TEXT NOT NULL, processed_at TEXT,
        consumer TEXT NOT NULL DEFAULT 'game', version INTEGER NOT NULL DEFAULT 1
    )""")
    connection.execute("INSERT INTO domain_events(event_id,event_type,project_id,context_json,created_at) VALUES ('game-1','Game','p','{\"coins\": 1}','2026-09-21T00:00:00Z')")

    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION == 9
    assert connection.execute("SELECT context_json FROM domain_events WHERE event_id='game-1'").fetchone()[0] == '{"coins": 1}'
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        'cloud_sync_state', 'cloud_sync_outbox', 'cloud_sync_event_objects',
        'cloud_sync_inbox', 'cloud_sync_entities',
    } <= tables
    columns = {row[1] for row in connection.execute('PRAGMA table_info(cloud_sync_outbox)')}
    assert not {
        'payload', 'payload_json', 'content', 'content_json', 'plaintext',
        'plaintext_hash', 'ciphertext', 'nonce', 'blob',
    } & columns
    assert {'parent_event_id', 'local_ordinal', 'lifecycle'} <= columns

    # A C9 writer that omits C15 compatibility columns still inserts safely.
    connection.execute("""INSERT INTO cloud_sync_outbox(
        event_id, account_id, device_id, project_id, entity_id, entity_type,
        operation, revision, updated_at, deleted_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        UUID_1, 'account', UUID_2, 'project', 'deleted-note', 'note', 'delete',
        1, '2026-09-21T00:00:00Z', '2026-09-21T00:00:00Z', '2026-09-21T00:00:00Z',
    ))
    assert connection.execute("SELECT parent_event_id,local_ordinal,lifecycle FROM cloud_sync_outbox").fetchone() == (None, 0, 'legacy')


def test_c15_upgrade_from_populated_v8_preserves_authoritative_data():
    connection = _create_v8_database()
    connection.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('p','Project',0,'symbols','активен','{}')")
    connection.execute("INSERT INTO project_order(project_id,position) VALUES('p',0)")
    connection.execute("INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES('n','p',NULL,'old','{\"revision\": 7}')")
    connection.execute("""INSERT INTO documents(id,scope_key,project_id,stage_id,title,content_json,content_format,extensions_json)
        VALUES('d','project:p','p',NULL,'Document','{}','json','{}')""")
    connection.execute("INSERT INTO settings(key,value_json) VALUES('theme','\"dark\"')")
    connection.execute("INSERT INTO application_metadata(key,value,updated_at) VALUES('data_last_written_by_version','6.0.0','now')")
    connection.execute("INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) VALUES('account',?,0,0,'created','updated')", (UUID_2,))
    connection.execute("""INSERT INTO cloud_sync_outbox(event_id,account_id,device_id,project_id,entity_id,entity_type,operation,revision,updated_at,deleted_at,created_at,attempt_count,last_error,next_attempt_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (UUID_1, 'account', UUID_2, 'p', 'n', 'note', 'upsert', 7, 'updated', None, 'created', 2, 'retry', 'later'))
    connection.commit()

    assert apply_migrations(connection) == 9
    assert connection.execute('SELECT schema_version FROM schema_info').fetchone()[0] == 9
    assert connection.execute("SELECT payload_json FROM notes WHERE id='n'").fetchone()[0] == '{"revision": 7}'
    assert connection.execute("SELECT title FROM documents WHERE id='d'").fetchone()[0] == 'Document'
    assert connection.execute("SELECT value_json FROM settings WHERE key='theme'").fetchone()[0] == '"dark"'
    assert connection.execute("SELECT value FROM application_metadata WHERE key='data_last_written_by_version'").fetchone()[0] == '6.0.0'
    assert connection.execute("""SELECT event_id,account_id,device_id,project_id,entity_id,entity_type,operation,revision,updated_at,deleted_at,created_at,attempt_count,last_error,next_attempt_at,parent_event_id,local_ordinal,lifecycle
        FROM cloud_sync_outbox""").fetchone() == (UUID_1, 'account', UUID_2, 'p', 'n', 'note', 'upsert', 7, 'updated', None, 'created', 2, 'retry', 'later', None, 0, 'legacy')
    assert connection.execute('SELECT count(*) FROM cloud_sync_event_objects').fetchone()[0] == 0
    assert connection.execute('SELECT count(*) FROM cloud_sync_inbox').fetchone()[0] == 0
    assert connection.execute('SELECT count(*) FROM cloud_sync_entities').fetchone()[0] == 0


def test_c15_event_object_requires_binary_xchacha_shape():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    insert = "INSERT INTO cloud_sync_event_objects VALUES(?,?,?,?,?,?,?)"
    connection.execute(insert, ('account', UUID_1, 1, 1, b'n' * 24, b'c' * 16, 'now'))
    for event_id, nonce, ciphertext in [
        (UUID_2, b'n' * 23, b'c' * 16),
        ('123e4567-e89b-42d3-a456-426614174002', b'n' * 25, b'c' * 16),
        ('123e4567-e89b-42d3-a456-426614174003', 'not-a-blob', b'c' * 16),
        ('123e4567-e89b-42d3-a456-426614174004', b'n' * 24, b'c' * 15),
        ('123e4567-e89b-42d3-a456-426614174005', b'n' * 24, 'not-a-blob'),
    ]:
        try:
            connection.execute(insert, ('account', event_id, 1, 1, nonce, ciphertext, 'now'))
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError('invalid encrypted object was accepted')


def test_c15_inbox_and_entity_head_constraints_allow_opaque_metadata():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_inbox(connection)
    for kwargs in [
        {'event_id': UUID_1, 'sequence': 2}, {'event_id': UUID_2, 'sequence': 1},
        {'event_id': '123e4567-e89b-42d3-a456-426614174006', 'sequence': 5,
         'operation': 'delete', 'deleted_at': None},
        {'event_id': UUID_2, 'sequence': 3, 'operation': 'upsert', 'deleted_at': 'deleted'},
        {'event_id': UUID_2, 'sequence': 4, 'state': 'invalid'},
    ]:
        try:
            _insert_inbox(connection, **kwargs)
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError('invalid inbox row was accepted')
    _insert_inbox(connection, account='other', event_id=UUID_1, sequence=1, state='applied')
    for index, state in enumerate(('received', 'unknown_entity', 'orphan', 'conflict', 'rejected'), start=10):
        _insert_inbox(connection, event_id=f'123e4567-e89b-42d3-a456-426614174{index:03d}', sequence=index, state=state)
    assert connection.execute('SELECT count(*) FROM cloud_sync_event_objects').fetchone()[0] == 0

    entity = "INSERT INTO cloud_sync_entities VALUES(?,?,?,?,?,?,?,?,?)"
    connection.execute(entity, ('account', 'project', 'entity', 'note', UUID_1, 1, None, None, 'now'))
    connection.execute(entity, ('other', 'project', 'entity', 'note', UUID_1, 1, None, None, 'now'))
    for values in [
        ('account', '', 'other', 'note', UUID_1, 1, None, None, 'now'),
        ('account', 'project', 'other', 'note', UUID_1, 0, None, None, 'now'),
        ('account', 'project', 'other', 'note', UUID_1, 1, UUID_2, None, 'now'),
        ('account', 'project', 'other', 'note', UUID_1, 1, None, 'conflict', 'now'),
    ]:
        try:
            connection.execute(entity, values)
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError('invalid entity head was accepted')


def test_c15_durable_table_writes_track_application_version(tmp_path):
    from nfprogress.core.sqlite.connection import open_database

    with open_database(tmp_path) as connection:
        configure_application_metadata(connection, application_version='9.8.7-test.1', new_database=False)
        connection.execute("INSERT INTO cloud_sync_event_objects VALUES(?,?,?,?,?,?,?)", ('account', UUID_1, 1, 1, b'n' * 24, b'c' * 16, 'now'))
        _insert_inbox(connection)
        connection.execute("INSERT INTO cloud_sync_entities VALUES(?,?,?,?,?,?,?,?,?)", ('account', 'project', 'entity', 'note', UUID_1, 1, None, None, 'now'))
        connection.commit()
        assert connection.execute("SELECT value FROM application_metadata WHERE key='data_last_written_by_version'").fetchone()[0] == '9.8.7-test.1'
