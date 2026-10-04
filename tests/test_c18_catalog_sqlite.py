"""Forward-only schema31 preserves local catalog and immutable account history."""
import sqlite3
import pytest
from nfprogress.core.sqlite.schema import apply_migrations,CURRENT_SCHEMA_VERSION,MIGRATIONS_DIR

@pytest.mark.parametrize('version',range(32))
def test_catalog_all_supported_prefixes_upgrade(version):
    db=sqlite3.connect(':memory:');db.create_function('note_sync_remote_apply_authorized',1,lambda _:0)
    db.execute("CREATE TABLE domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,project_id TEXT NOT NULL,stage_id TEXT,progress_id TEXT,effective_date TEXT,delta_symbols REAL,context_json TEXT NOT NULL,created_at TEXT NOT NULL,processed_at TEXT,consumer TEXT NOT NULL DEFAULT 'game',version INTEGER NOT NULL DEFAULT 1)")
    for path in sorted(MIGRATIONS_DIR.glob('*.sql'))[:version]:db.executescript(path.read_text())
    db.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)');db.execute('INSERT INTO schema_info VALUES(?)',(version,));db.commit()
    assert apply_migrations(db)==CURRENT_SCHEMA_VERSION==37
    assert apply_migrations(db)==37
    assert db.execute('SELECT count(*) FROM cloud_catalog_events').fetchone()==(0,)
    db.close()


def test_catalog_populated_30_lossless_and_immutable(tmp_path,monkeypatch):
    import nfprogress.core.sqlite.schema as schema
    path=tmp_path/'native.db';db=sqlite3.connect(path)
    with monkeypatch.context() as m:
        m.setattr(schema,'CURRENT_SCHEMA_VERSION',30);apply_migrations(db)
    db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('L','Local',1,'symbols','active','{}')")
    db.execute("INSERT INTO project_order VALUES('L',0)");db.execute("INSERT INTO project_folders VALUES('F','Work',0,'{\"id\":\"F\",\"name\":\"Work\"}')")
    db.execute("INSERT INTO project_folder_members VALUES('L','F')")
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('a','123e4567-e89b-42d3-a456-426614174001','now','now')")
    before={t:db.execute(f'SELECT * FROM {t}').fetchall() for t in ('project_folders','project_folder_members','project_order')};db.commit()
    assert apply_migrations(db)==37
    for t,rows in before.items():assert db.execute(f'SELECT * FROM {t}').fetchall()==rows
    db.execute("INSERT INTO cloud_catalog_state VALUES('a','captured','{}','{}',NULL,'now')")
    db.execute("INSERT INTO cloud_catalog_events(account_id,event_id,entity_type,entity_id,canonical_frame,state) VALUES('a','event','folder','F',?,'unsealed')",(b'x'*20,))
    with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE cloud_catalog_events SET canonical_frame=?",(b'y'*20,))
    db.execute("UPDATE cloud_catalog_events SET state='sealed',nonce=?,ciphertext=?",(b'n'*24,b'c'*36))
    with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE cloud_catalog_events SET nonce=?",(b'z'*24,))
    with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE cloud_catalog_state SET snapshot_json='[]'")
    db.commit();db.close();db=sqlite3.connect(path);assert apply_migrations(db)==37
    for t,rows in before.items():assert db.execute(f'SELECT * FROM {t}').fetchall()==rows
    db.close()
