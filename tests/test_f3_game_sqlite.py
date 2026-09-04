from __future__ import annotations

import json
import pickle
from pathlib import Path

import engine
import game

from nfprogress.core.game_state import GameEventConsumer, SQLiteGameRepository
from nfprogress.core.migration import MigrationImportError, cutover_game, cutover_projects
from nfprogress.core.services.game import GameService
from nfprogress.core.sqlite.connection import open_database
from nfprogress.core.sqlite.ownership import StorageOwner, StorageOwnershipRepository, Subsystem
from nfprogress.core.sqlite.settings import cutover_settings
from nfprogress.core.storage import PickleRepository


def _prepared_root(tmp_path: Path) -> tuple[PickleRepository, engine.Project]:
    repository = PickleRepository(tmp_path)
    project = engine.Project('F3 project', 10_000)
    repository.write_projects({
        'projects': {project.name: project},
        'project_order': [project.project_id],
        'notifications': ['legacy notification'],
        'global_streaks': [],
        'global_streak_status': 'No',
        'max_global_streak': 0,
        'future_game_root': {'kept': True},
    })
    gamer = game.Gamer(level=2, exp=125, coins=80)
    gamer.future_game_field = {'nested': [1, True, None]}
    gamer.api_streak_reward_days = {'local:f3': engine.today_for_test()}
    repository.write_gamer(gamer)
    return repository, project


def test_game_cutover_imports_unknown_state_and_is_idempotent(tmp_path):
    repository, _project = _prepared_root(tmp_path)

    bundle = cutover_game(tmp_path)

    assert bundle.payload['dto_version'] == 1
    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.GAME) == StorageOwner.SQLITE
    restored = repository.read_gamer()
    assert restored.level == 2
    assert restored.coins == 80
    assert restored.future_game_field == {'nested': [1, True, None]}
    game_data = SQLiteGameRepository(tmp_path).read_game_data()
    assert game_data['notifications'] == ['legacy notification']
    assert SQLiteGameRepository(tmp_path).read_payload()['extensions']['future_game_root'] == {'kept': True}

    # A second startup returns without consulting legacy files.
    (tmp_path / 'gamer.pkl').write_bytes(b'not a pickle anymore')
    second = cutover_game(tmp_path)
    assert second.payload == {}
    assert repository.read_gamer().coins == 80


def test_game_cutover_rehydrates_legacy_notifications(tmp_path):
    repository, _project = _prepared_root(tmp_path)
    notification = engine.Notification(
        'saved notification', tag='game',
        date_create=engine.datetime(2026, 1, 2, 3, 4), status='Read',
    )
    repository.write_projects({
        **repository.read_projects(),
        'notifications': {'new': [notification], 'read': []},
    })

    cutover_game(tmp_path)

    restored = SQLiteGameRepository(tmp_path).read_game_data()['notifications']
    assert restored['new'][0].text == 'saved notification'
    assert restored['new'][0].tag == 'game'
    assert restored['new'][0].status == 'Read'


def test_failed_game_verifier_keeps_pickle_owner(tmp_path, monkeypatch):
    _repository, _project = _prepared_root(tmp_path)
    monkeypatch.setattr(
        'nfprogress.core.migration.verify_game_bundle',
        lambda *_args, **_kwargs: (False, ['intentional mismatch']),
    )

    try:
        cutover_game(tmp_path)
    except MigrationImportError:
        pass
    else:
        raise AssertionError('Game owner must not switch after failed verification')
    assert StorageOwnershipRepository(tmp_path).get_owner(Subsystem.GAME) == StorageOwner.PICKLE


def test_sqlite_game_writes_do_not_touch_stale_pickle_and_work_without_pickle(tmp_path, monkeypatch):
    repository, _project = _prepared_root(tmp_path)
    cutover_game(tmp_path)
    stale = pickle.dumps(game.Gamer(coins=9999))
    (tmp_path / 'gamer.pkl').write_bytes(stale)
    before = (tmp_path / 'gamer.pkl').stat().st_mtime_ns

    repository.write_gamer(game.Gamer(coins=42))
    monkeypatch.setattr(game, 'load_game', lambda: (_ for _ in ()).throw(AssertionError('PKL read')))
    assert repository.read_gamer().coins == 42
    assert (tmp_path / 'gamer.pkl').stat().st_mtime_ns == before
    assert GameService(repository).get_state()['profile']['coins'] == 42


