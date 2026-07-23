from datetime import datetime, date

import engine


def test_day_before_start_time_belongs_to_previous_calendar_date(monkeypatch):
    monkeypatch.setattr(engine, 'now_for_test', lambda: datetime(2026, 7, 23, 1, 59, 59))
    monkeypatch.setattr(engine, 'load_settings', lambda: {'start_day_time': '02:00:00'})

    assert engine.today_for_test() == date(2026, 7, 22)


def test_day_after_start_time_keeps_current_calendar_date(monkeypatch):
    monkeypatch.setattr(engine, 'now_for_test', lambda: datetime(2026, 7, 23, 2, 0, 0))
    monkeypatch.setattr(engine, 'load_settings', lambda: {'start_day_time': '02:00:00'})

    assert engine.today_for_test() == date(2026, 7, 23)


def test_midnight_is_used_when_setting_is_missing(monkeypatch):
    monkeypatch.setattr(engine, 'now_for_test', lambda: datetime(2026, 7, 23, 0, 0, 0))
    monkeypatch.setattr(engine, 'load_settings', lambda: {})

    assert engine.today_for_test() == date(2026, 7, 23)


def test_project_streak_is_not_lost_when_day_start_time_moves_back(monkeypatch):
    effective_day = date(2026, 7, 22)
    monkeypatch.setattr(engine, 'today_for_test', lambda: effective_day)

    project = engine.Project(
        name='Book',
        goal=1_000,
        deadline=date(2026, 7, 31),
        total_symbols=1_000,
        personal_goal_for_the_day=100,
    )
    project.streaks = [date(2026, 7, 23)]
    project.streak_status = 'Go'

    assert project.get_streak_status() == 'Go'
    assert project.streaks == [date(2026, 7, 23)]


def test_global_streak_is_not_lost_when_day_start_time_moves_back(monkeypatch):
    effective_day = date(2026, 7, 22)
    monkeypatch.setattr(engine, 'save_data', lambda data: None)

    project = engine.Project(
        name='Book',
        goal=1_000,
        deadline=date(2026, 7, 31),
        total_symbols=1_000,
        personal_goal_for_the_day=100,
    )
    project.streaks = [date(2026, 7, 23)]
    project.streak_status = 'Go'
    data = {
        'projects': {'Book': project},
        'global_streaks': [date(2026, 7, 23)],
        'global_streak_status': 'Go',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    assert engine.global_streak_status(data, today=effective_day) == 'Go'
    assert data['global_streaks'] == [date(2026, 7, 23)]


def test_streak_bonus_is_not_due_when_its_saved_day_is_ahead_of_today():
    assert not engine.streak_bonus_is_due(date(2026, 7, 23), date(2026, 7, 22))
    assert not engine.streak_bonus_is_due(date(2026, 7, 23), date(2026, 7, 23))
    assert engine.streak_bonus_is_due(date(2026, 7, 23), date(2026, 7, 24))
