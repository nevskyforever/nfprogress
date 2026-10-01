from __future__ import annotations

import sqlite3
import pytest

from nfprogress.core.sqlite.schema import CURRENT_SCHEMA_VERSION, MIGRATIONS_DIR, apply_migrations


def _database(version: int) -> sqlite3.Connection:
    db = sqlite3.connect(':memory:')
    db.execute('PRAGMA foreign_keys=ON')
    db.create_function('note_sync_remote_apply_authorized', 1, lambda _capability: 0)
    db.execute('CREATE TABLE domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,project_id TEXT NOT NULL,stage_id TEXT,progress_id TEXT,effective_date TEXT,delta_symbols REAL,context_json TEXT NOT NULL,created_at TEXT NOT NULL,processed_at TEXT,consumer TEXT NOT NULL DEFAULT \'game\',version INTEGER NOT NULL DEFAULT 1)')
    for path in sorted(MIGRATIONS_DIR.glob('*.sql'))[:version]:
        db.executescript(path.read_text(encoding='utf-8'))
    db.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    db.execute('INSERT INTO schema_info VALUES(?)',(version,))
    return db


def test_c18_metadata_fresh_schema_and_immutable_candidate():
    db = _database(0)
    assert apply_migrations(db) == CURRENT_SCHEMA_VERSION == 27
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'cloud_sync_metadata_candidates','cloud_sync_metadata_events',
            'cloud_sync_metadata_tips','cloud_sync_metadata_projection',
            'cloud_sync_metadata_apply_ledger', 'cloud_sync_metadata_reconciliation'} <= tables
    assert apply_migrations(db) == 27
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_c18_metadata_populated_v24_upgrade_preserves_note_and_blocks_bad_event():
    db = _database(24)
    db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('project','Local',1,'symbols','active','{}')")
    db.execute("INSERT INTO project_order(project_id,position) VALUES('project',0)")
    db.execute("INSERT INTO notes(id,project_id,payload_json) VALUES('note','project','{}')")
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('account','123e4567-e89b-42d3-a456-426614174001','now','now')")
    db.execute("INSERT INTO cloud_sync_project_bindings(project_id,account_id,created_at,updated_at) VALUES('project','account','now','now')")
    db.commit()
    assert apply_migrations(db) == 27
    assert db.execute("SELECT id,project_id,payload_json FROM notes").fetchone() == ('note','project','{}')
    assert db.execute("SELECT COUNT(*) FROM cloud_sync_metadata_candidates").fetchone()[0] == 0
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO cloud_sync_metadata_events(account_id,event_id,project_id,device_id,bootstrap_id,parent_event_ids_json,generation,revision,operation,payload_json,state,created_at) VALUES('account','123e4567-e89b-42d3-a456-426614174010','project','123e4567-e89b-42d3-a456-426614174001','123e4567-e89b-42d3-a456-426614174002','[]',1,2,'create','{}','received','now')")
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    assert apply_migrations(db) == 27


def test_metadata_import_v26_upgrade_keeps_forward_cursor_and_immutable_progress():
    db = _database(26)
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('account','123e4567-e89b-42d3-a456-426614174001','now','now')")
    db.commit()
    assert apply_migrations(db) == 27
    db.execute("INSERT INTO cloud_sync_metadata_imports(account_id,project_id,bootstrap_id,cursor) VALUES('account','not-yet-imported','bootstrap',16)")
    assert db.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 0
    db.execute("INSERT INTO cloud_sync_metadata_import_pages VALUES('account','not-yet-imported',0,16,?,1)", ('a' * 64,))
    db.execute("INSERT INTO cloud_sync_metadata_import_events VALUES('account','not-yet-imported','event',1,?)", (b'{}',))
    for sql in (
        "UPDATE cloud_sync_metadata_imports SET cursor=15",
        "UPDATE cloud_sync_metadata_imports SET bootstrap_id='replacement'",
        "UPDATE cloud_sync_metadata_import_pages SET next_cursor=17",
        "DELETE FROM cloud_sync_metadata_import_pages",
        "UPDATE cloud_sync_metadata_import_events SET canonical_payload=x'00'",
        "DELETE FROM cloud_sync_metadata_import_events",
        "UPDATE cloud_sync_metadata_imports SET event_count=3201",
        "UPDATE cloud_sync_metadata_imports SET payload_bytes=16777217",
    ):
        with pytest.raises(sqlite3.IntegrityError): db.execute(sql)
    db.commit()
    assert db.execute('SELECT cursor FROM cloud_sync_metadata_imports').fetchone()[0] == 16
    assert apply_migrations(db) == 27
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
