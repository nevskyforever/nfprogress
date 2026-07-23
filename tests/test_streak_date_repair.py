from datetime import date, datetime, timedelta

import engine


def complete_project_for_streak(today):
    project = engine.Project(
        name='Book',
        goal=1000,
        deadline=date(2026, 7, 31),
        total_symbols=1000,
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.streaks = [date(2026, 7, 9)]
    project.max_streak = 1
    project.deadline_set_date = today
    return project


def test_project_streak_repairs_gap_after_date_bug(monkeypatch):
    today = date(2026, 7, 11)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(engine, 'load_settings', lambda: {'game_mode': False, 'global_streak': True})

    project = complete_project_for_streak(today)

    assert project.get_streak_status() == 'Go'
    assert project.streaks == [date(2026, 7, 9), date(2026, 7, 10), date(2026, 7, 11)]
    assert engine.streak_length(project.streaks) == 3


def test_global_streak_repairs_gap_after_date_bug(monkeypatch):
    today = date(2026, 7, 11)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(engine, 'load_settings', lambda: {'game_mode': False, 'global_streak': True})
    monkeypatch.setattr(engine, 'save_data', lambda data: None)

    project = complete_project_for_streak(today)
    data = {
        'projects': {'Book': project},
        'global_streaks': [date(2026, 7, 9)],
        'global_streak_status': 'Active',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    assert engine.global_streak_status(data, today=today) == 'Go'
    assert data['global_streaks'] == [date(2026, 7, 9), date(2026, 7, 10), date(2026, 7, 11)]
    assert data['max_global_streak'] == 3


def test_leaked_test_date_is_ignored_outside_dev_mode(monkeypatch):
    real_today = date(2026, 7, 11)
    leaked_test_day = date(2026, 7, 8)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return real_today

    monkeypatch.setattr(engine, 'date', FixedDate)
    monkeypatch.setattr(engine, 'dev_mode', False)
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {'today_for_test_mode': True, 'today_for_test_date': leaked_test_day},
    )

    assert engine.today_for_test() == real_today


def test_legacy_test_date_is_ignored_in_dev_mode(monkeypatch):
    real_today = date(2026, 7, 11)
    legacy_test_day = date(2026, 7, 8)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return real_today

    monkeypatch.setattr(engine, 'date', FixedDate)
    monkeypatch.setattr(engine, 'dev_mode', True)
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {'today_for_test_mode': True, 'today_for_test_date': legacy_test_day},
    )

    assert engine.today_for_test() == real_today


def test_test_datetime_works_in_dev_mode(monkeypatch):
    selected_test_datetime = datetime(2026, 7, 12, 15, 45)
    monkeypatch.setattr(engine, 'dev_mode', True)
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {'today_for_test_mode': True, 'today_for_test_datetime': selected_test_datetime},
    )

    assert engine.now_for_test() == selected_test_datetime
    assert engine.today_for_test() == selected_test_datetime.date()


def test_global_streak_recovers_after_bug_saved_lose(monkeypatch):
    today = date(2026, 7, 11)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(engine, 'load_settings', lambda: {'game_mode': False, 'global_streak': True})
    monkeypatch.setattr(engine, 'save_data', lambda data: None)

    data = {
        'projects': {},
        'global_streaks': [],
        'global_streak_status': 'Lose 88',
        'max_global_streak': 88,
        'last_global_streak_lost_date': today,
        'last_global_streak_lose_len': 88,
    }

    assert engine.global_streak_status(data, today=today) == 'Active'
    assert engine.streak_length(data['global_streaks']) == 90
    assert engine.streak_last_day(data['global_streaks']) == date(2026, 7, 10)


def test_project_streak_recovers_after_bug_saved_lose(monkeypatch):
    today = date(2026, 7, 11)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(engine, 'load_settings', lambda: {'game_mode': False, 'global_streak': True})

    project = complete_project_for_streak(today)
    project.streaks = []
    project.streak_status = 'Lose 26'
    project.last_streak_lost_date = today
    project.max_streak = 26

    assert project.get_streak_status() == 'Go'
    assert engine.streak_length(project.streaks) == 29
    assert engine.streak_last_day(project.streaks) == today


class DummyGamer:
    def __init__(self, freeze_count=0):
        self.items = {'Предметы': {'Заморозка': freeze_count}, 'Зелья': {}, 'Награды': {}}
        self.saved = False

    def save(self):
        self.saved = True


def project_with_yesterday_gap(today):
    project = engine.Project(
        name='Book',
        goal=1000,
        deadline=today + timedelta(days=10),
        total_symbols=0,
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.streaks = [today - timedelta(days=2)]
    project.max_streak = 1
    project.streak_status = 'Active'
    project.project_plan = {
        'signature': str((
            project.deadline,
            project.personal_goal_for_the_day,
            project.goal,
            project.unit,
            project.deadline_set_date,
        )),
        today - timedelta(days=1): 100,
        today: 200,
    }
    return project


def enable_developer_test_date(monkeypatch, today):
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {
            'game_mode': True,
            'global_streak': True,
            'today_for_test_mode': True,
            'today_for_test_datetime': datetime.combine(today, datetime.min.time()),
            'today_for_test_date': today,
        },
    )
    monkeypatch.setattr(engine, 'dev_mode', True)


