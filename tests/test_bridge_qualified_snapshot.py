from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

import engine
import game
import nfprogress.migration_helper as migration_helper
from nfprogress.core.legacy_shadow import sync_legacy_sqlite_shadow
from nfprogress.core.recovery import validate_sqlite_file
from nfprogress.core.services.documents import ProjectDocumentService
from nfprogress.core.sqlite.ordering import validate_order_invariants
from nfprogress.core.storage import PickleRepository
from nfprogress.migration_helper import HelperError, verify_prepared_profile


SOURCE_NAMES = ('data.pkl', 'settings.pkl', 'gamer.pkl', 'documents.json')


def _sha256_sources(root: Path) -> dict[str, str]:
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in SOURCE_NAMES
    }


def _rich_document(label: str = 'Rich text') -> dict:
    return {
        'type': 'doc',
        'content': [
            {
                'type': 'heading',
                'attrs': {'level': 2},
                'content': [{'type': 'text', 'text': 'Heading'}],
            },
            {
                'type': 'paragraph',
                'attrs': {'lineHeight': '1.75'},
                'content': [
                    {
                        'type': 'text',
                        'text': label,
                        'marks': [
                            {'type': 'bold'},
                            {'type': 'italic'},
                            {'type': 'underline'},
                            {'type': 'strike'},
                            {
                                'type': 'textStyle',
                                'attrs': {
                                    'color': '#123456',
                                    'fontFamily': 'Georgia',
                                    'fontSize': '18px',
                                },
                            },
                        ],
                    },
                    {'type': 'text', 'text': '\tTabbed'},
                    {'type': 'hardBreak'},
                    {'type': 'text', 'text': 'next line'},
                ],
            },
            {
                'type': 'bulletList',
                'content': [{
                    'type': 'listItem',
                    'content': [{
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': 'bullet'}],
                    }],
                }],
            },
            {
                'type': 'orderedList',
                'attrs': {'start': 3},
                'content': [{
                    'type': 'listItem',
                    'content': [{
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': 'ordered'}],
                    }],
                }],
            },
            {
                'type': 'blockquote',
                'content': [{
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'quote'}],
                }],
            },
        ],
    }


def _fixture(root: Path) -> tuple[dict, engine.Project, engine.Stage, dict]:
    project = engine.Project('P', 10_000)
    stage = engine.Stage('S', 10_000, parent_project_name=project.name)
    project.stages = [stage]
    project.enable_stages = True
    project.synch = {'type': 'word', 'path': '/tmp/progress-source.docx'}
    project.work_method = 'sync'
    project.last_synch = '2026-09-20T12:00:00+00:00'
    stage.work_method = 'app'
    data = {
        'projects': {project.name: project},
        'last': project.name,
        'notifications': [],
        'global_streaks': [],
        'global_streak_status': 'No',
        'max_global_streak': 0,
    }
    document = {
        f'{project.project_id}:{stage.stage_id}': {
            'project_id': project.project_id,
            'stage_id': stage.stage_id,
            'title': 'Manuscript',
            'content': _rich_document(),
            'content_format': 'tiptap-json/v1',
            'exists': True,
            'updated_at': '2026-09-20T12:00:00+00:00',
            'docx_path': '/tmp/manuscript.docx',
            'sync_state': 'synced',
            'last_synced_hash': 'abc',
            'last_synced_at': '2026-09-20T12:00:00+00:00',
            'local_dirty': False,
            'word_dirty': False,
        },
    }
    with engine.data_directory_context(root):
        engine.atomic_pickle_save(data, engine.get_data_file_path('data'))
        engine.atomic_pickle_save({'language': 'ru'}, engine.get_data_file_path('settings'))
        engine.atomic_pickle_save(game.Gamer(), engine.get_data_file_path('gamer'))
    (root / 'documents.json').write_text(
        json.dumps(document, ensure_ascii=False), encoding='utf-8',
    )
    return data, project, stage, document


