"""Schema37 upgrade preserves opaque account evidence and makes Game history durable."""
import sqlite3
import json
from pathlib import Path

import pytest

from nfprogress.core.sqlite.schema import apply_migrations, MIGRATIONS_DIR

_GAME_VECTORS=json.loads((Path(__file__).resolve().parents[1]/'frontend/src/cloud/__fixtures__/gameCodecV1.json').read_text())['examples']


@pytest.mark.parametrize('vector',_GAME_VECTORS,ids=lambda vector:vector['name'])
def test_python_game_writer_matches_frozen_ts_rust_vectors(vector):
    from nfprogress.core.sqlite.game_sync_writer import canonical,frame
    assert canonical(vector['event'])==vector['canonical_json']
    assert frame(vector['event']).hex()==vector['frame_hex']


@pytest.mark.parametrize('version', range(37))
def test_game_every_prefix_upgrade_and_reopen(version, tmp_path):
    path = tmp_path / 'game.db'
    db = sqlite3.connect(path)
    db.create_function('note_sync_remote_apply_authorized', 1, lambda _: 0)
    db.execute("CREATE TABLE domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,project_id TEXT NOT NULL,stage_id TEXT,progress_id TEXT,effective_date TEXT,delta_symbols REAL,context_json TEXT NOT NULL,created_at TEXT NOT NULL,processed_at TEXT,consumer TEXT NOT NULL DEFAULT 'game',version INTEGER NOT NULL DEFAULT 1)")
    for migration in sorted(MIGRATIONS_DIR.glob('*.sql'))[:version]:
        db.executescript(migration.read_text())
    db.execute('CREATE TABLE schema_info(schema_version INTEGER NOT NULL)')
    db.execute('INSERT INTO schema_info VALUES(?)', (version,))
    db.commit()
    assert apply_migrations(db) == 38
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    assert db.execute('SELECT COUNT(*) FROM cloud_game_rewards').fetchone() == (0,)
    db.close()
    db = sqlite3.connect(path)
    assert apply_migrations(db) == 38
    db.close()


def test_game_populated36_preserves_catalog_blocker_and_ciphertext(tmp_path, monkeypatch):
    import nfprogress.core.sqlite.schema as schema
    db = sqlite3.connect(tmp_path / 'populated.db')
    monkeypatch.setattr(schema, 'CURRENT_SCHEMA_VERSION', 36)
    apply_migrations(db)
    db.execute("INSERT INTO cloud_sync_state VALUES('a','123e4567-e89b-42d3-a456-426614174001',1,0,'now','now')")
    event = '123e4567-e89b-42d3-a456-426614174002'
    db.execute("INSERT INTO cloud_sync_account_inbox(account_id,event_id,canonical_user_id,scope,server_sequence,device_id,entity_id,entity_type,operation,sync_revision,updated_at,deleted_at,crypto_version,aad_version,nonce,ciphertext,state,error_code,received_at) VALUES('a',?,'123e4567-e89b-42d3-a456-426614174003','account',1,'123e4567-e89b-42d3-a456-426614174001','retained-folder','folder','upsert',1,'now',NULL,2,2,?,?,'blocked','account_entity_codec_not_activated','now')", (event, b'n' * 24, b'c' * 32))
    db.execute("INSERT INTO cloud_catalog_inbox_blockers VALUES('a',?,'catalog_parent_unknown')", (event,))
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='schema_info'")]
    before = {t: db.execute(f'SELECT * FROM "{t}"').fetchall() for t in tables}
    db.commit()
    monkeypatch.setattr(schema, 'CURRENT_SCHEMA_VERSION', 38)
    assert apply_migrations(db) == 38
    for table, rows in before.items():
        assert db.execute(f'SELECT * FROM "{table}"').fetchall() == rows
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    with pytest.raises(sqlite3.IntegrityError, match='immutable account inbox'):
        db.execute("UPDATE cloud_sync_account_inbox SET ciphertext=?", (b'x' * 32,))
    with pytest.raises(sqlite3.IntegrityError, match='cross-scope inbox collision'):
        db.execute("INSERT INTO cloud_sync_inbox(account_id,event_id,server_sequence,device_id,project_id,entity_id,entity_type,operation,sync_revision,updated_at,received_at) VALUES('a',?,1,'123e4567-e89b-42d3-a456-426614174001','P','N','note','upsert',1,'now','now')", (event,))
    db.close()