def test_developer_test_date_does_not_repair_missed_project_streak_without_freeze(monkeypatch):
    today = date(2026, 7, 11)
    enable_developer_test_date(monkeypatch, today)
    gamer = DummyGamer(freeze_count=0)

    import game
    monkeypatch.setattr(game, 'load_game', lambda: gamer)

    project = project_with_yesterday_gap(today)

    assert project.get_streak_status() == 'Lose 1'
    assert project.streaks == []
    assert gamer.items['Предметы']['Заморозка'] == 0


def test_developer_test_date_total_does_not_retroactively_extend_without_freeze(monkeypatch):
    today = date(2026, 7, 11)
    enable_developer_test_date(monkeypatch, today)
    gamer = DummyGamer(freeze_count=0)

    import game
    monkeypatch.setattr(game, 'load_game', lambda: gamer)

    project = project_with_yesterday_gap(today)
    project.total_symbols = 1000

    assert project.get_streak_status() == 'Lose 1'
    assert project.streaks == []


def test_developer_test_date_auto_freeze_spends_inventory(monkeypatch):
    today = date(2026, 7, 11)
    enable_developer_test_date(monkeypatch, today)
    gamer = DummyGamer(freeze_count=1)

    import game
    monkeypatch.setattr(game, 'load_game', lambda: gamer)

    project = project_with_yesterday_gap(today)

    assert project.get_streak_status() == 'Active'
    assert project.streaks == [today - timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert gamer.items['Предметы']['Заморозка'] == 0
    assert gamer.saved is True


def test_developer_test_date_does_not_repair_missed_global_streak_without_freeze(monkeypatch):
    today = date(2026, 7, 11)
    enable_developer_test_date(monkeypatch, today)
    monkeypatch.setattr(engine, 'save_data', lambda data: None)
    gamer = DummyGamer(freeze_count=0)

    import game
    monkeypatch.setattr(game, 'load_game', lambda: gamer)

    data = {
        'projects': {'Book': project_with_yesterday_gap(today)},
        'global_streaks': [today - timedelta(days=2)],
        'global_streak_status': 'Active',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    assert engine.global_streak_status(data, today=today) == 'Lose 1'
    assert data['global_streaks'] == []


def test_auto_freeze_extends_global_streak_before_global_loss(monkeypatch):
    today = date(2026, 7, 13)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {
            'game_mode': True,
            'global_streak': True,
            'today_for_test_mode': True,
            'today_for_test_datetime': datetime.combine(today, datetime.min.time()),
        },
    )
    monkeypatch.setattr(engine, 'save_data', lambda data: None)
    gamer = DummyGamer(freeze_count=1)

    import game
    monkeypatch.setattr(game, 'load_game', lambda: gamer)

    project = engine.Project(
        name='Book',
        goal=1000,
        deadline=today + timedelta(days=10),
        total_symbols=0,
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.streaks = [date(2026, 7, 10), engine.STREAK_FREEZE_MARKER]
    project.streak_status = 'Active'
    project.freezes = 1
    data = {
        'projects': {'Book': project},
        'global_streaks': [date(2026, 7, 10), engine.STREAK_FREEZE_MARKER],
        'global_streak_status': 'Active',
        'max_global_streak': 2,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': True, 'freeze_changed': True}
    assert data['projects']['Book'].streaks == [
        date(2026, 7, 10),
        engine.STREAK_FREEZE_MARKER,
        engine.STREAK_FREEZE_MARKER,
    ]
    assert data['global_streaks'] == [
        date(2026, 7, 10),
        engine.STREAK_FREEZE_MARKER,
        engine.STREAK_FREEZE_MARKER,
    ]
    assert gamer.items['Предметы']['Заморозка'] == 0
    assert engine.global_streak_status(data, today=today) == 'Active'


def test_real_date_auto_freeze_spends_inventory_after_date_bug_repair_window(monkeypatch):
    today = date(2026, 7, 19)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(engine, 'dev_mode', False)
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {
            'game_mode': True,
            'global_streak': True,
            'today_for_test_mode': False,
        },
    )
    monkeypatch.setattr(engine, 'save_data', lambda data: None)
    gamer = DummyGamer(freeze_count=1)

    import game
    monkeypatch.setattr(game, 'load_game', lambda: gamer)

    project = project_with_yesterday_gap(today)
    data = {
        'projects': {'Book': project},
        'global_streaks': [today - timedelta(days=2)],
        'global_streak_status': 'Active',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': True, 'freeze_changed': True}
    assert project.streaks == [today - timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert data['global_streaks'] == [today - timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert gamer.items['Предметы']['Заморозка'] == 0
    assert gamer.saved is True


def test_game_controller_uses_ui_auto_freeze_notifications():
    import game_UI

    class DummyUi:
        def __init__(self):
            self.calls = []

        def _refresh_project_streak_statuses(self, data, show_auto_freeze_toasts=True):
            self.calls.append((data, show_auto_freeze_toasts))
            return True

    ui = DummyUi()
    controller = game_UI.GameMenuController.__new__(game_UI.GameMenuController)
    controller.ui = ui
    data = {'projects': {}}

    result = controller.refresh_project_streak_statuses(data)

    assert result == {'changed': True, 'freeze_changed': True}
    assert ui.calls == [(data, True)]
