from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

import engine
from nfprogress.core.errors import ConflictError, ValidationError
from nfprogress.core.repositories.storage import PickleRepository
from nfprogress.core.services.projects import ProjectService


@pytest.fixture
def service(tmp_path):
    return ProjectService(PickleRepository(tmp_path))


def test_project_stage_progress_and_statistics_round_trip(service):
    project = service.create_project({
        'name': 'Роман',
        'goal': 10_000,
        'unit': 'symbols',
        'deadline': (date.today() + timedelta(days=30)).isoformat(),
    })
    stage = service.create_stage(project['id'], {
        'name': 'Черновик',
        'goal': 5_000,
        'unit': 'symbols',
    })

    result = service.record_progress(
        project['id'], stage_id=stage['id'], new_total=1_250,
    )
    stats = service.statistics(project['id'], stage_id=stage['id'])

    assert result['added_symbols'] == 1_250
    assert result['project']['stages'][0]['total'] == 1_250
    assert result['entry']['id']
    assert stats['metrics']['entries_count'] == 1
    assert stats['metrics']['best_day']['date'] == engine.today_for_test().isoformat()
    assert stats['metrics']['best_weekday']['weekday'] == engine.today_for_test().weekday()
    assert isinstance(stats['metrics']['active_days_percent'], float)
    assert stats['timeline'][0]['symbols'] == 1_250


def test_today_summary_uses_legacy_project_and_stage_totals(service, monkeypatch):
    today = date(2026, 8, 23)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = service.create_project({
        'name': 'Обычный', 'goal': 1_000, 'unit': 'symbols',
    })
    staged = service.create_project({
        'name': 'По этапам', 'goal': 1_000, 'unit': 'symbols',
    })
    stage = service.create_stage(staged['id'], {
        'name': 'Черновик', 'goal': 1_000, 'unit': 'symbols',
    })

    service.record_progress(project['id'], new_total=125)
    service.record_progress(staged['id'], stage_id=stage['id'], new_total=250)

    summary = service.today_summary()

    assert summary['date'] == today.isoformat()
    assert summary['symbols'] == 375
    assert {item['name']: item['symbols'] for item in summary['projects']} == {
        'Обычный': 125,
        'По этапам': 250,
    }


def test_project_names_are_unique_and_lookup_uses_stable_id(service):
    first = service.create_project({'name': 'A', 'goal': 100, 'unit': 'symbols'})
    with pytest.raises(ConflictError):
        service.create_project({'name': 'A', 'goal': 200, 'unit': 'symbols'})

    renamed = service.update_project(first['id'], {'name': 'B'})

    assert renamed['id'] == first['id']
    assert service.get_project(first['id'])['name'] == 'B'


def test_infinite_goal_is_json_safe_and_cannot_complete(service):
    project = service.create_project({
        'name': 'Дневник', 'infinite': True, 'unit': 'symbols',
    })

    assert project['infinite'] is True
    assert project['goal'] is None
    with pytest.raises(ValidationError):
        service.complete_project(project['id'])


def test_progress_is_server_calculated_and_deletable(service):
    project = service.create_project({'name': 'Text', 'goal': 1000, 'unit': 'symbols'})
    first = service.record_progress(project['id'], new_total=400)
    second = service.record_progress(project['id'], new_total=250)

    assert first['added_symbols'] == 400
    assert second['added_symbols'] == -150

    updated = service.delete_progress(project['id'], second['entry']['id'])
    assert updated['total'] == 400
    assert len(updated['progress_entries']) == 1


def test_synchronized_entity_rejects_manual_progress_but_accepts_sync_result(service):
    project = service.create_project({'name': 'Synced', 'goal': 1_000, 'unit': 'symbols'})

    def configure_sync(data):
        service._find_project(data, project['id']).synch = {
            'type': 'word',
            'path': '/tmp/manuscript.docx',
        }

    service.repository.update_projects(configure_sync)

    with pytest.raises(ValidationError, match='Ручная запись прогресса недоступна'):
        service.record_progress(project['id'], new_total=400)

    result = service.record_synchronized_progress(
        project['id'], new_total=400, source_modified_at=datetime.now(),
    )
    assert result['project']['total'] == 400


