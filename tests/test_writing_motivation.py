from datetime import datetime, timedelta

import engine
import game


def make_gamer(monkeypatch):
    gamer = game.Gamer()
    monkeypatch.setattr(gamer, 'save', lambda: None)
    gamer.daily_challenge = {
        'date': engine.today_for_test().isoformat(),
        'target': 1000,
        'progress': 0,
        'completed': False,
    }
    return gamer


def test_daily_challenge_rewards_only_once(monkeypatch):
    gamer = make_gamer(monkeypatch)

    first_messages = gamer.record_motivation_progress(1000)
    coins_after_completion = gamer.coins
    exp_after_completion = gamer.exp
    second_messages = gamer.record_motivation_progress(500)

    assert first_messages
    assert second_messages == []
    assert gamer.daily_challenge['completed'] is True
    assert gamer.coins == coins_after_completion
    assert gamer.exp == exp_after_completion
    assert gamer.inspiration == 13


def test_successful_session_advances_session_challenge(monkeypatch):
    gamer = make_gamer(monkeypatch)
    ok, _ = gamer.select_weekly_challenge('sessions', save=False)
    assert ok is True
    ok, _ = gamer.start_writing_session(25, 600, 'Продолжить черновик', save=False)
    assert ok is True

    gamer.record_motivation_progress(600)
    ok, message = gamer.finish_writing_session(save=False)

    assert ok is True
    assert 'Сессия завершена' in message
    assert gamer.writing_session is None
    assert gamer.weekly_challenge['progress'] == 1


def test_unsuccessful_session_has_no_penalty(monkeypatch):
    gamer = make_gamer(monkeypatch)
    initial_health = gamer.health
    initial_coins = gamer.coins
    gamer.start_writing_session(15, 1000, 'Составить план', save=False)

    ok, message = gamer.finish_writing_session(save=False)

    assert ok is False
    assert 'штрафа нет' in message
    assert gamer.health == initial_health
    assert gamer.coins == initial_coins