def _assert_60_qualified(root: Path) -> None:
    assert validate_sqlite_file(root / 'nfprogress.db', allow_versions={7}) == 7
    assert verify_prepared_profile(root) == (True, [])
    connection = sqlite3.connect(root / 'nfprogress.db')
    try:
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        validate_order_invariants(connection)
        assert dict(connection.execute(
            'SELECT subsystem,owner FROM storage_ownership',
        )) == {
            'projects': 'sqlite',
            'settings': 'sqlite',
            'notes': 'sqlite',
            'game': 'sqlite',
        }
        assert connection.execute(
            'SELECT sync_status FROM mirror_state WHERE id=1',
        ).fetchone()[0] == 'healthy'
        assert json.loads(connection.execute(
            "SELECT value_json FROM game_metadata WHERE key='migration_status'",
        ).fetchone()[0])['status'] == 'ready_for_tauri'
        assert json.loads(connection.execute(
            "SELECT value_json FROM document_metadata "
            "WHERE key='documents_json_migration'",
        ).fetchone()[0])['status'] == 'complete'
    finally:
        connection.close()


def _document_service(root: Path) -> ProjectDocumentService:
    return ProjectDocumentService(
        PickleRepository(root), None, allow_local_files=True,
    )


def test_bridge_preserves_rich_text_and_independent_word_bindings(
        tmp_path, monkeypatch,
):
    _data, project, stage, documents = _fixture(tmp_path)
    before = _sha256_sources(tmp_path)

    def forbidden_service_load(_self):
        raise AssertionError('migration preparation used document service migrations')

    monkeypatch.setattr(
        ProjectDocumentService, '_load_with_migrations', forbidden_service_load,
    )
    assert sync_legacy_sqlite_shadow(tmp_path, raise_on_error=True)

    assert _sha256_sources(tmp_path) == before
    _assert_60_qualified(tmp_path)
    connection = sqlite3.connect(tmp_path / 'nfprogress.db')
    try:
        assert connection.execute(
            'SELECT COUNT(*) FROM projects WHERE id=?', (project.project_id,),
        ).fetchone()[0] == 1
        assert connection.execute(
            'SELECT COUNT(*) FROM stages WHERE id=? AND project_id=?',
            (stage.stage_id, project.project_id),
        ).fetchone()[0] == 1
        content = json.loads(connection.execute(
            'SELECT content_json FROM documents WHERE project_id=? AND stage_id=?',
            (project.project_id, stage.stage_id),
        ).fetchone()[0])
        assert content == next(iter(documents.values()))['content']
        binding = connection.execute(
            'SELECT external_path,last_external_hash,last_synced_revision,'
            'last_synced_hash,last_synced_at,sync_state,expected_external_hash '
            'FROM document_bindings',
        ).fetchone()
        assert binding[0] == '/tmp/manuscript.docx'
        assert binding[1:5] == (
            'abc', 0, 'abc', '2026-09-20T12:00:00+00:00',
        )
        assert binding[5] in {'synced', 'missing_external'}
        assert binding[6] == 'abc'
        project_binding = connection.execute(
            'SELECT external_path,binding_type,last_synced_at '
            'FROM project_bindings WHERE project_id=? AND stage_id IS NULL',
            (project.project_id,),
        ).fetchone()
        assert project_binding == (
            '/tmp/progress-source.docx',
            'word',
            '2026-09-20T12:00:00+00:00',
        )
    finally:
        connection.close()
    with engine.data_directory_context(tmp_path):
        assert engine.load_data()['projects'][project.name].project_id == project.project_id


