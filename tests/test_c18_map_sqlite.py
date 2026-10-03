"""Forward-only map substrate upgrades every accepted prefix without data loss."""
import sqlite3
import pytest
from nfprogress.core.sqlite.schema import apply_migrations, MIGRATIONS_DIR

@pytest.mark.parametrize('version', range(34))
def test_map_every_prefix_upgrade_reopen(version, tmp_path):
    path = tmp_path / 'map.db'
    db = sqlite3.connect(path)
    db.create_function('note_sync_remote_apply_authorized', 1, lambda _: 0)
    db.execute("CREATE TABLE domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,project_id TEXT NOT NULL,stage_id TEXT,progress_id TEXT,effective_date TEXT,delta_symbols REAL,context_json TEXT NOT NULL,created_at TEXT NOT NULL,processed_at TEXT,consumer TEXT NOT NULL DEFAULT 'game',version INTEGER NOT NULL DEFAULT 1)")
    for migration in sorted(MIGRATIONS_DIR.glob('*.sql'))[:version]:
        db.executescript(migration.read_text())
    db.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    db.execute('INSERT INTO schema_info VALUES(?)', (version,))
    db.commit()
    assert apply_migrations(db) == 36
    assert db.execute('SELECT count(*) FROM cloud_map_events').fetchone() == (0,)
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    db.close()
    db = sqlite3.connect(path)
    assert apply_migrations(db) == 36
    db.close()


def test_map_populated33_preserves_all_tables(tmp_path, monkeypatch):
    import nfprogress.core.sqlite.schema as schema
    path = tmp_path / 'upgrade.db'
    db = sqlite3.connect(path)
    with monkeypatch.context() as patch:
        patch.setattr(schema, 'CURRENT_SCHEMA_VERSION', 33)
        assert apply_migrations(db) == 33
    db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('P','Local',1,'symbols','active','{\"mindmap\":{\"nodeData\":{\"id\":\"root\",\"topic\":\"retained\",\"children\":[]}}}')")
    db.execute("INSERT INTO project_order VALUES('P',0)")
    db.execute("INSERT INTO stages(id,project_id,name,infinite,unit,status,payload_json) VALUES('S','P','Stage',1,'symbols','active','{}')")
    db.execute("INSERT INTO stage_order VALUES('S','P',0)")
    db.execute("INSERT INTO notes VALUES('N','P','S','now','{\"source_type\":\"mindmap\",\"metadata\":{\"extension\":\"retained\"}}')")
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('a','123e4567-e89b-42d3-a456-426614174001','now','now')")
    tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='schema_info'")]
    before = {table: db.execute(f'SELECT * FROM "{table}"').fetchall() for table in tables}
    db.commit()
    assert apply_migrations(db) == 36
    for table, rows in before.items():
        assert db.execute(f'SELECT * FROM "{table}"').fetchall() == rows
    db.close()
    db = sqlite3.connect(path)
    assert apply_migrations(db) == 36
    for table, rows in before.items():
        assert db.execute(f'SELECT * FROM "{table}"').fetchall() == rows
    db.close()