def test_flow_ink_bonus_is_spent_by_successful_session(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.session_reward_bonus = 0.25
    gamer.start_writing_session(15, 100, 'Написать новую сцену', save=False)
    gamer.record_motivation_progress(100)

    ok, _ = gamer.finish_writing_session(save=False)

    assert ok is True
    assert gamer.session_reward_bonus == 0
    assert gamer.exp == 312.5


def test_inspiration_increases_writing_rewards(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.inspiration = 50

    gamer.give_symbol_bonus(100)

    assert gamer.coins == 10.5
    assert gamer.exp == 525


def test_adaptive_target_uses_recent_productive_days(monkeypatch):
    class Note:
        def __init__(self, day, symbols):
            self.day = day
            self.symbols = symbols

        def get_date_create(self):
            return self.day

        def get_added_symbols(self):
            return self.symbols

    today = datetime(2026, 8, 3).date()
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = type('Project', (), {
        'enable_stages': False,
        'notes': [Note(today.replace(day=1), 2000), Note(today.replace(day=2), 3000)],
    })()

    target = game.Gamer.calculate_adaptive_daily_target({'projects': {'Роман': project}})

    assert target == 2000


def test_migration_adds_motivation_state_to_old_gamer(monkeypatch):
    gamer = make_gamer(monkeypatch)
    for attribute in (
        'inspiration', 'daily_challenge', 'weekly_challenge',
        'writing_session', 'session_reward_bonus', 'specialization',
        'specialization_changed_at',
    ):
        delattr(gamer, attribute)

    gamer.migrate()

    assert gamer.inspiration == 0
    assert gamer.daily_challenge is None
    assert gamer.weekly_challenge is None
    assert gamer.writing_session is None
    assert gamer.session_reward_bonus == 0
    assert gamer.specialization is None
    assert gamer.specialization_changed_at is None


def test_specialization_unlock_and_change_cooldown(monkeypatch):
    gamer = make_gamer(monkeypatch)
    ok, message = gamer.select_specialization('marathoner', save=False)
    assert ok is False
    assert '3 уровне' in message

    gamer.level = 3
    ok, _ = gamer.select_specialization('marathoner', save=False)
    assert ok is True
    ok, message = gamer.select_specialization('ritualist', save=False)
    assert ok is False
    assert '14 дн.' in message

    changed_at = engine.today_for_test()
    monkeypatch.setattr(
        engine,
        'today_for_test',
        lambda: changed_at + timedelta(days=14),
    )
    ok, _ = gamer.select_specialization('ritualist', save=False)
    assert ok is True


def test_marathoner_rewards_large_entries(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'marathoner'
    gamer.daily_challenge['target'] = 100000

    gamer.give_symbol_bonus(3000)

    assert gamer.coins == 345
    assert gamer.exp == 17250


def test_editor_rewards_editorial_session(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'editor'
    gamer.start_writing_session(15, 100, 'Отредактировать текст', save=False)
    gamer.record_motivation_progress(100)

    ok, _ = gamer.finish_writing_session(save=False)

    assert ok is True
    assert gamer.coins == 31.3
    assert gamer.exp == 312.5


def test_finisher_increases_completion_reward(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'finisher'

    gamer.give_complete_bonus('Complete', 1000, project_name='Роман')

    assert gamer.coins == 240
    assert gamer.exp == 24000


def test_explorer_increases_daily_challenge_reward(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'explorer'

    gamer.record_motivation_progress(1000)

    assert gamer.coins == 60
    assert gamer.exp == 600


def test_session_countdown_uses_wall_clock(monkeypatch):
    gamer = make_gamer(monkeypatch)
    current_time = [datetime(2026, 8, 3, 12, 0, 0)]
    monkeypatch.setattr(game, 'get_session_now', lambda: current_time[0])
    gamer.start_writing_session(15, 1000, 'Продолжить черновик', save=False)

    assert gamer.writing_session_remaining_seconds() == 900
    current_time[0] += timedelta(seconds=1)
    assert gamer.writing_session_remaining_seconds() == 899


def test_legacy_session_switches_from_frozen_test_time(monkeypatch):
    gamer = make_gamer(monkeypatch)
    wall_time = datetime(2026, 8, 3, 15, 30, 0)
    monkeypatch.setattr(game, 'get_session_now', lambda: wall_time)
    gamer.writing_session = {
        'started_at': datetime(2026, 8, 3, 10, 0, 0),
        'duration_minutes': 25,
        'target_symbols': 1000,
        'progress': 300,
        'intention': 'Продолжить черновик',
    }

    gamer.normalize_motivation()

    assert gamer.writing_session['clock_source'] == 'wall'
    assert gamer.writing_session['started_at'] == wall_time
    assert gamer.writing_session['progress'] == 300


def test_ui_session_timer_refreshes_label_every_second():
    from types import SimpleNamespace

    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    from game_UI import GameMenuController

    class StatusLabel:
        def __init__(self):
            self.values = []

        def setText(self, value):
            self.values.append(value)

    class SessionGamer:
        writing_session = {
            'progress': 0,
            'target_symbols': 1000,
            'intention': 'Продолжить черновик',
        }

        def __init__(self):
            self.calls = 0

        def writing_session_remaining_seconds(self):
            self.calls += 1
            return 901 - self.calls

    app = QCoreApplication.instance() or QCoreApplication([])
    label = StatusLabel()
    controller = GameMenuController.__new__(GameMenuController)
    controller.ui = SimpleNamespace(
        centralwidget=None,
        writing_session_status=label,
    )
    controller.gamer = SessionGamer()
    controller.update_writing_session_clock()
    controller.setup_writing_session_timer()

    loop = QEventLoop()
    QTimer.singleShot(1150, loop.quit)
    loop.exec()
    controller.writing_session_timer.stop()

    assert app is not None
    assert len(label.values) >= 2
    assert '15:00' in label.values[0]
    assert '14:59' in label.values[-1]
