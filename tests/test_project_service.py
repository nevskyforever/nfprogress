from __future__ import annotations

from datetime import date, timedelta

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


def test_stage_order_requires_complete_permutation(service):
    project = service.create_project({'name': 'Book', 'goal': 1000, 'unit': 'symbols'})
    first = service.create_stage(project['id'], {'name': 'One', 'goal': 500})
    second = service.create_stage(project['id'], {'name': 'Two', 'goal': 500})

    reordered = service.reorder_stages(project['id'], [second['id'], first['id']])
    assert [stage['id'] for stage in reordered['stages']] == [second['id'], first['id']]

    with pytest.raises(ValidationError):
        service.reorder_stages(project['id'], [first['id']])


def test_repository_does_not_touch_default_legacy_location(service, monkeypatch):
    monkeypatch.setattr(engine, 'save_data', lambda _data: pytest.fail('legacy save called'))
    project = service.create_project({'name': 'Isolated', 'goal': 100, 'unit': 'symbols'})
    assert project['name'] == 'Isolated'
