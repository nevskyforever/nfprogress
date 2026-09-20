from __future__ import annotations

import json
import pickle
import sqlite3
from datetime import date

import engine
import game

from nfprogress.core.legacy_shadow import (
    reconcile_legacy_sqlite_shadow,
    sync_legacy_sqlite_shadow,
)
from nfprogress.core.sqlite import SQLiteMirrorRepository
from nfprogress.core.sqlite.connection import open_database


def _payload(root):
    with open_database(root) as database:
        state = database.execute(
            'SELECT sync_status,last_error FROM mirror_state WHERE id=1',
        ).fetchone()
        game_payload = json.loads(database.execute(
            'SELECT payload_json FROM game_state WHERE id=1',
        ).fetchone()[0])
        owners = dict(database.execute(
            'SELECT subsystem,owner FROM storage_ownership',
        ))
    return state, game_payload, owners


def _legacy_data(project=None):
    projects = {project.name: project} if project is not None else {}
    return {
        'projects': projects,
        'last': project.name if project is not None else None,
        'notifications': [],
        'global_streaks': [],
        'global_streak_status': 'No',
        'max_global_streak': 0,
    }


def test_legacy_save_paths_immediately_refresh_healthy_pickle_owned_mirror(tmp_path):
    project = engine.Project('Bridge', 100)
    data = _legacy_data(project)
    with engine.data_directory_context(tmp_path):
        engine.save_data(data)
        state, _game_payload, owners = _payload(tmp_path)
        assert state['sync_status'] == 'healthy'
        assert set(owners.values()) == {'pickle'}

        engine.save_settings({'language': 'de', 'bridge': 'new'})
        with open_database(tmp_path) as database:
            assert json.loads(database.execute(
                "SELECT value_json FROM settings WHERE key='bridge'",
            ).fetchone()[0]) == 'new'
            assert database.execute(
                'SELECT sync_status FROM mirror_state WHERE id=1',
            ).fetchone()[0] == 'healthy'

        gamer = game.Gamer()
        gamer.coins += 17
        gamer.save()
        _state, game_payload, _owners = _payload(tmp_path)
        assert game_payload['gamer']['coins'] == gamer.coins


def test_global_and_local_freeze_are_projected_with_tagged_dates(tmp_path):
    freeze_day = date(2026, 9, 20)
    project = engine.Project('Frozen', 100)
    stage = engine.Stage('Frozen stage', 100, parent_project_name=project.name)
    project.streaks = [freeze_day, engine.STREAK_FREEZE_MARKER]
    stage.streaks = [freeze_day, engine.STREAK_FREEZE_MARKER]
    project.stages = [stage]
    project.enable_stages = True
    data = _legacy_data(project)
    data['global_streaks'] = [freeze_day, engine.STREAK_FREEZE_MARKER]

    with engine.data_directory_context(tmp_path):
        engine.save_data(data)

    state, payload, _owners = _payload(tmp_path)
    assert state['sync_status'] == 'healthy'
    tagged = {'__type__': 'date', 'value': freeze_day.isoformat()}
    assert payload['global_streak']['global_streaks'] == [
        tagged, engine.STREAK_FREEZE_MARKER,
    ]
    project_key = f'project:{project.project_id}'
    assert payload['project_game_state'][project_key]['streaks'] == [
        tagged, engine.STREAK_FREEZE_MARKER,
    ]
    stage_key = f'stage:{project.project_id}:{stage.stage_id}'
    assert payload['project_game_state'][stage_key]['streaks'] == [
        tagged, engine.STREAK_FREEZE_MARKER,
    ]


def test_failed_sync_keeps_new_pickle_marks_dirty_and_retries(tmp_path, monkeypatch):
    with engine.data_directory_context(tmp_path):
        engine.save_data(_legacy_data())
        replacement = _legacy_data()
        replacement['bridge_value'] = 'new-pickle'
        original = SQLiteMirrorRepository.rebuild

        def fail(*_args, **_kwargs):
            raise sqlite3.OperationalError('disk full')

        monkeypatch.setattr(SQLiteMirrorRepository, 'rebuild', fail)
        engine.save_data(replacement)
        with (tmp_path / 'data.pkl').open('rb') as stream:
            assert pickle.load(stream)['bridge_value'] == 'new-pickle'
        with open_database(tmp_path) as database:
            state = database.execute(
                'SELECT sync_status,last_error FROM mirror_state WHERE id=1',
            ).fetchone()
            assert state['sync_status'] == 'dirty'
            assert 'disk full' in state['last_error']

        monkeypatch.setattr(SQLiteMirrorRepository, 'rebuild', original)
        engine.save_settings({'retry': True})
        state, payload, _owners = _payload(tmp_path)
        assert state['sync_status'] == 'healthy'
        assert payload['extensions']['bridge_value'] == 'new-pickle'


def test_startup_heals_stale_dirty_or_missing_mirror_without_replacing_pickle(tmp_path):
    data = _legacy_data()
    data['bridge_value'] = 'authoritative'
    with engine.data_directory_context(tmp_path):
        engine.atomic_pickle_save(data, engine.get_data_file_path('data'))
        engine.atomic_pickle_save({'language': 'ru'}, engine.get_data_file_path('settings'))
        engine.atomic_pickle_save(game.Gamer(), engine.get_data_file_path('gamer'))
    original_bytes = {
        path.name: path.read_bytes() for path in tmp_path.glob('*.pkl')
    }

    with open_database(tmp_path) as database:
        database.execute(
            "INSERT INTO mirror_state(id,source_format,source_schema_version,sync_status,last_error) "
            "VALUES(1,'pickle','legacy','dirty','stale') "
            "ON CONFLICT(id) DO UPDATE SET sync_status='dirty',last_error='stale'",
        )
        database.commit()
    assert reconcile_legacy_sqlite_shadow(tmp_path)
    state, payload, _owners = _payload(tmp_path)
    assert state['sync_status'] == 'healthy'
    assert payload['extensions']['bridge_value'] == 'authoritative'
    assert original_bytes == {
        path.name: path.read_bytes() for path in tmp_path.glob('*.pkl')
    }

    (tmp_path / 'nfprogress.db').unlink()
    assert sync_legacy_sqlite_shadow(tmp_path)
    assert (tmp_path / 'nfprogress.db').is_file()
    assert _payload(tmp_path)[0]['sync_status'] == 'healthy'


def test_nested_gamer_save_during_rebuild_does_not_recurse(tmp_path, monkeypatch):
    gamer = game.Gamer()
    with engine.data_directory_context(tmp_path):
        engine.atomic_pickle_save(_legacy_data(), engine.get_data_file_path('data'))
        engine.atomic_pickle_save({}, engine.get_data_file_path('settings'))

    rebuilds = 0
    original_rebuild = SQLiteMirrorRepository.rebuild

    def counted_rebuild(self, *args, **kwargs):
        nonlocal rebuilds
        rebuilds += 1
        return original_rebuild(self, *args, **kwargs)

    original_load_data = engine.load_data

    def load_and_migrate():
        gamer.save()
        return original_load_data()

    monkeypatch.setattr(SQLiteMirrorRepository, 'rebuild', counted_rebuild)
    monkeypatch.setattr(engine, 'load_data', load_and_migrate)
    with engine.data_directory_context(tmp_path):
        assert sync_legacy_sqlite_shadow(tmp_path)
    assert rebuilds == 1
