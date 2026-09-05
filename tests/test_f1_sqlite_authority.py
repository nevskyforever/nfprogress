from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import engine
import pytest

from nfprogress.core.migration import (
    MigrationBundle,
    import_projects_bundle,
    verify_projects_bundle,
)
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.sqlite.ordering import OrderInvariantError
from nfprogress.core.sqlite.ownership import StorageOwner, StorageOwnershipRepository, Subsystem
from nfprogress.core.storage import PickleRepository


def _complex_legacy_state():
    project = engine.Project('F1 project', 10_000, unit='symbols')
    project.custom_unknown = {'future': ['значение', True, None]}
    project.synch = {
        'type': 'word', 'path': '/tmp/manuscript.docx', 'file_id': 'word-17',
        'provider_metadata': {'revision': 3},
    }
    project.last_synch = datetime(2026, 1, 2, 3, 4)
    project.mindmap_data = {
        'nodeData': {'id': 'root', 'topic': 'Корень', 'children': []},
        'nfprogressFloatingItems': [
            {'id': 'note', 'kind': 'note', 'text': 'Текст', 'x': 25, 'y': 75},
        ],
    }
    project.folder_id = 'folder-1'
    project.notes.append(engine.Note(1_000, 1_000, 10, entry_id='entry-1'))
    project.notes[0].future_progress_field = {'source': 'legacy'}
    stage = engine.Stage('Chapter', 5_000, parent_project_name=project.name, stage_id='stage-1')
    stage.custom_stage_field = {'keep': 'yes'}
    stage.synch = {'type': 'scrivener', 'path': '/tmp/book.scriv'}
    stage.notes.append(engine.Note(500, 500, 10, entry_id='entry-2'))
    project.stages = [stage]
    project.enable_stages = True
    return {
        'projects': {project.name: project},
        'project_order': [project.project_id],
        'project_folders': [{'id': 'folder-1', 'name': 'Черновики', 'future': {'color': 'blue'}}],
        'last': project.name,
        'future_root_field': {'version': 2},
    }


def test_f1_bundle_is_idempotent_and_preserves_unknown_sync_map_and_folders(tmp_path):
    state = _complex_legacy_state()
    bundle = MigrationBundle.from_legacy(state)
    bundle.source_manifest = {
        'data.pkl': {
            'source_format': 'pickle', 'source_schema_version': 'legacy',
            'checksum': 'sha256:test', 'size_bytes': 123,
        },
    }

    import_projects_bundle(bundle, tmp_path)
    import_projects_bundle(bundle, tmp_path)

    consistent, errors = verify_projects_bundle(bundle, tmp_path)
    assert consistent, errors
    with open_database(tmp_path) as db:
        assert json.loads(db.execute(
            "SELECT payload_json FROM project_extensions WHERE entity_type='project'",
        ).fetchone()[0]) == {'custom_unknown': {'future': ['значение', True, None]}}
        assert db.execute('SELECT COUNT(*) FROM project_bindings').fetchone()[0] == 2
        assert json.loads(db.execute(
            "SELECT payload_json FROM project_bindings WHERE stage_id IS NULL",
        ).fetchone()[0])['provider_metadata'] == {'revision': 3}
        assert json.loads(db.execute(
            'SELECT payload_json FROM project_folders',
        ).fetchone()[0])['future'] == {'color': 'blue'}


def test_f1_import_does_not_delete_sqlite_owned_notes_or_other_domains(tmp_path):
    state = _complex_legacy_state()
    project = next(iter(state['projects'].values()))
    repository = PickleRepository(tmp_path)
    repository.write_projects(state)
    StorageOwnershipRepository(tmp_path).set_owner(Subsystem.NOTES, StorageOwner.SQLITE)
    with open_database(tmp_path) as db:
        db.execute(
            "INSERT INTO notes(id, project_id, updated_at, payload_json) VALUES(?, ?, ?, ?)",
            ('note-1', project.project_id, 'sqlite-time', '{"content":"authoritative"}'),
        )
        db.execute("INSERT INTO settings(key, value_json) VALUES('f1', 'true')")
        db.commit()

    import_projects_bundle(MigrationBundle.from_legacy(state), tmp_path)

    with open_database(tmp_path) as db:
        note = db.execute('SELECT updated_at, payload_json FROM notes WHERE id="note-1"').fetchone()
        assert note['updated_at'] == 'sqlite-time'
        assert json.loads(note['payload_json'])['content'] == 'authoritative'
        assert db.execute("SELECT value_json FROM settings WHERE key='f1'").fetchone()[0] == 'true'


def test_populated_pre_order_upgrade_stops_before_publishing_schema_v3(tmp_path):
    connection = sqlite3.connect(tmp_path / 'nfprogress.db')
    connection.executescript((Path(__file__).parents[1] / 'nfprogress/core/sqlite/migrations/001_initial.sql').read_text())
    connection.execute('CREATE TABLE schema_info (schema_version INTEGER NOT NULL)')
    connection.execute("INSERT INTO schema_info VALUES(1)")
    connection.execute("INSERT INTO settings VALUES('keep', '42')")
    connection.execute("INSERT INTO projects VALUES('p', 'P', 1, 0, 'symbols', 'активен', NULL, NULL, '{}')")
    connection.execute("INSERT INTO notes VALUES('n', 'p', NULL, 't', '{}')")
    connection.commit()
    connection.close()

    with pytest.raises(OrderInvariantError, match='project ordering is incomplete'):
        open_database(tmp_path)
    with sqlite3.connect(tmp_path / 'nfprogress.db') as db:
        assert db.execute('SELECT schema_version FROM schema_info').fetchone()[0] == 2
        assert db.execute("SELECT value_json FROM settings WHERE key='keep'").fetchone()[0] == '42'
        assert db.execute('SELECT id FROM notes').fetchone()[0] == 'n'
