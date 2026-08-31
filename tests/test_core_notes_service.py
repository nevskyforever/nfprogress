from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

import engine
from nfprogress.core.errors import NotFoundError, ValidationError
from nfprogress.core.services.notes import (
    ProjectNotesService,
    extract_mindmap_notes,
    note_html_to_plain_text,
    sanitize_note_html,
)


class MemoryProjectsRepository:
    """Exercise the same copy-on-read boundary as pickle persistence."""

    def __init__(self, *projects: engine.Project) -> None:
        self.data = {
            'projects': {project.name: deepcopy(project) for project in projects},
        }
        self.write_count = 0
        self.update_count = 0

    def read_projects(self) -> dict:
        return deepcopy(self.data)

    def write_projects(self, data: dict) -> None:
        self.data = deepcopy(data)
        self.write_count += 1

    def update_projects(self, mutator):
        data = deepcopy(self.data)
        result = mutator(data)
        self.data = data
        self.update_count += 1
        return deepcopy(result)

    def project(self, project_id: str) -> engine.Project:
        return next(
            project for project in self.data['projects'].values()
            if project.project_id == project_id
        )


def _map_data(note_id: str = 'map-note', text: str = 'Текст карты') -> dict:
    return {
        'nodeData': {
            'id': 'root-node',
            'topic': 'Роман',
            'children': [
                {'id': 'scene-node', 'topic': 'Сцена', 'children': []},
            ],
        },
        'freeNodes': [
            {
                'id': note_id,
                'topic': text,
                'children': [],
                'position': {'x': 320, 'y': 180},
                'nfprogressFreeRoot': True,
                'nfprogressNote': True,
            },
        ],
        'arrows': [
            {
                'id': f'link-{note_id}',
                'from': note_id,
                'to': 'scene-node',
                'label': '',
            },
        ],
        'summaries': [],
    }


def _record(note_id: str, title: str, *, order: int = 0) -> dict:
    return {
        'id': note_id,
        'title': title,
        'content': f'<p>{title}</p>',
        'sort_order': order,
        'source_type': 'project',
    }


def test_regular_note_crud_normalizes_sanitizes_and_orders_records():
    project = engine.Project(name='Book', goal=1000)
    outside = engine.Project(name='Outside', goal=1000)
    repository = MemoryProjectsRepository(project, outside)
    service = ProjectNotesService(repository, project.project_id)

    assert service.load_notes() == {
        'notes': [],
        'read_only': False,
        'context': {'hasStages': False, 'stages': []},
    }
    first = service.create_note()
    second = service.create_note()
    updated = service.update_note(first['id'], {
        'title': 'План\x00',
        'content': (
            '<p onclick="bad()">Безопасно <strong>важно</strong>'
            '<script>alert(1)</script>'
            '<a href="javascript:bad()">плохо</a>'
            '<a href="https://example.com/note">ссылка</a></p>'
        ),
        'tags': [' Сюжет ', '#карта', 'сюжет', None],
        'color': 'blue',
        'pinned': True,
        'checklist': [
            {'id': 'check', 'text': 'Проверить', 'checked': True},
            {'id': 'check', 'text': 'Повтор', 'checked': False},
        ],
    })

    assert updated['title'] == 'План'
    assert updated['tags'] == ['Сюжет']
    assert updated['system_tags'] == []
    assert updated['color'] == 'blue'
    assert updated['pinned'] is True
    assert len({item['id'] for item in updated['checklist']}) == 2
    assert '<script>' not in updated['content']
    assert 'onclick' not in updated['content']
    assert 'javascript:' not in updated['content']
    assert '<strong>важно</strong>' in updated['content']
    assert 'href="https://example.com/note"' in updated['content']
    assert note_html_to_plain_text(updated['content']).startswith(
        'Безопасно важноalert(1)плохо',
    )

    reordered = service.update_order([second['id'], first['id']])
    assert reordered['changed'] is True
    stored = repository.project(project.project_id)
    order_by_id = {
        record['id']: record['sort_order'] for record in stored.project_notes
    }
    assert order_by_id == {first['id']: 1, second['id']: 0}
    assert repository.project(outside.project_id).project_notes == []

    deleted = service.delete_note(first['id'])
    assert deleted['deleted'] is True
    assert service.get_note(first['id']) is None
    json.dumps(service.load_notes(), ensure_ascii=False, allow_nan=False)