def test_game_reward_unique_bytes_and_transaction_rollback(tmp_path):
    path = tmp_path / 'reward.db'
    db = sqlite3.connect(path)
    apply_migrations(db)
    db.execute("INSERT INTO cloud_sync_state VALUES('a','123e4567-e89b-42d3-a456-426614174001',0,0,'now','now')")
    project, reward = ['123e4567-e89b-42d3-a456-' + f'{i:012d}' for i in (2, 3)]
    for event, scope, owner, pid in ((project, 'project', '["P",null]', 'P'), (reward, 'account', 'account', None)):
        db.execute("INSERT INTO cloud_game_events(account_id,event_id,scope,owner_key,project_id,entity_id,canonical_frame,parents_json,revision,state) VALUES('a',?,?,?,?,?,?, '[]',1,'unsealed')", (event, scope, owner, pid, 'game:' + event, b'WORTA-C1' + b'x' * 20))
    db.commit()
    db.execute('BEGIN')
    db.execute("INSERT INTO cloud_game_rewards VALUES('a','reward:X',?,?,?)", (reward, project, b'fixed-frame'))
    db.rollback()
    assert db.execute('SELECT COUNT(*) FROM cloud_game_rewards').fetchone() == (0,)
    db.execute("INSERT INTO cloud_game_rewards VALUES('a','reward:X',?,?,?)", (reward, project, b'fixed-frame'))
    db.commit()
    db.close()
    db = sqlite3.connect(path)
    db.execute('PRAGMA foreign_keys=ON')
    for frame in (b'fixed-frame', b'different-effect'):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO cloud_game_rewards VALUES('a','reward:X',?,?,?)", (reward, project, frame))
    with pytest.raises(sqlite3.IntegrityError, match='immutable game evidence'):
        db.execute("UPDATE cloud_game_rewards SET canonical_frame=?", (b'changed',))
    with pytest.raises(sqlite3.IntegrityError, match='retained game history'):
        db.execute('DELETE FROM cloud_game_events')
    assert db.execute('SELECT canonical_frame FROM cloud_game_rewards').fetchone() == (b'fixed-frame',)
    db.close()


