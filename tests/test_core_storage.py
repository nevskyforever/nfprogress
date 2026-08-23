from __future__ import annotations

import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import engine
import game
import pytest

from nfprogress.core.serialization import (
    serialize_note,
    serialize_project,
    serialize_stage,
    to_json_safe,
)
from nfprogress.core.storage import PickleRepository


def test_repository_uses_only_explicit_base_dir_and_restores_context(
        tmp_path, monkeypatch):
    isolated_dir = tmp_path / 'isolated'
    default_dir = tmp_path / 'legacy-default'
    monkeypatch.setattr(engine, 'dev_mode', True)
    monkeypatch.setattr(engine, 'get_test_data_dir', lambda: default_dir)
    repository = PickleRepository(isolated_dir)

    repository.write_projects({'projects': {}, 'last': 'isolated'})

    assert (isolated_dir / 'data.pkl').is_file()
    assert not default_dir.exists()
    assert engine.get_data_file_path('data') == default_dir / 'data.pkl'


def test_projects_round_trip_and_atomic_update_return_value(tmp_path):
    repository = PickleRepository(tmp_path)
    repository.write_projects({'projects': {}, 'last': None, 'counter': 0})

    def increment(data):
        data['counter'] += 1
        return f"version-{data['counter']}"

    assert repository.update_projects(increment) == 'version-1'
    assert repository.read_projects()['counter'] == 1
    assert not list(tmp_path.glob('*.tmp'))


def test_failed_project_update_does_not_replace_saved_data(tmp_path):
    repository = PickleRepository(tmp_path)
    repository.write_projects({'projects': {}, 'counter': 1})

    def fail_after_mutation(data):
        data['counter'] = 99
        raise RuntimeError('stop')

    with pytest.raises(RuntimeError, match='stop'):
        repository.update_projects(fail_after_mutation)

    assert repository.read_projects()['counter'] == 1


def test_repository_lock_serializes_concurrent_updates(tmp_path):
    repository = PickleRepository(tmp_path)
    repository.write_projects({'projects': {}, 'counter': 0})

    def increment(_index):
        repository.update_projects(
            lambda data: data.__setitem__('counter', data['counter'] + 1),
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(increment, range(30)))

    assert repository.read_projects()['counter'] == 30


def test_repository_instances_share_a_directory_lock(tmp_path):
    repositories = [PickleRepository(tmp_path) for _ in range(3)]
    repositories[0].write_projects({'projects': {}, 'counter': 0})

    def increment(index):
        repositories[index % len(repositories)].update_projects(
            lambda data: data.__setitem__('counter', data['counter'] + 1),
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(increment, range(30)))

    assert repositories[0].read_projects()['counter'] == 30


def test_legacy_entity_ids_are_stable_before_migration_is_saved(tmp_path):
    repository = PickleRepository(tmp_path)
    project = engine.Project(name='Старый проект', goal=100)
    stage = engine.Stage(name='Старый этап', goal=100)
    del project.project_id
    del stage.project_id
    del stage.stage_id
    project.enable_stages = True
    project.stages = [stage]
    repository.write_projects({
        'projects': {project.name: project},
        'last': project.name,
    })

    first = repository.read_projects()['projects'][project.name]
    second = repository.read_projects()['projects'][project.name]

    assert first.project_id == second.project_id
    assert first.stages[0].stage_id == second.stages[0].stage_id


def test_settings_and_embedded_game_save_stay_in_repository_context(tmp_path):
    repository = PickleRepository(tmp_path)
    settings = {'game_mode': True, 'start_day_time': '00:00:00'}
    repository.write_settings(settings)
    assert repository.read_settings() == settings

    gamer = game.Gamer(level=3, coins=42)
    with repository.locked():
        gamer.save()

    restored = repository.read_gamer()
    assert restored.level == 3
    assert restored.coins == 42
    assert (tmp_path / 'gamer.pkl').is_file()


def test_settings_updates_share_the_repository_transaction_lock(tmp_path):
    repository = PickleRepository(tmp_path)
    repository.write_settings({'counter': 0})

    def increment(_index):
        repository.update_settings(
            lambda settings: settings.__setitem__(
                'counter', settings['counter'] + 1,
            ),
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(increment, range(30)))

    assert repository.read_settings()['counter'] == 30


def test_timestamped_backup_copies_without_removing_source(tmp_path):
    repository = PickleRepository(tmp_path)
    original = {'projects': {'sentinel': 'unchanged'}}
    repository.write_projects(original)
    source_bytes = (tmp_path / 'data.pkl').read_bytes()

    backup_dir = repository.create_backup('data')

    assert backup_dir.parent == tmp_path / 'backups'
    assert backup_dir.name.endswith('Z')
    assert (backup_dir / 'data.pkl').read_bytes() == source_bytes
    assert (tmp_path / 'data.pkl').read_bytes() == source_bytes
    assert pickle.loads(source_bytes) == original


def test_json_safe_values_are_strictly_serializable():
    payload = to_json_safe({
        'created': datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc),
        'day': date(2026, 1, 2),
        'values': (1, float('inf'), float('-inf'), float('nan')),
    })

    assert payload == {
        'created': '2026-01-02T03:04:00+00:00',
        'day': '2026-01-02',
        'values': [1, None, None, None],
    }
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_project_stage_and_progress_projections_are_json_safe(tmp_path):
    repository = PickleRepository(tmp_path)
    with repository.storage_context():
        project = engine.Project(name='Дневник', goal=float('inf'), unit='symbols')
        stage = engine.Stage(
            name='Черновик',
            goal=float('inf'),
            unit='symbols',
            parent_project_name=project.name,
        )
        entry = engine.Note(
            new_total=500,
            added_symbols=500,
            added_progress=25,
            date_create=datetime(2026, 1, 2, 12, 30),
        )
        stage.set_new_notes(entry)
        project.enable_stages = True
        project.stages = [stage]

        project_payload = serialize_project(project)
        stage_payload = serialize_stage(stage)
        entry_payload = serialize_note(entry, 'symbols')

    assert project_payload['id'] == project.project_id
    assert project_payload['goal'] is None
    assert project_payload['infinite'] is True
    assert project_payload['stages'][0]['id'] == stage.stage_id
    assert project_payload['streak_status'] == 'No'
    assert project_payload['streak_length'] == 0
    assert project_payload['max_streak'] == 0
    assert stage_payload['total'] == 500
    assert entry_payload['id'] == entry.entry_id
    assert entry_payload['new_total_symbols'] == 500
    json.dumps(project_payload, ensure_ascii=False, allow_nan=False)


def test_project_projection_uses_legacy_cumulative_today_goal(monkeypatch):
    today = date(2026, 8, 25)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = engine.Project(name='Роман', goal=5_000, total_symbols=2_000)
    stage = engine.Stage(
        name='Глава',
        goal=5_000,
        total_symbols=2_153,
        deadline=today + timedelta(days=2),
        personal_goal_for_the_day=500,
        parent_project_name=project.name,
    )
    project.enable_stages = True
    project.stages = [stage]

    project_payload = serialize_project(project)
    stage_payload = serialize_stage(stage)

    # Legacy displays the cumulative target (current value at day start + plan),
    # not the configured daily increment stored in personal_goal.
    assert stage_payload['personal_goal'] == 500
    assert stage_payload['today_goal'] == 2_653
    assert project_payload['today_goal'] == 2_653