def test_qualification_markers_are_published_only_after_data_verification(
        tmp_path, monkeypatch,
):
    _fixture(tmp_path)
    original_verify = migration_helper._semantic_verify
    observed_unqualified = False

    def inspect_verification(bundle, target, inspection, *, require_qualified=True):
        nonlocal observed_unqualified
        if not require_qualified:
            connection = sqlite3.connect(target / 'nfprogress.db')
            try:
                assert connection.execute(
                    'SELECT sync_status FROM mirror_state WHERE id=1',
                ).fetchone()[0] == 'rebuild_required'
                assert connection.execute(
                    "SELECT 1 FROM game_metadata WHERE key='migration_status'",
                ).fetchone() is None
                assert connection.execute(
                    "SELECT 1 FROM document_metadata "
                    "WHERE key='documents_json_migration'",
                ).fetchone() is None
                observed_unqualified = True
            finally:
                connection.close()
        return original_verify(
            bundle,
            target,
            inspection,
            require_qualified=require_qualified,
        )

    monkeypatch.setattr(migration_helper, '_semantic_verify', inspect_verification)
    assert sync_legacy_sqlite_shadow(tmp_path, raise_on_error=True)
    assert observed_unqualified
    _assert_60_qualified(tmp_path)


def test_each_authoritative_bridge_save_requalifies_the_snapshot(tmp_path):
    data, project, stage, documents = _fixture(tmp_path)
    assert sync_legacy_sqlite_shadow(tmp_path, raise_on_error=True)

    data['projects'].pop('P')
    project._name = 'P edited'
    data['projects'][project.name] = project
    data['last'] = project.name
    with engine.data_directory_context(tmp_path):
        engine.save_data(data)
    _assert_60_qualified(tmp_path)
    with sqlite3.connect(tmp_path / 'nfprogress.db') as connection:
        assert connection.execute(
            'SELECT name FROM projects WHERE id=?', (project.project_id,),
        ).fetchone()[0] == 'P edited'

    stage.notes.append(engine.Note(120, 120, 1.2))
    stage._total_symbols = 120
    with engine.data_directory_context(tmp_path):
        engine.save_data(data)
    _assert_60_qualified(tmp_path)
    with sqlite3.connect(tmp_path / 'nfprogress.db') as connection:
        assert connection.execute(
            'SELECT COUNT(*) FROM progress_entries WHERE stage_id=?',
            (stage.stage_id,),
        ).fetchone()[0] == 1

    freeze_day = date(2026, 9, 20)
    data['global_streaks'] = [freeze_day, engine.STREAK_FREEZE_MARKER]
    stage.streaks = [freeze_day, engine.STREAK_FREEZE_MARKER]
    with engine.data_directory_context(tmp_path):
        engine.save_data(data)
    _assert_60_qualified(tmp_path)
    with sqlite3.connect(tmp_path / 'nfprogress.db') as connection:
        payload = json.loads(connection.execute(
            'SELECT payload_json FROM game_state WHERE id=1',
        ).fetchone()[0])
        assert payload['global_streak']['global_streaks'][-1] == engine.STREAK_FREEZE_MARKER
        assert payload['project_game_state'][
            f'stage:{project.project_id}:{stage.stage_id}'
        ]['streaks'][-1] == engine.STREAK_FREEZE_MARKER

    source_key = next(iter(documents))
    documents[source_key]['content'] = _rich_document('edited text')
    _document_service(tmp_path)._write(documents)
    _assert_60_qualified(tmp_path)
    with sqlite3.connect(tmp_path / 'nfprogress.db') as connection:
        assert json.loads(connection.execute(
            'SELECT content_json FROM documents',
        ).fetchone()[0]) == documents[source_key]['content']

    documents[source_key].update({
        'last_synced_hash': 'updated-hash',
        'last_synced_at': '2026-09-20T14:00:00+00:00',
        'sync_state': 'synced',
    })
    _document_service(tmp_path)._write(documents)
    _assert_60_qualified(tmp_path)
    with sqlite3.connect(tmp_path / 'nfprogress.db') as connection:
        binding = connection.execute(
            'SELECT external_path,last_synced_hash,expected_external_hash '
            'FROM document_bindings',
        ).fetchone()
        assert binding == (
            '/tmp/manuscript.docx', 'updated-hash', 'updated-hash',
        )


