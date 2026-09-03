from __future__ import annotations

import engine
import pytest

from nfprogress.core.services.notes import ProjectNotesService, extract_mindmap_notes
from nfprogress.core.services.projects import ProjectService
from nfprogress.core.sqlite import (
    SQLiteNotesRepository,
    StorageOwner,
    StorageOwnershipRepository,
    Subsystem,
    canonical_notes_from_projects,
    cutover_notes,
)
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.storage import PickleRepository


def _seed(tmp_path):
    repository = PickleRepository(tmp_path)
    project = engine.Project('Книга Ω', 1000)
    stage = engine.Stage('Глава', 1000, parent_project_name=project.name, stage_id='stage-1')
    stage.project_notes = [{'id': 'stage-note', 'title': 'Этап', 'content': 'текст', 'sort_order': 0}]
    project.stages = [stage]
    project.enable_stages = True
    project.project_notes = [{'id': 'project-note', 'title': 'Проект', 'content': '内容', 'tags': ['идея'], 'sort_order': 0}]
    project.mindmap_data = {
        'nodeData': {'id': 'map-root', 'topic': project.name, 'children': []},
        'freeNodes': [{'id': 'map-note', 'topic': 'Заметка карты', 'children': [], 'nfprogressNote': True}],
    }
    repository.write_projects({'projects': {project.name: project}, 'last': project.name})
    return repository, project


def test_controlled_notes_cutover_imports_full_state_and_keeps_ids(tmp_path):
    repository, project = _seed(tmp_path)
    legacy = repository.read_projects()
    cutover_notes(tmp_path, legacy)

    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.NOTES) == StorageOwner.SQLITE
    rows = SQLiteNotesRepository(tmp_path).list_all(project.project_id)
    assert 'project-note' in {row['id'] for row in rows}
    assert any(row['source_type'] == 'mindmap' for row in rows)
    assert next(row for row in rows if row['id'] == 'project-note')['content'] == '内容'
    assert next(row for row in rows if row['source_type'] == 'mindmap')['content'] == 'Заметка карты'
    assert next(row for row in rows if row['source_type'] == 'mindmap')['source_map_id'] == 'map-root'
    assert len(SQLiteNotesRepository(tmp_path).list(project.project_id)) == 2
    assert len(SQLiteNotesRepository(tmp_path).list(project.project_id, 'stage-1')) == 1


def test_legacy_note_without_id_gets_repeatable_identity(tmp_path):
    repository = PickleRepository(tmp_path)
    project = engine.Project('Без ID', 1000)
    project.project_notes = [{'title': 'Старая заметка', 'content': 'текст'}]
    repository.write_projects({'projects': {project.name: project}})

    first = canonical_notes_from_projects(repository.read_projects())
    second = canonical_notes_from_projects(repository.read_projects())
    assert len(first) == len(second) == 1
    assert first[0]['id'] == second[0]['id']


def test_cutover_failure_rolls_back_notes_and_owner(tmp_path, monkeypatch):
    repository, _project = _seed(tmp_path)
    legacy = repository.read_projects()
    import nfprogress.core.sqlite.notes as notes_module
    original_json = notes_module._json
    calls = 0
    def fail_during_import(value):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise OSError('disk full')
        return original_json(value)
    monkeypatch.setattr(notes_module, '_json', fail_during_import)
    with pytest.raises(OSError, match='disk full'):
        cutover_notes(tmp_path, legacy)
    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.NOTES) == StorageOwner.PICKLE
    with open_database(tmp_path) as db:
        assert db.execute('SELECT COUNT(*) FROM notes').fetchone()[0] == 2


def test_sqlite_notes_are_idempotent_and_pickle_changes_are_ignored(tmp_path):
    repository, project = _seed(tmp_path)
    cutover_notes(tmp_path, repository.read_projects())
    notes = ProjectNotesService(repository, project.project_id)
    project_note_id = next(item['id'] for item in notes.load_notes()['notes'] if item['title'] == 'Проект')
    notes.update_note(project_note_id, {'content': 'SQLite новая версия'})
    stale = repository.read_projects()
    stale['projects'][project.name].project_notes[0]['content'] = 'PKL старая версия'
    repository.write_projects(stale)
    assert notes.get_note(project_note_id)['content'] == 'SQLite новая версия'
    assert next(row for row in SQLiteNotesRepository(tmp_path).list_all(project.project_id) if row['id'] == 'project-note')['content'] == 'SQLite новая версия'


def test_sqlite_map_note_updates_map_without_duplicate_cards(tmp_path):
    repository, project = _seed(tmp_path)
    cutover_notes(tmp_path, repository.read_projects())
    service = ProjectNotesService(repository, project.project_id)
    map_note = next(item for item in service.load_notes()['notes'] if item['source_type'] == 'mindmap')

    service.update_note(map_note['id'], {'content': 'Обновлено на карте'})
    stored = repository.read_projects()['projects'][project.name]
    assert extract_mindmap_notes(stored.mindmap_data) == [{'id': 'map-note', 'text': 'Обновлено на карте'}]
    assert len([item for item in SQLiteNotesRepository(tmp_path).list(project.project_id) if item['source_type'] == 'mindmap']) == 1

    service.update_mindmap(stored.mindmap_data)
    assert len([item for item in SQLiteNotesRepository(tmp_path).list(project.project_id) if item['source_type'] == 'mindmap']) == 1


def test_project_and_stage_deletion_removes_sqlite_notes(tmp_path):
    repository, project = _seed(tmp_path)
    cutover_notes(tmp_path, repository.read_projects())
    service = ProjectService(repository)
    service.delete_stage(project.project_id, 'stage-1')
    with open_database(tmp_path) as db:
        assert db.execute("SELECT COUNT(*) FROM notes WHERE stage_id = 'stage-1'").fetchone()[0] == 0
    service.delete_project(project.project_id)
    with open_database(tmp_path) as db:
        assert db.execute('SELECT COUNT(*) FROM notes WHERE project_id = ?', (project.project_id,)).fetchone()[0] == 0


def test_sqlite_notes_write_requires_valid_mirror_relation(tmp_path):
    repository, project = _seed(tmp_path)
    cutover_notes(tmp_path, repository.read_projects())
    with open_database(tmp_path) as db:
        db.execute("UPDATE mirror_state SET sync_status = 'dirty' WHERE id = 1")
        db.commit()
    with pytest.raises(Exception, match='backend'):
        SQLiteNotesRepository(tmp_path).create({
            'id': 'new', 'project_id': project.project_id, 'stage_id': None,
            'title': '', 'content': '', 'created_at': '', 'updated_at': '',
        })


def test_backup_always_contains_authoritative_notes_database(tmp_path):
    repository, _project = _seed(tmp_path)
    cutover_notes(tmp_path, repository.read_projects())
    backup = repository.create_backup('data')
    assert (backup / 'nfprogress.db').is_file()