def test_game_compatibility_writes_retain_local_evidence_and_block_complete_sync(tmp_path):
    import json
    db = sqlite3.connect(tmp_path / 'compatibility.db')
    apply_migrations(db)
    db.execute("INSERT INTO cloud_sync_state VALUES('a','123e4567-e89b-42d3-a456-426614174001',0,0,'now','now')")
    event = '123e4567-e89b-42d3-a456-426614174002'
    frame = b'WORTA-C1' + b'x' * 20
    db.execute("INSERT INTO cloud_game_events(account_id,event_id,scope,owner_key,entity_id,canonical_frame,parents_json,revision,state,server_sequence) VALUES('a',?,'account','account','game-state',?,'[]',1,'applied',1)", (event, frame))
    db.execute("INSERT INTO cloud_game_apply_ledger VALUES('a',?,1,'applied',?,?,?)", (event, b'n' * 24, b'c' * 16, frame))
    db.execute("INSERT INTO cloud_game_migrations VALUES('a','account','candidate','active',NULL)")
    original = {'gamer': {'coins': 50, 'writing_session': None}, 'notifications': {'read': []}}
    db.execute('INSERT INTO game_state VALUES(1,2,?,?)', (json.dumps(original), 'before'))
    # Notifications and the active session are local class C.
    local = {**original, 'notifications': {'read': ['notice']}, 'gamer': {**original['gamer'], 'writing_session': {'progress': 10}}}
    db.execute('UPDATE game_state SET payload_json=? WHERE id=1', (json.dumps(local),))
    assert db.execute('SELECT COUNT(*) FROM cloud_game_local_mutations').fetchone() == (0,)
    changed = {**local, 'gamer': {**local['gamer'], 'coins': 100}}
    db.execute('UPDATE game_state SET payload_json=?,updated_at=? WHERE id=1', (json.dumps(changed), 'after'))
    prior, retained = db.execute('SELECT prior_payload_json,payload_json FROM cloud_game_local_mutations').fetchone()
    assert json.loads(prior) == local
    assert json.loads(retained) == changed
    assert json.loads(db.execute('SELECT payload_json FROM game_state').fetchone()[0]) == changed
    assert db.execute('SELECT lifecycle,blocker FROM cloud_game_migrations').fetchone() == ('blocked', 'game_unsupported_local_mutation')
    assert db.execute('SELECT code FROM cloud_game_blockers').fetchone() == ('game_unsupported_local_mutation',)
    assert db.execute('SELECT COUNT(*) FROM cloud_game_rewards').fetchone() == (0,)
    # A subsequent compatibility writer cannot escape capture after the first block.
    changed['gamer']['coins'] = 150
    db.execute('UPDATE game_state SET payload_json=? WHERE id=1', (json.dumps(changed),))
    assert db.execute('SELECT COUNT(*) FROM cloud_game_local_mutations').fetchone() == (2,)
    with pytest.raises(sqlite3.IntegrityError, match='ledger rebuild'):
        db.execute('DELETE FROM game_state')
    db.commit()
    db.close()
    db = sqlite3.connect(tmp_path / 'compatibility.db')
    assert db.execute('SELECT COUNT(*) FROM cloud_game_local_mutations').fetchone() == (2,)
    assert db.execute('SELECT code FROM cloud_game_blockers').fetchone() == ('game_unsupported_local_mutation',)
    db.close()


def test_game_python_developer_provenance_survives_another_override(tmp_path, monkeypatch):
    import json
    import engine
    monkeypatch.setattr(engine, 'get_app_data_dir', lambda: tmp_path)
    from nfprogress.core.game_state import SQLiteGameRepository
    import game
    repository = SQLiteGameRepository(tmp_path)
    gamer = game.Gamer()
    gamer.coins = 123
    repository.record_game_developer_override(gamer)
    gamer.coins = 456
    repository.record_game_developer_override(gamer)
    with repository.transaction() as db:
        rows = db.execute('SELECT code,source_json FROM cloud_game_local_restrictions').fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 'game_developer_state_restricted'
    assert json.loads(rows[0][1])['coins'] == 123


def test_game_python_consumer_marker_failure_is_atomic_across_restart(tmp_path, monkeypatch):
    import engine
    monkeypatch.setattr(engine, 'get_app_data_dir', lambda: tmp_path)
    from nfprogress.core.game_state import SQLiteGameRepository, GameEventConsumer
    repository = SQLiteGameRepository(tmp_path)
    with repository.transaction() as db:
        repository._write_payload({'gamer': {'coins': 0, 'exp': 0}}, db)
        db.execute("INSERT INTO domain_events(event_id,event_type,project_id,delta_symbols,context_json,created_at) VALUES('source','ProgressAdded','p',100,'{}','now')")
        db.execute("CREATE TRIGGER fail_game_marker BEFORE UPDATE OF processed_at ON domain_events WHEN NEW.processed_at IS NOT NULL BEGIN SELECT RAISE(ABORT,'injected marker failure'); END")
    assert GameEventConsumer(tmp_path).process_pending() == {'processed': 0, 'failed': 1}
    assert repository.read_payload()['gamer']['coins'] == 0
    with repository.transaction() as db:
        assert db.execute("SELECT processed_at,attempt_count FROM domain_events WHERE event_id='source'").fetchone()[:] == (None, 1)
        db.execute('DROP TRIGGER fail_game_marker')
    consumer = GameEventConsumer(tmp_path)
    assert consumer.process_pending() == {'processed': 1, 'failed': 0}
    assert consumer.process_pending() == {'processed': 0, 'failed': 0}
    state = SQLiteGameRepository(tmp_path).read_payload()
    assert state['gamer']['coins'] == 10
    assert state['gamer']['exp'] == 500
