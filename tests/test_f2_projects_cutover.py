from __future__ import annotations

import json

import engine

from nfprogress.core.migration import MigrationImportError, cutover_projects
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.sqlite.ownership import StorageOwner, StorageOwnershipRepository, Subsystem
from nfprogress.core.storage import PickleRepository


def _legacy_state() -> dict:
    project = engine.Project('F2 project', 10_000, unit='symbols')
    project.future_extension = {'keep': ['value', True]}
    project.notes.append(engine.Note(2_000, 2_000, 20, entry_id='progress-1'))
    stage = engine.Stage('Chapter', 5_000, parent_project_name=project.name, stage_id='stage-1')
    stage.notes.append(engine.Note(1_000, 1_000, 20, entry_id='progress-2'))
    project.stages = [stage]
    project.enable_stages = True
    return {
        'projects': {project.name: project},
        'project_order': [project.project_id],
        'project_folders': [{'id': 'folder-1', 'name': 'Drafts'}],
        'last': project.name,
    }


def test_projects_cutover_verifies_switch_and_is_idempotent(tmp_path):
    repository = PickleRepository(tmp_path)
    with engine.data_directory_context(tmp_path):
        state = _legacy_state()
        repository.write_projects(state)
        bundle = cutover_projects(tmp_path)

    assert bundle.projects[0]['id'] == next(iter(state['projects'].values())).project_id
    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.PROJECTS) == StorageOwner.SQLITE
    with open_database(tmp_path) as db:
        assert db.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM domain_events').fetchone()[0] == 0
        assert json.loads(db.execute(
            "SELECT payload_json FROM project_extensions WHERE entity_type='project'",
        ).fetchone()[0]) == {'future_extension': {'keep': ['value', True]}}

    with engine.data_directory_context(tmp_path):
        cutover_projects(tmp_path)
    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.PROJECTS) == StorageOwner.SQLITE


def test_projects_cutover_failure_keeps_pickle_owner(tmp_path, monkeypatch):
    repository = PickleRepository(tmp_path)
    with engine.data_directory_context(tmp_path):
        state = _legacy_state()
        repository.write_projects(state)

    def fail_verification(*_args, **_kwargs):
        return False, ['intentional mismatch']

    monkeypatch.setattr('nfprogress.core.migration.verify_projects_bundle', fail_verification)
    with engine.data_directory_context(tmp_path):
        try:
            cutover_projects(tmp_path)
        except MigrationImportError:
            pass
        else:
            raise AssertionError('cutover must reject an unverified import')
    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.PROJECTS) == StorageOwner.PICKLE


def test_pickle_project_access_is_blocked_after_cutover(tmp_path):
    repository = PickleRepository(tmp_path)
    with engine.data_directory_context(tmp_path):
        state = _legacy_state()
        repository.write_projects(state)
        cutover_projects(tmp_path)
    with engine.data_directory_context(tmp_path):
        try:
            repository.read_projects()
        except RuntimeError as error:
            assert 'SQLite-authoritative' in str(error)
        else:
            raise AssertionError('legacy project reads must be blocked')
