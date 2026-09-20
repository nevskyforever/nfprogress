from __future__ import annotations

import json
from datetime import date

import engine
import game

from nfprogress.core.legacy_shadow import sync_legacy_sqlite_shadow
from nfprogress.core.sqlite.connection import open_database
from nfprogress.migration_helper import (
    OUTCOME_MIGRATION_VERIFIED,
    main,
    verify_prepared_profile,
)


def _data(project, *, marker: str):
    return {
        'projects': {project.name: project},
        'last': project.name,
        'notifications': [],
        'global_streaks': [],
        'global_streak_status': 'No',
        'max_global_streak': 0,
        'bridge_marker': marker,
    }


def test_dirty_real_sqlite_is_ignored_when_refreshing_test_from_legacy_sources(
        tmp_path, capsys, monkeypatch,
):
    real = tmp_path / 'real'
    test = tmp_path / 'test'
    real.mkdir()
    test.mkdir()

    project = engine.Project('Authoritative', 500)
    stale = _data(project, marker='old-sqlite')
    with engine.data_directory_context(real):
        engine.atomic_pickle_save(stale, engine.get_data_file_path('data'))
        engine.atomic_pickle_save({'bridge_setting': 'old'}, engine.get_data_file_path('settings'))
        stale_gamer = game.Gamer()
        stale_gamer.coins = 1
        engine.atomic_pickle_save(stale_gamer, engine.get_data_file_path('gamer'))
    (real / 'documents.json').write_text('{}', encoding='utf-8')
    assert sync_legacy_sqlite_shadow(real)

    freeze_day = date(2026, 9, 20)
    project.streaks = [freeze_day, engine.STREAK_FREEZE_MARKER]
    current = _data(project, marker='new-pickle')
    current['global_streaks'] = [freeze_day, engine.STREAK_FREEZE_MARKER]
    current_gamer = game.Gamer()
    current_gamer.coins = 777
    document = {
        f'{project.project_id}:project': {
            'project_id': project.project_id,
            'stage_id': None,
            'title': 'Current document',
            'content': {
                'type': 'doc',
                'content': [{'type': 'paragraph', 'content': [
                    {'type': 'text', 'text': 'new document'},
                ]}],
            },
            'exists': True,
            'updated_at': '2026-09-20T12:00:00+00:00',
        },
    }
    with engine.data_directory_context(real):
        engine.atomic_pickle_save(current, engine.get_data_file_path('data'))
        engine.atomic_pickle_save({'bridge_setting': 'new'}, engine.get_data_file_path('settings'))
        engine.atomic_pickle_save(current_gamer, engine.get_data_file_path('gamer'))
    (real / 'documents.json').write_text(
        json.dumps(document, ensure_ascii=False), encoding='utf-8',
    )
    with open_database(real) as database:
        database.execute(
            "UPDATE mirror_state SET sync_status='dirty',last_error='known stale mirror'",
        )
        database.commit()

    (test / 'obsolete.txt').write_text('must not survive activation', encoding='utf-8')
    monkeypatch.setattr(engine, 'get_app_data_dir', lambda: real)
    monkeypatch.setattr(engine, 'get_test_data_dir', lambda: test)
    report = engine.refresh_test_data()

    assert report.outcome == OUTCOME_MIGRATION_VERIFIED
    assert not (test / 'obsolete.txt').exists()
    assert (test / 'data.pkl').read_bytes() == (real / 'data.pkl').read_bytes()
    assert (test / 'settings.pkl').read_bytes() == (real / 'settings.pkl').read_bytes()
    assert (test / 'gamer.pkl').read_bytes() == (real / 'gamer.pkl').read_bytes()
    assert (test / 'documents.json').read_bytes() == (real / 'documents.json').read_bytes()

    ready, reasons = verify_prepared_profile(test)
    assert ready, reasons
    with open_database(test) as database:
        assert database.execute(
            'SELECT sync_status FROM mirror_state WHERE id=1',
        ).fetchone()[0] == 'healthy'
        assert set(dict(database.execute(
            'SELECT subsystem,owner FROM storage_ownership',
        )).values()) == {'sqlite'}
        assert json.loads(database.execute(
            "SELECT value_json FROM settings WHERE key='bridge_setting'",
        ).fetchone()[0]) == 'new'
        game_payload = json.loads(database.execute(
            'SELECT payload_json FROM game_state WHERE id=1',
        ).fetchone()[0])
        assert game_payload['extensions']['bridge_marker'] == 'new-pickle'
        assert game_payload['gamer']['coins'] == 777
        assert game_payload['global_streak']['global_streaks'] == [
            {'__type__': 'date', 'value': freeze_day.isoformat()},
            engine.STREAK_FREEZE_MARKER,
        ]
        assert database.execute(
            'SELECT title FROM documents',
        ).fetchone()[0] == 'Current document'

    assert main(['verify', '--data-dir', str(test), '--json']) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['status'] == 'READY_FOR_TAURI'
