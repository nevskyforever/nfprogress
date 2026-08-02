from datetime import datetime

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
        'writing_session', 'session_reward_bonus',
    ):
        delattr(gamer, attribute)

    gamer.migrate()

    assert gamer.inspiration == 0
    assert gamer.daily_challenge is None
    assert gamer.weekly_challenge is None
    assert gamer.writing_session is None
    assert gamer.session_reward_bonus == 0
