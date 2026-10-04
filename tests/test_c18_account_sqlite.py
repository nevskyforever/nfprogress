import sqlite3
import pytest
from nfprogress.core.sqlite.schema import apply_migrations, CURRENT_SCHEMA_VERSION, MIGRATIONS_DIR


@pytest.mark.parametrize('version',range(30))
def test_account_migration_every_historical_path(version):
    db=sqlite3.connect(':memory:')
    db.create_function('note_sync_remote_apply_authorized',1,lambda _:0)
    db.execute("CREATE TABLE schema_info(schema_version INTEGER NOT NULL)")
    db.execute("CREATE TABLE domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,project_id TEXT NOT NULL,stage_id TEXT,progress_id TEXT,effective_date TEXT,delta_symbols REAL,context_json TEXT NOT NULL,created_at TEXT NOT NULL,processed_at TEXT,consumer TEXT NOT NULL DEFAULT 'game',version INTEGER NOT NULL DEFAULT 1)")
    for migration in sorted(MIGRATIONS_DIR.glob('*.sql'))[:version]:
        db.executescript(migration.read_text())
    db.execute('INSERT INTO schema_info VALUES(?)',(version,));db.commit()
    assert apply_migrations(db)==CURRENT_SCHEMA_VERSION==37
    assert 'project_id' not in {row[1] for row in db.execute('PRAGMA table_info(cloud_sync_account_inbox)')}
    assert db.execute('SELECT COUNT(*) FROM projects').fetchone()==(0,)
    assert apply_migrations(db)==37
    db.close()


def test_populated_29_upgrade_and_reopen_preserves_accepted_data(tmp_path):
    import nfprogress.core.sqlite.schema as schema
    path=tmp_path/'account.db';db=sqlite3.connect(path)
    try:
        schema.CURRENT_SCHEMA_VERSION=29;apply_migrations(db)
    finally:schema.CURRENT_SCHEMA_VERSION=37
    db.execute("INSERT INTO cloud_sync_state VALUES('a','123e4567-e89b-42d3-a456-426614174001',1,0,'now','now')")
    db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,state,received_at) VALUES('a','123e4567-e89b-42d3-a456-426614174099',1,'123e4567-e89b-42d3-a456-426614174001','p','p','project_metadata','upsert',1,'now','received','now')")
    db.execute("INSERT INTO cloud_sync_event_objects VALUES('a','123e4567-e89b-42d3-a456-426614174099',1,1,?,?,'now')",(b'n'*24,b'c'*16));db.commit()
    assert apply_migrations(db)==37
    assert db.execute('SELECT nonce,ciphertext FROM cloud_sync_event_objects').fetchone()==(b'n'*24,b'c'*16)
    db.execute("INSERT INTO cloud_sync_account_inbox(account_id,event_id,canonical_user_id,scope,server_sequence,device_id,entity_id,entity_type,operation,sync_revision,updated_at,crypto_version,aad_version,nonce,ciphertext,received_at,state,error_code) VALUES('a','123e4567-e89b-42d3-a456-426614174098','123e4567-e89b-42d3-a456-426614174000','account',2,'123e4567-e89b-42d3-a456-426614174001','folder','folder','upsert',1,'now',2,2,?,?,'now','blocked','account_entity_codec_not_activated')",(b'n'*24,b'c'*16));db.commit();db.close()
    db=sqlite3.connect(path);assert apply_migrations(db)==37
    assert db.execute('SELECT nonce,ciphertext,error_code FROM cloud_sync_account_inbox').fetchone()==(b'n'*24,b'c'*16,'account_entity_codec_not_activated')
    with pytest.raises(sqlite3.IntegrityError):db.execute('UPDATE cloud_sync_account_inbox SET entity_id="changed"')
    db.close()
