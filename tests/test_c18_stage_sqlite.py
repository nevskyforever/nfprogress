"""Forward migration, lossless legacy classification and shared codec contract."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from test_c18_metadata_sqlite import _database
from nfprogress.core.sqlite.schema import CURRENT_SCHEMA_VERSION, apply_migrations

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['name', 'goal', 'infinite', 'unit', 'status', 'deadline', 'personal_goal',
          'auto_freeze', 'streak_enabled', 'work_method', 'created_at', 'completed_at']

@pytest.mark.parametrize('version', range(30))
def test_structural_every_supported_schema_and_idempotent_upgrade(version):
    db = _database(version)
    db.commit()
    assert apply_migrations(db) == CURRENT_SCHEMA_VERSION == 29
    assert apply_migrations(db) == CURRENT_SCHEMA_VERSION
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    assert db.execute('SELECT COUNT(*) FROM cloud_sync_stage_candidates').fetchone()[0] == 0


def test_populated_27_upgrade_preserves_exact_metadata_and_stage_order():
    db = _database(27)
    db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('project','Local',1,'symbols','active','{}')")
    db.execute("INSERT INTO project_order VALUES('project',0)")
    db.execute("INSERT INTO stages(id,project_id,name,infinite,unit,status,payload_json) VALUES('S1','project','Alpha',1,'symbols','active','{\"mindmap\":{\"private\":1}}')")
    db.execute("INSERT INTO stage_order VALUES('S1','project',0)")
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('account','123e4567-e89b-42d3-a456-426614174003','now','now')")
    db.execute("INSERT INTO cloud_sync_project_bindings VALUES('project','account','now','now')")
    db.execute("INSERT INTO cloud_sync_metadata_candidates(candidate_id,account_id,project_id,device_id,bootstrap_id,generation,codec_version,snapshot_json,unsupported_json,source_payload_json,state,created_at) VALUES('candidate','account','project','123e4567-e89b-42d3-a456-426614174003','123e4567-e89b-42d3-a456-426614174002',1,1,'{}','[]','{}','candidate','now')")
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cloud_sync_metadata_%'")] + ['stages','stage_order']
    before = {t: db.execute(f'SELECT * FROM {t}').fetchall() for t in tables}
    db.commit(); assert apply_migrations(db) == CURRENT_SCHEMA_VERSION
    assert {t:db.execute(f'SELECT * FROM {t}').fetchall() for t in tables} == before
    assert db.execute('SELECT COUNT(*) FROM cloud_sync_stage_candidates').fetchone()[0] == 0


def test_stage_model_sqlite_native_typescript_exact_portable_agreement(monkeypatch):
    import engine
    monkeypatch.setattr(engine, "load_settings", lambda: {})
    from nfprogress.core.serialization.projections import serialize_stage
    from nfprogress.core.sqlite.repository import SQLiteMirrorRepository
    from datetime import date
    fixture=json.loads((ROOT/'frontend/src/cloud/__fixtures__/stageCodecV1.json').read_text())
    stage=engine.Stage(name='Stage Alpha', goal=1234.5, create_date=date(2026,9,1),
        deadline=date(2027,1,1), personal_goal_for_the_day=100,stage_id='S1')
    source=serialize_stage(stage)
    assert fixture['portable_fields'] == FIELDS
    assert {k:source[k] for k in FIELDS} == fixture['event']['stage']
    # The persistence extension detector must classify every actual model field.
    extension=SQLiteMirrorRepository._extension_row('stage','S1',stage)
    assert json.loads(extension[2]) == {}
    stage.future_field={'must':'survive'}
    assert json.loads(SQLiteMirrorRepository._extension_row('stage','S1',stage)[2]) == {'future_field':{'must':'survive'}}
    rust=(ROOT/'frontend/src-tauri/src/stage_sync.rs').read_text()
    ts=(ROOT/'frontend/src/cloud/stageCodec.ts').read_text()
    for field in FIELDS:
        assert f'"{field}"' in rust.split('const LEGACY')[0]
        assert f"'{field}'" in ts.split('export const MAX_STAGE_BYTES')[0]
    assert set(source) == set(FIELDS) | {'id','total','progress','updated_at','notes_updated_at',
        'mindmap_updated_at','today_goal','planning_date','plan_daily_goal','added_today','remaining',
        'streak_status','streak_length','max_streak','progress_entries','project_notes','mindmap','stages',
        'stages_enabled','combine_stage_mindmaps','cover_image','folder_id','sync_available','parent_project_name'}


def test_populated_28_integration_upgrade_retains_structural_frames_and_ciphertext():
    db = _database(28)
    db.execute("INSERT INTO projects(id,name,infinite,unit,status,payload_json) VALUES('project','Local',1,'symbols','active','{}')")
    db.execute("INSERT INTO project_order VALUES('project',0)")
    db.execute("INSERT INTO cloud_sync_state(account_id,device_id,created_at,updated_at) VALUES('account','123e4567-e89b-42d3-a456-426614174003','now','now')")
    db.execute("INSERT INTO cloud_sync_project_bindings VALUES('project','account','now','now')")
    fixture = json.loads((ROOT/'frontend/src/cloud/__fixtures__/stageCodecV1.json').read_text())
    e = fixture['event']; h = e['header']; payload = fixture['canonical_json'].encode()
    frame = b'WORTA-C1' + bytes([1, 2, 1, 0]) + len(payload).to_bytes(4, 'big') * 2 + payload
    db.execute("INSERT INTO cloud_sync_structural_events(account_id,event_id,project_id,entity_type,entity_id,canonical_frame,metadata_event_id,revision,generation,operation,state) VALUES('account',?,'project','stage','S1',?,?,1,1,'create','sealed')", (h['event_id'],frame,h['metadata_event_id']))
    db.execute("INSERT INTO cloud_sync_event_objects VALUES('account',?,1,1,zeroblob(24),zeroblob(16),'now')", (h['event_id'],))
    tables = ['cloud_sync_structural_events', 'cloud_sync_event_objects', 'projects', 'project_order']
    before = {table: db.execute(f'SELECT * FROM {table}').fetchall() for table in tables}
    db.commit()
    assert apply_migrations(db) == CURRENT_SCHEMA_VERSION == 29
    assert {table: db.execute(f'SELECT * FROM {table}').fetchall() for table in tables} == before
    assert apply_migrations(db) == 29
    assert db.execute('SELECT count(*) FROM cloud_sync_structural_migrations').fetchone()[0] == 0
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
