"""Schema32 is forward-only; framed Note receipts retain exact source bytes."""
import sqlite3
import pytest
from nfprogress.core.sqlite.schema import apply_migrations, MIGRATIONS_DIR

@pytest.mark.parametrize('version',range(33))
def test_content_note_every_prefix_upgrade_and_reopen(version,tmp_path):
    path=tmp_path/'content.db';db=sqlite3.connect(path)
    db.create_function('note_sync_remote_apply_authorized',1,lambda _:0)
    db.execute("CREATE TABLE domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,project_id TEXT NOT NULL,stage_id TEXT,progress_id TEXT,effective_date TEXT,delta_symbols REAL,context_json TEXT NOT NULL,created_at TEXT NOT NULL,processed_at TEXT,consumer TEXT NOT NULL DEFAULT 'game',version INTEGER NOT NULL DEFAULT 1)")
    for p in sorted(MIGRATIONS_DIR.glob('*.sql'))[:version]:db.executescript(p.read_text())
    db.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    db.execute('INSERT INTO schema_info VALUES(?)',(version,));db.commit()
    assert apply_migrations(db)==32
    assert db.execute('SELECT count(*) FROM cloud_content_note_receipts').fetchone()==(0,)
    db.close();db=sqlite3.connect(path);assert apply_migrations(db)==32;db.close()


def test_content_note_populated31_preserves_all_existing_tables(tmp_path,monkeypatch):
    import nfprogress.core.sqlite.schema as schema
    path=tmp_path/'upgrade.db';db=sqlite3.connect(path)
    with monkeypatch.context() as m:
        m.setattr(schema,'CURRENT_SCHEMA_VERSION',31);assert apply_migrations(db)==31
    db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('L','Local',1,'symbols','active','{}')")
    db.execute("INSERT INTO project_order VALUES('L',0)")
    db.execute("INSERT INTO stages(id,project_id,name,infinite,unit,status,payload_json) VALUES('S','L','Stage',1,'symbols','active','{}')")
    db.execute("INSERT INTO stage_order VALUES('S','L',0)")
    db.execute("INSERT INTO notes VALUES('N','L','S','now','{\"content_format\":\"plain\",\"metadata\":{\"extension\":\"retained\"}}')")
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('a','123e4567-e89b-42d3-a456-426614174001','now','now')")
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='schema_info'")]
    before={t:db.execute(f'SELECT * FROM "{t}"').fetchall() for t in tables};db.commit()
    assert apply_migrations(db)==32
    for t,rows in before.items():assert db.execute(f'SELECT * FROM "{t}"').fetchall()==rows
    db.close();db=sqlite3.connect(path);assert apply_migrations(db)==32
    for t,rows in before.items():assert db.execute(f'SELECT * FROM "{t}"').fetchall()==rows
    db.close()


def test_content_note_receipt_frame_and_envelope_are_immutable(tmp_path):
    db=sqlite3.connect(tmp_path/'receipt.db');apply_migrations(db)
    eid='123e4567-e89b-42d3-a456-426614174002';device='123e4567-e89b-42d3-a456-426614174001'
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('a',?,'now','now')",(device,))
    db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,state,received_at) VALUES('a',?,1,?,'P','N','note','event',1,'now','received','now')",(eid,device))
    db.execute("INSERT INTO cloud_content_note_receipts VALUES('a',?,1,?,?,?,'waiting','stage_dependency_missing')",(eid,b'frame',b'n'*24,b'ciphertext'))
    for sql,args in [("UPDATE cloud_content_note_receipts SET canonical_frame=?",(b'other',)),("UPDATE cloud_content_note_receipts SET nonce=?",(b'x'*24,)),("UPDATE cloud_content_note_receipts SET ciphertext=?",(b'other',)),("UPDATE cloud_content_note_receipts SET server_sequence=2",()),("DELETE FROM cloud_content_note_receipts",())]:
        with pytest.raises(sqlite3.IntegrityError):db.execute(sql,args)
    db.execute("UPDATE cloud_content_note_receipts SET outcome='applied',blocker=NULL")
    with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE cloud_content_note_receipts SET outcome='waiting'")
    with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE cloud_content_note_receipts SET blocker='stage_dependency_missing'")
    db.commit();db.close();db=sqlite3.connect(tmp_path/'receipt.db');apply_migrations(db)
    assert db.execute('SELECT canonical_frame,outcome,blocker FROM cloud_content_note_receipts').fetchone()==(b'frame','applied',None)
    db.close()
