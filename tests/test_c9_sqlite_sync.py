from __future__ import annotations

import sqlite3
import json

import pytest

from nfprogress.core.sqlite.connection import configure_application_metadata
from nfprogress.core.sqlite.schema import (
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS_DIR,
    apply_migrations,
)


UUID_1 = '123e4567-e89b-42d3-a456-426614174000'
UUID_2 = '123e4567-e89b-42d3-a456-426614174001'
UUID_3 = '123e4567-e89b-42d3-a456-426614174002'
UUID_4 = '123e4567-e89b-42d3-a456-426614174003'


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


def _create_v9_database() -> sqlite3.Connection:
    connection = _create_v8_database()
    connection.executescript(
        (MIGRATIONS_DIR / '009_encrypted_sync_substrate.sql').read_text()
    )
    connection.execute('UPDATE schema_info SET schema_version=9')
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


def test_c17_upgrade_from_v16_preserves_existing_inbox_rows():
    connection = sqlite3.connect(':memory:')
    migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))[:16]
    assert migration_files[-1].name == '016_cloud_project_bootstrap.sql'
    for migration in migration_files:
        connection.executescript(migration.read_text(encoding='utf-8'))
    connection.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    connection.execute('INSERT INTO schema_info VALUES(16)')
    _insert_inbox(connection)

    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION
    assert connection.execute(
        'SELECT event_id,state,conflict_group_id,conflict_preserved_at '
        'FROM cloud_sync_inbox'
    ).fetchone() == (UUID_1, 'received', None, None)
    assert connection.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' "
        "AND name LIKE 'cloud_sync_note_conflict_%'"
    ).fetchone()[0] == 3


def test_c17_upgrade_from_v21_preserves_conflict_inbox_and_foreign_keys():
    connection = sqlite3.connect(':memory:')
    connection.execute('PRAGMA foreign_keys = ON')
    migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))[:21]
    assert migration_files[-1].name == '021_note_sync_resolution_upload_receipts.sql'
    for migration in migration_files:
        connection.executescript(migration.read_text(encoding='utf-8'))
    connection.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    connection.execute('INSERT INTO schema_info VALUES(21)')
    connection.execute("""INSERT INTO cloud_sync_note_conflict_groups(
        group_id,account_id,project_id,entity_id,entity_type,common_parent_event_id,
        tip_revision,generation,lifecycle,created_at,updated_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
        UUID_4, 'account', 'project', 'entity', 'note', UUID_2,
        2, 1, 'open', 'now', 'now',
    ))
    connection.execute("""INSERT INTO cloud_sync_inbox(
        account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,
        operation,sync_revision,updated_at,deleted_at,state,received_at,
        conflict_group_id,conflict_preserved_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        'account', UUID_1, 1, UUID_2, 'project', 'entity', 'note', 'upsert', 2,
        '2026-09-21T00:00:00Z', None, 'conflict_preserved',
        '2026-09-21T00:00:00Z', UUID_4, '2026-09-21T00:00:01Z',
    ))
    connection.commit()

    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION
    assert connection.execute("""SELECT event_id,server_sequence,state,
        conflict_group_id,conflict_preserved_at FROM cloud_sync_inbox""").fetchone() == (
        UUID_1, 1, 'conflict_preserved', UUID_4, '2026-09-21T00:00:01Z',
    )
    assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    assert connection.execute(
        "SELECT count(*) FROM sqlite_master WHERE sql LIKE '%cloud_sync_inbox_v21%'"
    ).fetchone()[0] == 0
    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION


def test_c15_sqlite_sync_substrate_fresh_schema_is_metadata_only():
    connection = sqlite3.connect(':memory:')
    connection.execute("""CREATE TABLE domain_events (
        event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, project_id TEXT NOT NULL,
        stage_id TEXT, progress_id TEXT, effective_date TEXT, delta_symbols REAL,
        context_json TEXT NOT NULL, created_at TEXT NOT NULL, processed_at TEXT,
        consumer TEXT NOT NULL DEFAULT 'game', version INTEGER NOT NULL DEFAULT 1
    )""")
    connection.execute("INSERT INTO domain_events(event_id,event_type,project_id,context_json,created_at) VALUES ('game-1','Game','p','{\"coins\": 1}','2026-09-21T00:00:00Z')")

    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION == 22
    assert connection.execute("SELECT context_json FROM domain_events WHERE event_id='game-1'").fetchone()[0] == '{"coins": 1}'
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        'cloud_sync_state', 'cloud_sync_outbox', 'cloud_sync_event_objects',
        'cloud_sync_inbox', 'cloud_sync_entities',
        'cloud_sync_project_bindings', 'cloud_sync_note_intents',
        'cloud_sync_note_intent_cursors',
        'cloud_account_bindings',
        'cloud_sync_upload_receipts',
        'cloud_sync_project_bootstraps',
        'cloud_sync_note_conflict_groups',
        'cloud_sync_note_conflict_versions',
        'cloud_sync_note_conflict_tips',
        'cloud_sync_note_causal_history',
        'cloud_sync_note_pending_resolutions',
        'cloud_sync_note_resolution_outbox',
        'cloud_sync_note_resolution_dependencies',
        'cloud_sync_note_resolution_upload_receipts',
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