def test_mindmap_note_reconciliation_is_two_way_for_text_and_delete():
    project = engine.Project(name='Book', goal=1000)
    project.mindmap_data = _map_data()
    repository = MemoryProjectsRepository(project)
    service = ProjectNotesService(repository, project.project_id)

    loaded = service.load_notes()
    assert repository.update_count == 1
    map_card = loaded['notes'][0]
    assert map_card['content'] == 'Текст карты'
    assert map_card['source_map_id'] == 'root-node'
    assert map_card['system_tags'] == ['карта']
    assert repository.project(project.project_id).project_notes[0]['content'] == ''

    updated = service.update_note(
        map_card['id'],
        {'content': 'Из карточки', 'title': 'Отдельный заголовок'},
    )
    stored = repository.project(project.project_id)
    assert extract_mindmap_notes(stored.mindmap_data) == [
        {'id': 'map-note', 'text': 'Из карточки'},
    ]
    assert updated['display_title'] == 'Отдельный заголовок'
    assert service.consume_map_commands() == [{
        'command': 'update',
        'node_id': 'map-note',
        'text': 'Из карточки',
    }]

    changed_map = deepcopy(stored.mindmap_data)
    changed_map['freeNodes'][0]['topic'] = 'Из редактора карты'
    map_result = service.update_mindmap(changed_map)
    assert map_result['notes'][0]['content'] == 'Из редактора карты'
    assert repository.project(project.project_id).project_notes[0]['revision'] == 2

    deleted = service.delete_note(map_card['id'])
    assert deleted['deleted'] is True
    stored = repository.project(project.project_id)
    assert extract_mindmap_notes(stored.mindmap_data) == []
    assert stored.mindmap_data['arrows'] == []
    assert stored.project_notes == []
    assert service.consume_map_commands() == [{
        'command': 'delete',
        'node_id': 'map-note',
        'text': '',
    }]

    recreated_map = _map_data(text='Вернулась')
    recreated = service.update_mindmap(recreated_map)
    assert len(recreated['notes']) == 1
    without_note = deepcopy(recreated_map)
    without_note['freeNodes'] = []
    without_note['arrows'] = []
    removed_from_map = service.update_mindmap(without_note)
    assert removed_from_map['notes'] == []
    assert repository.project(project.project_id).project_notes == []


def test_resource_change_timestamps_are_kept_for_empty_resources(monkeypatch):
    monkeypatch.setattr(
        'nfprogress.core.services.notes._now_iso',
        lambda: '2026-09-01T12:00:00+00:00',
    )
    project = engine.Project(name='Book', goal=1000)
    repository = MemoryProjectsRepository(project)
    service = ProjectNotesService(repository, project.project_id)

    service.update_mindmap({
        'nodeData': {'id': 'root', 'topic': 'Book', 'children': []},
    })
    stored = repository.project(project.project_id)
    assert stored.mindmap_updated_at == '2026-09-01T12:00:00+00:00'

    note = service.create_note()
    assert repository.project(project.project_id).notes_updated_at == '2026-09-01T12:00:00+00:00'
    service.delete_note(note['id'])
    stored = repository.project(project.project_id)
    assert stored.notes_updated_at == '2026-09-01T12:00:00+00:00'
    assert stored.project_notes == []