def test_stage_order_requires_complete_permutation(service):
    project = service.create_project({'name': 'Book', 'goal': 1000, 'unit': 'symbols'})
    first = service.create_stage(project['id'], {'name': 'One', 'goal': 500})
    second = service.create_stage(project['id'], {'name': 'Two', 'goal': 500})

    reordered = service.reorder_stages(project['id'], [second['id'], first['id']])
    assert [stage['id'] for stage in reordered['stages']] == [second['id'], first['id']]

    with pytest.raises(ValidationError):
        service.reorder_stages(project['id'], [first['id']])


def test_stage_conversion_preserves_initial_total_history_and_entry_ids(service):
    project = service.create_project({
        'name': 'Book', 'goal': 1_000, 'total': 200, 'unit': 'symbols',
        'stages_enabled': True,
    })

    assert project['stages_enabled'] is True
    assert project['total'] == 200
    assert project['stages'][0]['total'] == 200

    progress = service.record_progress(
        project['id'], stage_id=project['stages'][0]['id'], new_total=450,
    )
    entry_id = progress['entry']['id']
    converted = service.update_project(project['id'], {'stages_enabled': False})

    assert converted['stages_enabled'] is False
    assert converted['total'] == 450
    assert converted['progress_entries'][0]['id'] == entry_id
    assert converted['progress_entries'][0]['new_total'] == 450


def test_unit_conversion_includes_daily_goals(service):
    project = service.create_project({
        'name': 'Book',
        'goal': 80_000,
        'total': 40_000,
        'personal_goal': 4_000,
        'unit': 'symbols',
        'stages_enabled': True,
    })

    converted = service.update_project(project['id'], {'unit': 'author_list'})

    assert converted['personal_goal'] == pytest.approx(0.1)
    assert converted['stages'][0]['personal_goal'] == pytest.approx(0.1)
    assert converted['stages'][0]['total'] == pytest.approx(1)


def test_infinite_stage_cannot_be_completed_and_completed_project_cannot_reorder(service):
    project = service.create_project({
        'name': 'Series',
        'goal': 100,
        'unit': 'symbols',
        'stages': [
            {'name': 'Done', 'goal': 100, 'total': 100},
            {'name': 'Open', 'infinite': True},
        ],
    })
    infinite_stage = project['stages'][1]

    with pytest.raises(ValidationError, match='Бесконечный этап'):
        service.complete_stage(project['id'], infinite_stage['id'])

    finite_project = service.create_project({
        'name': 'Finite',
        'goal': 100,
        'unit': 'symbols',
        'stages': [
            {'name': 'One', 'goal': 50, 'total': 50},
            {'name': 'Two', 'goal': 50, 'total': 50},
        ],
    })
    service.complete_project(finite_project['id'])
    with pytest.raises(ValidationError, match='только для просмотра'):
        service.reorder_stages(
            finite_project['id'],
            [stage['id'] for stage in reversed(finite_project['stages'])],
        )


def test_shared_project_sources_are_infinite_and_lifecycle_is_protected(service):
    project = service.create_project({
        'name': 'Общий проект', 'infinite': True, 'unit': 'symbols',
    })
    source = service.create_stage(project['id'], {
        'name': 'Источник 1', 'goal': 500, 'total': 0,
    })

    assert source['infinite'] is True
    assert source['goal'] is None
    with pytest.raises(ValidationError, match='не редактируются'):
        service.update_stage(project['id'], source['id'], {'name': 'Other'})
    with pytest.raises(ValidationError, match='только в настройках'):
        service.delete_project(project['id'])
    with pytest.raises(ValidationError, match='нельзя архивировать'):
        service.set_project_archived(project['id'], True)


def test_repository_does_not_touch_default_legacy_location(service, monkeypatch):
    monkeypatch.setattr(engine, 'save_data', lambda _data: pytest.fail('legacy save called'))
    project = service.create_project({'name': 'Isolated', 'goal': 100, 'unit': 'symbols'})
    assert project['name'] == 'Isolated'