def test_c17_upgrade_from_v20_preserves_sealed_resolution_envelope_and_adds_receipts():
    connection = sqlite3.connect(':memory:')
    migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))[:20]
    assert migration_files[-1].name == '020_note_sync_resolution_sealing.sql'
    for migration in migration_files:
        connection.executescript(migration.read_text(encoding='utf-8'))
    connection.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    connection.execute('INSERT INTO schema_info VALUES(20)')
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute("""INSERT INTO cloud_sync_note_conflict_groups(
        group_id,account_id,project_id,entity_id,entity_type,common_parent_event_id,
        tip_revision,generation,lifecycle,created_at,updated_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
        UUID_4, 'account', 'project', 'entity', 'note', UUID_1, 2, 1, 'resolving', 'now', 'now',
    ))
    connection.execute("""INSERT INTO cloud_sync_note_pending_resolutions(
        resolution_event_id,account_id,device_id,project_id,entity_id,conflict_group_id,
        expected_conflict_generation,resolution_revision,tip_event_ids_json,strategy,
        result_operation,canonical_payload,lifecycle,prepared_at,updated_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        UUID_3, 'account', UUID_2, 'project', 'entity', UUID_4, 1, 2,
        json.dumps([UUID_1, UUID_2]), 'choose_version', 'upsert', b'canonical-v2',
        'consumed', 'now', 'now',
    ))
    connection.execute("""INSERT INTO cloud_sync_note_resolution_outbox(
        resolution_event_id,account_id,device_id,project_id,entity_id,clone_entity_id,
        conflict_group_id,conflict_generation,revision,parent_event_ids_json,strategy,
        result_operation,canonical_payload,lifecycle,applied_at,updated_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        UUID_3, 'account', UUID_2, 'project', 'entity', None, UUID_4, 1, 2,
        json.dumps([UUID_1, UUID_2]), 'choose_version', 'upsert', b'canonical-v2',
        'local_pending', 'now', 'now',
    ))
    connection.execute("""INSERT INTO cloud_sync_event_objects(
        account_id,event_id,crypto_version,aad_version,nonce,ciphertext,stored_at
    ) VALUES(?,?,?,?,?,?,?)""", ('account', UUID_3, 1, 1, b'n' * 24, b'c' * 16, 'now'))
    connection.execute("""UPDATE cloud_sync_note_resolution_outbox
        SET lifecycle='sealed_local' WHERE resolution_event_id=?""", (UUID_3,))
    connection.commit()

    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION
    assert connection.execute("SELECT lifecycle,canonical_payload FROM cloud_sync_note_resolution_outbox").fetchone() == ('sealed_local', b'canonical-v2')
    assert connection.execute("SELECT nonce,ciphertext FROM cloud_sync_event_objects WHERE event_id=?", (UUID_3,)).fetchone() == (b'n' * 24, b'c' * 16)
    connection.execute("""INSERT INTO cloud_sync_outbox(
        event_id,account_id,device_id,project_id,entity_id,entity_type,operation,
        revision,updated_at,deleted_at,created_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
        UUID_1, 'account', UUID_2, 'project', 'v1-note', 'note', 'upsert', 1,
        'now', None, 'now',
    ))
    # First v1, then resolution: the resolution-table trigger rejects a shared sequence.
    connection.execute("""INSERT INTO cloud_sync_upload_receipts(
        account_id,event_id,device_id,server_sequence,duplicate,accepted_at
    ) VALUES(?,?,?,?,?,?)""", ('account', UUID_1, UUID_2, 2, 0, 'now'))
    with pytest.raises(sqlite3.IntegrityError, match='note_sync_receipt_sequence_conflict'):
        connection.execute("""INSERT INTO cloud_sync_note_resolution_upload_receipts(
            account_id,resolution_event_id,device_id,server_sequence,duplicate,accepted_at
        ) VALUES(?,?,?,?,?,?)""", ('account', UUID_3, UUID_2, 2, 0, 'now'))
    connection.execute("""INSERT INTO cloud_sync_note_resolution_upload_receipts(
        account_id,resolution_event_id,device_id,server_sequence,duplicate,accepted_at
    ) VALUES(?,?,?,?,?,?)""", ('account', UUID_3, UUID_2, 1, 0, 'now'))
    connection.execute("UPDATE cloud_sync_note_resolution_outbox SET lifecycle='accepted' WHERE resolution_event_id=?", (UUID_3,))
    assert connection.execute("SELECT lifecycle FROM cloud_sync_note_resolution_outbox").fetchone()[0] == 'accepted'
    # First resolution, then v1: the v1-table trigger protects its actual write path too.
    connection.execute("""INSERT INTO cloud_sync_outbox(
        event_id, account_id, device_id, project_id, entity_id, entity_type,
        operation, revision, updated_at, deleted_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        '123e4567-e89b-42d3-a456-426614174004', 'account', UUID_2, 'project', 'v1-note-2', 'note', 'upsert',
        1, 'now', None, 'now',
    ))
    with pytest.raises(sqlite3.IntegrityError, match='note_sync_receipt_sequence_conflict'):
        connection.execute("""INSERT INTO cloud_sync_upload_receipts(
            account_id,event_id,device_id,server_sequence,duplicate,accepted_at
        ) VALUES(?,?,?,?,?,?)""", ('account', '123e4567-e89b-42d3-a456-426614174004', UUID_2, 1, 0, 'now'))


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

    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION
    assert connection.execute('SELECT schema_version FROM schema_info').fetchone()[0] == CURRENT_SCHEMA_VERSION
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


def _insert_project(connection: sqlite3.Connection, project_id: str = 'project') -> None:
    connection.execute(
        "INSERT INTO projects(id,name,infinite,unit,status,payload_json) "
        "VALUES(?, 'Project', 0, 'symbols', 'active', '{}')",
        (project_id,),
    )
    connection.execute(
        "INSERT INTO project_order(project_id,position) "
        "VALUES(?, (SELECT COUNT(*) FROM project_order))",
        (project_id,),
    )


def _note_payload(*, note_id: str = 'note', content: str = 'one') -> str:
    return '{"id":"%s","project_id":"project","stage_id":null,' \
        '"source_type":"project","source_map_id":null,"source_node_id":null,' \
        '"content_format":"html","content":"%s","updated_at":"now"}' % (
            note_id, content,
        )


def _bind_project(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) "
        "VALUES('account',?,0,0,'now','now')",
        (UUID_2,),
    )
    connection.execute(
        "INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at) "
        "VALUES('project','account','now','now')"
    )


def _insert_unsealed_event(
        connection: sqlite3.Connection, *, event_id: str = UUID_1,
        entity_id: str = 'note', operation: str = 'upsert',
        revision: int = 1, ordinal: int = 1, deleted_at: str | None = None,
) -> None:
    updated_at = deleted_at if operation == 'delete' else 'now'
    connection.execute(
        """INSERT INTO cloud_sync_outbox(
            event_id,account_id,device_id,project_id,entity_id,entity_type,
            operation,revision,updated_at,deleted_at,created_at,parent_event_id,
            local_ordinal,lifecycle
        ) VALUES(?,?,?,?,?,'note',?,?,?,?,'now',NULL,?,'unsealed')""",
        (event_id, 'account', UUID_2, 'project', entity_id, operation,
         revision, updated_at, deleted_at, ordinal),
    )


def _insert_intent(
        connection: sqlite3.Connection, snapshot: str, *, event_id: str = UUID_1,
        state: str = 'pending', error: str | None = None,
        next_attempt_at: str | None = None,
) -> None:
    connection.execute(
        """INSERT INTO cloud_sync_note_intents(
            event_id,mutation_generation,snapshot_json,seal_state,
            seal_attempt_count,last_error_code,next_attempt_at,state_updated_at
        ) VALUES(?,1,?,?,0,?,?,'now')""",
        (event_id, snapshot, state, error, next_attempt_at),
    )


def test_c154_v9_upgrade_preserves_data_without_binding_or_intent_backfill():
    connection = _create_v9_database()
    _insert_project(connection)
    payload = _note_payload()
    connection.execute(
        "INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) "
        "VALUES('note','project',NULL,'old',?)",
        (payload,),
    )
    connection.execute(
        "INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) "
        "VALUES('account',?,0,0,'created','updated')",
        (UUID_2,),
    )
    connection.execute(
        """INSERT INTO cloud_sync_outbox(
            event_id,account_id,device_id,project_id,entity_id,entity_type,
            operation,revision,updated_at,deleted_at,created_at,attempt_count,
            last_error,next_attempt_at,parent_event_id,local_ordinal,lifecycle
        ) VALUES(?,?,?,?,?,'note','upsert',7,'updated',NULL,'created',2,
                 'retry','later',NULL,0,'legacy')""",
        (UUID_1, 'account', UUID_2, 'project', 'note'),
    )
    connection.execute(
        "INSERT INTO cloud_sync_event_objects VALUES(?,?,?,?,?,?,?)",
        ('account', UUID_1, 1, 1, b'n' * 24, b'c' * 16, 'stored'),
    )
    _insert_inbox(connection, account='account', event_id=UUID_1, sequence=1)
    connection.execute(
        "INSERT INTO cloud_sync_entities VALUES(?,?,?,?,?,?,?,?,?)",
        ('account', 'project', 'note', 'note', UUID_1, 7, None, None, 'now'),
    )
    connection.commit()

    assert apply_migrations(connection) == CURRENT_SCHEMA_VERSION
    assert connection.execute("SELECT payload_json FROM notes WHERE id='note'").fetchone()[0] == payload
    assert connection.execute(
        "SELECT revision,local_ordinal,lifecycle,last_error FROM cloud_sync_outbox"
    ).fetchone() == (7, 0, 'legacy', 'retry')
    assert connection.execute('SELECT count(*) FROM cloud_sync_event_objects').fetchone()[0] == 1
    assert connection.execute('SELECT count(*) FROM cloud_sync_inbox').fetchone()[0] == 1
    assert connection.execute('SELECT count(*) FROM cloud_sync_entities').fetchone()[0] == 1
    assert connection.execute('SELECT count(*) FROM cloud_sync_project_bindings').fetchone()[0] == 0
    assert connection.execute('SELECT count(*) FROM cloud_sync_note_intents').fetchone()[0] == 0


def test_c154_project_binding_constraints():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_project(connection)
    _bind_project(connection)
    assert connection.execute(
        "SELECT project_id,account_id FROM cloud_sync_project_bindings"
    ).fetchone() == ('project', 'account')

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO cloud_sync_project_bindings VALUES('missing','account','now','now')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO cloud_sync_project_bindings VALUES('project','missing','now','now')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO cloud_sync_project_bindings VALUES('project','account','again','again')"
        )


def test_c154d2a_cloud_account_binding_is_explicit_and_immutable():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    connection.execute(
        "INSERT INTO cloud_sync_state(account_id,device_id,pull_cursor,ack_cursor,created_at,updated_at) "
        "VALUES('opaque-local-account',?,0,0,'now','now')",
        (UUID_2,),
    )
    user_id = '00000000-0000-0000-0000-000000000101'
    connection.execute(
        "INSERT INTO cloud_account_bindings VALUES(?,?,?,?)",
        ('opaque-local-account', user_id, 'now', 'now'),
    )
    assert connection.execute(
        "SELECT local_account_id,canonical_user_id FROM cloud_account_bindings"
    ).fetchone() == ('opaque-local-account', user_id)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "UPDATE cloud_account_bindings SET canonical_user_id=? WHERE local_account_id=?",
            ('00000000-0000-0000-0000-000000000102', 'opaque-local-account'),
        )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO cloud_account_bindings VALUES(?,?,?,?)",
            ('missing-account', '00000000-0000-0000-0000-000000000103', 'now', 'now'),
        )
    assert connection.execute(
        "SELECT canonical_user_id FROM cloud_account_bindings WHERE local_account_id='opaque-local-account'"
    ).fetchone()[0] == user_id


def test_c154_note_intent_constraints_and_outbox_relation():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_unsealed_event(connection)
    _insert_intent(connection, _note_payload())
    assert connection.execute(
        "SELECT mutation_generation,seal_state FROM cloud_sync_note_intents"
    ).fetchone() == (1, 'pending')

    invalid_rows = [
        (UUID_1, 0, '{}', 'pending', 0, None, None, 'now'),
        (UUID_1, 1, 'not-json', 'pending', 0, None, None, 'now'),
        (UUID_1, 1, '[]', 'pending', 0, None, None, 'now'),
        (UUID_1, 1, '{}', 'pending', 0, 'error', None, 'now'),
        (UUID_1, 1, '{}', 'blocked', 0, None, None, 'now'),
        (UUID_1, 1, '{}', 'invariant_error', 0, 'broken', 'later', 'now'),
    ]
    connection.execute('DELETE FROM cloud_sync_note_intents')
    for row in invalid_rows:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO cloud_sync_note_intents VALUES(?,?,?,?,?,?,?,?)", row
            )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO cloud_sync_note_intents VALUES(?,1,'{}','pending',0,NULL,NULL,'now')",
            ('123e4567-e89b-42d3-a456-426614174099',),
        )


def test_c154_note_intent_requires_matching_unsealed_note_event():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_unsealed_event(connection, operation='delete', deleted_at='deleted')
    incomplete_tombstone = (
        '{"id":"note","project_id":"project","source_type":"project",'
        '"content_format":"html","deleted_at":"deleted"}'
    )
    with pytest.raises(sqlite3.IntegrityError, match='requires_unsealed_note_event'):
        _insert_intent(connection, incomplete_tombstone)

    connection.execute("UPDATE cloud_sync_outbox SET operation='event', deleted_at=NULL")
    with pytest.raises(sqlite3.IntegrityError, match='requires_unsealed_note_event'):
        _insert_intent(connection, _note_payload())

    connection.execute("UPDATE cloud_sync_outbox SET operation='upsert'")
    connection.execute("UPDATE cloud_sync_outbox SET entity_type='document'")
    with pytest.raises(sqlite3.IntegrityError, match='requires_unsealed_note_event'):
        _insert_intent(connection, _note_payload())


def test_c154_partial_uniqueness_enforces_nonlegacy_event_chains():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_unsealed_event(connection)

    with pytest.raises(sqlite3.IntegrityError):
        _insert_unsealed_event(
            connection,
            event_id=UUID_2,
            revision=2,
            ordinal=2,
        )

    connection.execute(
        "UPDATE cloud_sync_outbox SET lifecycle='sealed' WHERE event_id=?",
        (UUID_1,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        _insert_unsealed_event(
            connection,
            event_id=UUID_2,
            revision=1,
            ordinal=2,
        )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """INSERT INTO cloud_sync_outbox(
                event_id,account_id,device_id,project_id,entity_id,entity_type,
                operation,revision,updated_at,created_at,local_ordinal,lifecycle
            ) VALUES(?,'account',?,'project','other','note','upsert',1,
                'now','now',1,'sealed')""",
            (UUID_2, UUID_2),
        )

    # Pre-C15.4 compatibility rows retain their original permissive semantics.
    for event_id in (
        '123e4567-e89b-42d3-a456-426614174097',
        '123e4567-e89b-42d3-a456-426614174098',
    ):
        connection.execute(
            """INSERT INTO cloud_sync_outbox(
                event_id,account_id,device_id,project_id,entity_id,entity_type,
                operation,revision,updated_at,created_at
            ) VALUES(?,'account',?,'legacy-project','legacy-note','note',
                'upsert',1,'now','now')""",
            (event_id, UUID_2),
        )


def test_c154_local_only_note_crud_remains_unguarded():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_project(connection)
    first = _note_payload(content='one')
    second = _note_payload(content='two')
    connection.execute(
        "INSERT INTO notes VALUES('note','project',NULL,'now',?)", (first,)
    )
    connection.execute(
        "UPDATE notes SET payload_json=? WHERE id='note'", (second,)
    )
    connection.execute("DELETE FROM notes WHERE id='note'")
    assert connection.execute("SELECT count(*) FROM notes").fetchone()[0] == 0


def test_c154_bound_note_crud_fails_without_matching_intent():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_project(connection)
    original = _note_payload(content='one')
    connection.execute(
        "INSERT INTO notes VALUES('note','project',NULL,'now',?)", (original,)
    )
    _bind_project(connection)

    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute(
            "INSERT INTO notes VALUES('other','project',NULL,'now',?)",
            (_note_payload(note_id='other'),),
        )
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute(
            "UPDATE notes SET payload_json=? WHERE id='note'",
            (_note_payload(content='two'),),
        )
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute("DELETE FROM notes WHERE id='note'")


def test_c154_bound_upsert_requires_exact_entity_operation_and_snapshot():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_project(connection)
    _bind_project(connection)
    expected = _note_payload(content='expected')
    _insert_unsealed_event(connection, entity_id='other')
    _insert_intent(connection, _note_payload(note_id='other'))
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute(
            "INSERT INTO notes VALUES('note','project',NULL,'now',?)", (expected,)
        )

    connection.execute('DELETE FROM cloud_sync_outbox')
    _insert_unsealed_event(connection, operation='delete', deleted_at='now')
    tombstone = ('{"id":"note","project_id":"project","stage_id":null,'
                 '"source_type":"project","source_map_id":null,'
                 '"source_node_id":null,"content_format":"html",'
                 '"deleted_at":"now"}')
    _insert_intent(connection, tombstone)
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute(
            "INSERT INTO notes VALUES('note','project',NULL,'now',?)", (expected,)
        )

    connection.execute('DELETE FROM cloud_sync_outbox')
    _insert_unsealed_event(connection)
    _insert_intent(connection, _note_payload(content='stale'))
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute(
            "INSERT INTO notes VALUES('note','project',NULL,'now',?)", (expected,)
        )

    connection.execute(
        "UPDATE cloud_sync_note_intents SET snapshot_json=? WHERE event_id=?",
        (expected, UUID_1),
    )
    connection.execute(
        "INSERT INTO notes VALUES('note','project',NULL,'now',?)", (expected,)
    )
    assert connection.execute("SELECT payload_json FROM notes").fetchone()[0] == expected
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute("UPDATE notes SET updated_at='other' WHERE id='note'")


def test_c154_bound_delete_requires_matching_tombstone_route():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_project(connection)
    original = _note_payload()
    connection.execute(
        "INSERT INTO notes VALUES('note','project',NULL,'now',?)", (original,)
    )
    _bind_project(connection)
    _insert_unsealed_event(
        connection,
        entity_id='other',
        operation='delete',
        deleted_at='deleted',
    )
    wrong = ('{"id":"other","project_id":"project","stage_id":null,'
             '"source_type":"project","source_map_id":null,"source_node_id":null,'
             '"content_format":"html","deleted_at":"deleted"}')
    _insert_intent(connection, wrong)
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute("DELETE FROM notes WHERE id='note'")

    connection.execute('DELETE FROM cloud_sync_outbox')
    _insert_unsealed_event(connection, operation='delete', deleted_at='deleted')
    tombstone = ('{"id":"note","project_id":"project","stage_id":null,'
                 '"source_type":"project","source_map_id":null,"source_node_id":null,'
                 '"content_format":"html","deleted_at":"deleted"}')
    _insert_intent(connection, tombstone)
    connection.execute("DELETE FROM notes WHERE id='note'")
    assert connection.execute("SELECT count(*) FROM notes").fetchone()[0] == 0


@pytest.mark.parametrize(('field', 'value'), [
    ('stage_id', 'stage'), ('source_type', 'mindmap'), ('source_map_id', 'map'),
    ('source_node_id', 'node'), ('content_format', 'text'),
])
def test_c157b_delete_tombstone_route_mismatch_is_rejected(field: str, value: str):
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection)
    _insert_project(connection)
    original = _note_payload()
    connection.execute("INSERT INTO notes VALUES('note','project',NULL,'now',?)", (original,))
    _bind_project(connection)
    _insert_unsealed_event(connection, operation='delete', deleted_at='deleted')
    tombstone = {'id': 'note', 'project_id': 'project', 'stage_id': None,
                 'source_type': 'project', 'source_map_id': None, 'source_node_id': None,
                 'content_format': 'html', 'deleted_at': 'deleted'}
    tombstone[field] = value
    _insert_intent(connection, json.dumps(tombstone, separators=(',', ':')))
    with pytest.raises(sqlite3.IntegrityError, match='matching_sync_intent'):
        connection.execute("DELETE FROM notes WHERE id='note'")
    assert connection.execute("SELECT payload_json FROM notes WHERE id='note'").fetchone()[0] == original


def test_c157b_delete_deleted_at_mismatch_is_rejected_by_intent_validator():
    connection = sqlite3.connect(':memory:')
    apply_migrations(connection); _insert_project(connection); _bind_project(connection)
    _insert_unsealed_event(connection, operation='delete', deleted_at='deleted')
    bad = ('{"id":"note","project_id":"project","stage_id":null,"source_type":"project",'
           '"source_map_id":null,"source_node_id":null,"content_format":"html","deleted_at":"other"}')
    with pytest.raises(sqlite3.IntegrityError, match='requires_unsealed'):
        _insert_intent(connection, bad)