def test_project_view_uses_aggregate_ids_and_routes_stage_mutations():
    draft = engine.Stage(
        name='Черновик',
        goal=1000,
        parent_project_name='Book',
        stage_id='draft-stage',
    )
    draft.project_notes = engine.normalize_project_note_records([
        _record('shared', 'Черновик'),
    ])
    completed = engine.Stage(
        name='Редактура',
        goal=1000,
        status='завершен',
        parent_project_name='Book',
        stage_id='editing-stage',
    )
    completed.project_notes = engine.normalize_project_note_records([
        _record('shared', 'Редактура'),
    ])
    project = engine.Project(name='Book', goal=2000)
    project.enable_stages = True
    project.stages = [draft, completed]
    repository = MemoryProjectsRepository(project)
    service = ProjectNotesService(repository, project.project_id)

    payload = service.load_notes()
    assert payload['context'] == {
        'hasStages': True,
        'stages': [
            {'id': 'draft-stage', 'name': 'Черновик'},
            {'id': 'editing-stage', 'name': 'Редактура'},
        ],
    }
    assert {note['id'] for note in payload['notes']} == {
        'stage:draft-stage:shared',
        'stage:editing-stage:shared',
    }
    assert {note['owner_order'] for note in payload['notes']} == {1, 2}
    editing_card = next(
        note for note in payload['notes']
        if note['owner_id'] == 'editing-stage'
    )
    assert editing_card['read_only'] is True
    with pytest.raises(ValidationError):
        service.update_note(editing_card['id'], {'title': 'Нельзя'})

    draft_card = next(
        note for note in payload['notes']
        if note['owner_id'] == 'draft-stage'
    )
    updated = service.update_note(draft_card['id'], {'title': 'Новый план'})
    assert updated['stage_name'] == 'Черновик'
    assert updated['title'] == 'Новый план'
    assert service.get_map_target(draft_card['id']) is None

    project_card = service.create_note()
    assert project_card['id'].startswith(f'project:{project.project_id}:')
    assert project_card['owner_type'] == 'project'
    completed_service = ProjectNotesService(
        repository,
        project.project_id,
        stage_id='editing-stage',
    )
    assert completed_service.load_notes()['read_only'] is True
    with pytest.raises(ValidationError):
        completed_service.create_note()
    json.dumps(service.load_notes(), ensure_ascii=False, allow_nan=False)


def test_combined_map_updates_active_stage_but_preserves_completed_stage():
    active = engine.Stage(
        name='Draft',
        goal=1000,
        parent_project_name='Book',
        stage_id='draft-stage',
    )
    active.mindmap_data = {
        'nodeData': {
            'id': 'draft-root',
            'topic': 'Draft plan',
            'children': [
                {'id': 'draft-scene', 'topic': 'Scene', 'children': []},
            ],
        },
    }
    completed = engine.Stage(
        name='Editing',
        goal=1000,
        status='завершен',
        parent_project_name='Book',
        stage_id='editing-stage',
    )
    completed.mindmap_data = {
        'nodeData': {
            'id': 'editing-root',
            'topic': 'Editing plan',
            'children': [
                {'id': 'editing-scene', 'topic': 'Check', 'children': []},
            ],
        },
    }
    project = engine.Project(name='Book', goal=2000)
    project.mindmap_data = {
        'nodeData': {'id': 'project-root', 'topic': 'Book', 'children': []},
    }
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [active, completed]
    repository = MemoryProjectsRepository(project)
    service = ProjectNotesService(repository, project.project_id)

    payload = service.get_mindmap()
    assert payload['combined'] is True
    branches = {
        branch['nfprogressStageId']: branch
        for branch in payload['data']['nodeData']['children']
    }
    branches['draft-stage']['children'].append({
        'id': 'new-active-node',
        'topic': 'New scene',
        'children': [],
    })
    branches['editing-stage']['children'].append({
        'id': 'forbidden-node',
        'topic': 'Must not persist',
        'children': [],
    })

    result = service.update_mindmap(payload['data'])
    stored = repository.project(project.project_id)
    stored_active = next(
        stage for stage in stored.stages if stage.stage_id == 'draft-stage'
    )
    stored_completed = next(
        stage for stage in stored.stages if stage.stage_id == 'editing-stage'
    )
    assert any(
        child['topic'] == 'New scene'
        for child in stored_active.mindmap_data['nodeData']['children']
    )
    assert all(
        child['topic'] != 'Must not persist'
        for child in stored_completed.mindmap_data['nodeData']['children']
    )
    assert result['combined'] is True
    json.dumps(result, ensure_ascii=False, allow_nan=False)


def test_service_uses_stable_ids_and_has_no_qt_or_localization_runtime():
    project = engine.Project(name='Same name', goal=1000)
    repository = MemoryProjectsRepository(project)
    service = ProjectNotesService(repository, project.project_id)
    replacement = engine.Project(name='Same name', goal=1000)
    repository.data['projects']['Same name'] = replacement

    with pytest.raises(NotFoundError, match='Проект больше не существует'):
        service.load_notes()

    source = Path(ProjectNotesService.__module__.replace('.', '/'))
    source = Path(__file__).resolve().parents[1] / source.with_suffix('.py')
    module_text = source.read_text(encoding='utf-8')
    assert 'PySide6' not in module_text
    assert 'QObject' not in module_text
    assert 'Signal' not in module_text
    assert 'localization' not in module_text
    assert sanitize_note_html('<b>ok</b>') == '<b>ok</b>'