def test_document_scope_collision_fails_closed_without_deletion(tmp_path):
    _data, project, stage, documents = _fixture(tmp_path)
    assert sync_legacy_sqlite_shadow(tmp_path, raise_on_error=True)
    previous_database = (tmp_path / 'nfprogress.db').read_bytes()
    documents[f'{project.project_id}:project'] = {
        'project_id': project.project_id,
        'stage_id': None,
        'title': 'Project manuscript',
        'content': _rich_document('project-level text'),
        'exists': True,
        'docx_path': '/tmp/project-manuscript.docx',
        'sync_state': 'synced',
        'last_synced_hash': 'project-hash',
        'last_synced_at': '2026-09-20T15:00:00+00:00',
    }
    (tmp_path / 'documents.json').write_text(
        json.dumps(documents, ensure_ascii=False), encoding='utf-8',
    )
    before = _sha256_sources(tmp_path)

    with pytest.raises(HelperError, match='conflicting project/stage document scopes'):
        sync_legacy_sqlite_shadow(tmp_path, raise_on_error=True)

    assert _sha256_sources(tmp_path) == before
    assert (tmp_path / 'nfprogress.db').read_bytes() == previous_database
    assert (tmp_path / 'backups' / 'bridge-preparation-source.json').is_file()
    loaded = _document_service(tmp_path)._load_with_migrations()
    assert set(loaded) == set(documents)
    assert _sha256_sources(tmp_path) == before


def test_empty_documents_source_cannot_replace_nonempty_snapshot(tmp_path):
    _fixture(tmp_path)
    assert sync_legacy_sqlite_shadow(tmp_path, raise_on_error=True)
    previous_database = (tmp_path / 'nfprogress.db').read_bytes()
    (tmp_path / 'documents.json').write_text('{}', encoding='utf-8')

    with pytest.raises(HelperError, match='unexpectedly empty'):
        sync_legacy_sqlite_shadow(tmp_path, raise_on_error=True)

    assert (tmp_path / 'nfprogress.db').read_bytes() == previous_database


def test_qualified_snapshot_passes_projects_read_and_real_to_test_contract(tmp_path):
    real = tmp_path / 'real'
    test = tmp_path / 'test_data'
    real.mkdir()
    test.mkdir()
    _fixture(real)
    assert sync_legacy_sqlite_shadow(real, raise_on_error=True)
    _assert_60_qualified(real)

    with sqlite3.connect(real / 'nfprogress.db') as connection:
        owner = connection.execute(
            "SELECT owner FROM storage_ownership WHERE subsystem='projects'",
        ).fetchone()[0]
        status = connection.execute(
            'SELECT sync_status FROM mirror_state WHERE id=1',
        ).fetchone()[0]
        assert owner == 'sqlite'
        assert status == 'healthy'
        project_order = connection.execute(
            'SELECT project_id,position FROM project_order ORDER BY position',
        ).fetchall()
        assert [position for _project_id, position in project_order] == list(
            range(len(project_order)),
        )
        assert connection.execute(
            'SELECT COUNT(*) FROM projects',
        ).fetchone()[0] == len(project_order)

    source = sqlite3.connect(real / 'nfprogress.db')
    destination = sqlite3.connect(test / 'nfprogress.db')
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    _assert_60_qualified(test)

    tables = (
        'projects', 'stages', 'progress_entries', 'settings', 'game_state',
        'project_bindings', 'documents', 'document_bindings',
        'storage_ownership', 'mirror_state', 'game_metadata',
        'document_metadata',
    )
    real_db = sqlite3.connect(real / 'nfprogress.db')
    test_db = sqlite3.connect(test / 'nfprogress.db')
    try:
        for table in tables:
            assert real_db.execute(
                f'SELECT * FROM {table} ORDER BY rowid',
            ).fetchall() == test_db.execute(
                f'SELECT * FROM {table} ORDER BY rowid',
            ).fetchall()
    finally:
        test_db.close()
        real_db.close()