def test_sqlite_game_state_does_not_read_legacy_game_files(tmp_path, monkeypatch):
    repository, _project = _prepared_root(tmp_path)
    cutover_projects(tmp_path)
    cutover_settings(tmp_path, repository.read_settings())
    cutover_game(tmp_path)
    monkeypatch.setattr(game, 'load_game', lambda: (_ for _ in ()).throw(AssertionError('PKL read')))
    monkeypatch.setattr(engine, 'load_data', lambda: (_ for _ in ()).throw(AssertionError('data.pkl read')))
    monkeypatch.setattr(engine, 'load_settings', lambda: (_ for _ in ()).throw(AssertionError('settings.pkl read')))

    state = GameService(repository).get_state()

    assert state['profile']['coins'] == 80


def test_progress_event_is_atomic_idempotent_and_survives_restart(tmp_path):
    repository, project = _prepared_root(tmp_path)
    cutover_game(tmp_path)
    with open_database(tmp_path) as db:
        db.execute(
            "INSERT OR IGNORE INTO domain_events(event_id,event_type,project_id,delta_symbols,context_json,created_at) VALUES(?,?,?,?,?,?)",
            ('progress-1', 'ProgressAdded', project.project_id, 100, '{}', '2026-01-01T00:00:00Z'),
        )
        db.commit()

    assert GameEventConsumer(tmp_path).process_pending() == {'processed': 1, 'failed': 0}
    assert GameEventConsumer(tmp_path).process_pending() == {'processed': 0, 'failed': 0}
    assert repository.read_gamer().coins == 90
    with open_database(tmp_path) as db:
        row = db.execute(
            'SELECT status, processed_at, attempt_count FROM domain_events WHERE event_id=?',
            ('progress-1',),
        ).fetchone()
        assert row['status'] == 'processed'
        assert row['processed_at']
        assert row['attempt_count'] == 0


def test_completion_reward_once_and_deletion_is_non_reversible(tmp_path):
    repository, project = _prepared_root(tmp_path)
    cutover_game(tmp_path)
    with open_database(tmp_path) as db:
        for event_id, event_type, context in (
            ('completion-1', 'ProjectCompleted', {'key': f'project:{project.project_id}', 'total_symbols': 1000}),
            ('delete-1', 'ProgressDeleted', {}),
        ):
            db.execute(
                'INSERT INTO domain_events(event_id,event_type,project_id,context_json,created_at) VALUES(?,?,?,?,?)',
                (event_id, event_type, project.project_id, json.dumps(context), '2026-01-01T00:00:00Z'),
            )
        db.commit()
    result = GameEventConsumer(tmp_path).process_pending()
    assert result == {'processed': 2, 'failed': 0}
    first = repository.read_gamer().coins
    with open_database(tmp_path) as db:
        db.execute(
            "INSERT OR IGNORE INTO domain_events(event_id,event_type,project_id,context_json,created_at) VALUES('completion-duplicate','ProjectCompleted',?,'{\"key\":\"project:%s\",\"total_symbols\":1000}','2026-01-01T00:00:01Z')"
            % project.project_id,
            (project.project_id,),
        )
        db.commit()
    GameEventConsumer(tmp_path).process_pending()
    assert repository.read_gamer().coins == first


def test_failed_event_retries_then_becomes_poison(tmp_path):
    _repository, project = _prepared_root(tmp_path)
    cutover_game(tmp_path)
    with open_database(tmp_path) as db:
        db.execute(
            "INSERT INTO domain_events(event_id,event_type,project_id,context_json,created_at) VALUES('bad','Unsupported',?,'{}','2026-01-01T00:00:00Z')",
            (project.project_id,),
        )
        db.commit()
    consumer = GameEventConsumer(tmp_path)
    assert consumer.process_pending() == {'processed': 0, 'failed': 1}
    assert consumer.process_pending() == {'processed': 0, 'failed': 1}
    assert consumer.process_pending() == {'processed': 0, 'failed': 1}
    with open_database(tmp_path) as db:
        row = db.execute("SELECT status,attempt_count,last_error,failed_at FROM domain_events WHERE event_id='bad'").fetchone()
        assert row['status'] == 'failed'
        assert row['attempt_count'] == 3
        assert row['last_error']
        assert row['failed_at']


def test_game_sqlite_integrity_after_event_processing(tmp_path):
    _repository, project = _prepared_root(tmp_path)
    cutover_game(tmp_path)
    with open_database(tmp_path) as db:
        db.execute(
            "INSERT INTO domain_events(event_id,event_type,project_id,delta_symbols,context_json,created_at) VALUES('integrity','ProgressAdded',?,50,'{}','2026-01-01T00:00:00Z')",
            (project.project_id,),
        )
        db.commit()
    GameEventConsumer(tmp_path).process_pending()
    with open_database(tmp_path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
