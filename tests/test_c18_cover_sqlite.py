"""Forward-only cover support migration; existing portable authority is retained."""
import sqlite3
import pytest
from nfprogress.core.sqlite.schema import apply_migrations, MIGRATIONS_DIR


@pytest.mark.parametrize('version', range(38))
def test_cover_every_prefix_and_reopen(version, tmp_path):
    path = tmp_path / 'cover.db'
    db = sqlite3.connect(path)
    db.create_function('note_sync_remote_apply_authorized', 1, lambda _: 0)
    db.execute("CREATE TABLE domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,project_id TEXT NOT NULL,stage_id TEXT,progress_id TEXT,effective_date TEXT,delta_symbols REAL,context_json TEXT NOT NULL,created_at TEXT NOT NULL,processed_at TEXT,consumer TEXT NOT NULL DEFAULT 'game',version INTEGER NOT NULL DEFAULT 1)")
    for migration in sorted(MIGRATIONS_DIR.glob('*.sql'))[:version]:
        db.executescript(migration.read_text())
    db.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    db.execute('INSERT INTO schema_info VALUES(?)', (version,))
    db.commit()
    existing = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='schema_info'")]
    before = {t: db.execute(f'SELECT * FROM "{t}"').fetchall() for t in existing}
    assert apply_migrations(db) == 38
    for table, rows in before.items():
        assert db.execute(f'SELECT * FROM "{table}"').fetchall() == rows
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    assert db.execute('SELECT count(*) FROM cloud_cover_intents').fetchone() == (0,)
    db.close()
    with sqlite3.connect(path) as reopened:
        assert apply_migrations(reopened) == 38
        assert reopened.execute('PRAGMA foreign_key_check').fetchall() == []


def test_cover_material_write_once_and_verified_monotonic(tmp_path):
    db = sqlite3.connect(tmp_path / 'material.db')
    apply_migrations(db)
    db.execute("INSERT INTO cloud_sync_state VALUES('a','123e4567-e89b-42d3-a456-426614174001',0,0,'now','now')")
    db.execute("INSERT INTO cloud_cover_material VALUES('a','P','X','{}',?,?,?,0)",
               (b'n' * 24, b'c' * 20, b'\xff\xd8\xff\xd9'))
    db.execute("UPDATE cloud_cover_material SET remote_verified=1")
    for statement in ("UPDATE cloud_cover_material SET remote_verified=0",
                      "UPDATE cloud_cover_material SET jpeg=x'ffd800d9'",
                      "UPDATE cloud_cover_material SET reference_json='null'",
                      "DELETE FROM cloud_cover_material"):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(statement)
    db.commit(); db.close()
    with sqlite3.connect(tmp_path / 'material.db') as reopened:
        assert reopened.execute('SELECT remote_verified,jpeg FROM cloud_cover_material').fetchone() == (1,b'\xff\xd8\xff\xd9')


def test_cover_populated37_retains_all_entity_inboxes_and_local_sources(tmp_path,monkeypatch):
    import nfprogress.core.sqlite.schema as schema
    path=tmp_path/'populated37.db';db=sqlite3.connect(path)
    with monkeypatch.context() as patch:
        patch.setattr(schema,'CURRENT_SCHEMA_VERSION',37)
        assert apply_migrations(db)==37
    db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('P','Local',1,'symbols','active','{\"cover_image\":\"data:image/jpeg;base64,retained-source\",\"local_path\":\"/local-only/book.docx\"}')")
    db.execute("INSERT INTO project_order VALUES('P',0)")
    db.execute("INSERT INTO stages(id,project_id,name,infinite,unit,status,payload_json) VALUES('S','P','Stage',1,'symbols','active','{}')")
    db.execute("INSERT INTO stage_order VALUES('S','P',0)")
    db.execute("INSERT INTO notes(id,project_id,stage_id,updated_at,payload_json) VALUES('N','P','S','now','{\"content\":\"retained\"}')")
    device='123e4567-e89b-42d3-a456-426614174001'
    db.execute("INSERT INTO cloud_sync_state VALUES('a',?,9,0,'now','now')",(device,))
    for sequence,kind in enumerate(('project_metadata','stage','note','map','document','progress','project_game'),1):
        event=f'123e4567-e89b-42d3-a456-{sequence+100:012}'
        db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,state,received_at) VALUES('a',?,?,?,'P',?,?,'upsert',1,'now','received','now')",(event,sequence,device,kind,kind))
        db.execute("INSERT INTO cloud_sync_event_objects VALUES('a',?,1,1,?,?,'now')",(event,b'n'*24,b'c'*32))
    for sequence,kind in ((8,'folder'),(9,'account_game')):
        event=f'123e4567-e89b-42d3-a456-{sequence+100:012}'
        db.execute("INSERT INTO cloud_sync_account_inbox(account_id,event_id,canonical_user_id,scope,server_sequence,device_id,entity_id,entity_type,operation,sync_revision,updated_at,deleted_at,crypto_version,aad_version,nonce,ciphertext,state,error_code,received_at) VALUES('a',?,'123e4567-e89b-42d3-a456-426614174099','account',?,?,?,?,'upsert',1,'now',NULL,2,2,?,?,'blocked','account_entity_codec_not_activated','now')",(event,sequence,device,kind,kind,b'n'*24,b'c'*32))
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='schema_info'")]
    before={t:db.execute(f'SELECT * FROM "{t}"').fetchall() for t in tables}
    db.commit();assert apply_migrations(db)==38;db.close()
    with sqlite3.connect(path) as reopened:
        assert apply_migrations(reopened)==38
        for table,rows in before.items():
            assert reopened.execute(f'SELECT * FROM "{table}"').fetchall()==rows
        assert reopened.execute('PRAGMA foreign_key_check').fetchall()==[]
