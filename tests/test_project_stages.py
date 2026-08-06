import datetime

import engine


class DummyGamer:
    def __init__(self, freeze_count=0):
        self.items = {'Предметы': {'Заморозка': freeze_count}, 'Зелья': {}, 'Награды': {}}
        self.saved = False

    def save(self):
        self.saved = True


def enable_freeze_mode(monkeypatch, today, gamer, saved_data=None):
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(
        engine,
        'load_settings',
        lambda: {
            'game_mode': True,
            'global_streak': True,
            'today_for_test_mode': True,
            'today_for_test_datetime': datetime.datetime.combine(today, datetime.time.min),
        },
    )
    monkeypatch.setattr(engine, 'save_data', lambda data: saved_data.append(data) if saved_data is not None else None)

    import game
    monkeypatch.setattr(game, 'load_game', lambda: gamer)


def stage_with_missed_yesterday(name, today):
    stage = engine.Stage(
        name=name,
        goal=1000,
        total_symbols=0,
        deadline=today + datetime.timedelta(days=10),
        unit='symbols',
        personal_goal_for_the_day=100,
        parent_project_name='Book',
    )
    stage.streaks = [today - datetime.timedelta(days=2)]
    stage.max_streak = 1
    stage.streak_status = 'Active'
    return stage


def stage_with_unextended_today(name, today):
    stage = stage_with_missed_yesterday(name, today)
    stage.streaks = [today - datetime.timedelta(days=1)]
    return stage


def test_auto_freeze_preserves_missed_global_streak_without_active_project_streaks(monkeypatch):
    today = datetime.date(2026, 7, 26)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    data = {
        'projects': {},
        'global_streaks': [today - datetime.timedelta(days=2)],
        'global_streak_status': 'Active',
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': True, 'freeze_changed': True}
    assert data['global_streaks'] == [today - datetime.timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert data['global_streak_status'] == 'Freeze'
    assert gamer.items['Предметы']['Заморозка'] == 0
    assert gamer.saved is True


def test_auto_freeze_does_not_spend_new_freeze_for_active_global_streak(monkeypatch):
    today = datetime.date(2026, 7, 26)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    data = {
        'projects': {},
        'global_streaks': [today - datetime.timedelta(days=1)],
        'global_streak_status': 'Active',
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': False, 'freeze_changed': False}
    assert data['global_streaks'] == [today - datetime.timedelta(days=1)]
    assert gamer.items['Предметы']['Заморозка'] == 1


def test_convert_project_to_stages_moves_notes_to_first_stage():
    deadline = datetime.date(2026, 7, 30)
    project = engine.Project(name='Book', goal=1000, total_symbols=300, deadline=deadline)
    note = engine.Note(300, 300, 30, datetime.datetime(2026, 7, 1, 10, 0))
    project.notes = [note]
    project.streaks = [datetime.date(2026, 7, 1)]
    project.max_streak = 1
    project.streak_status = 'Active'
    project.synch = {'type': 'word', 'path': '/tmp/book.docx'}

    project.convert_to_stages()

    assert project.has_stages()
    assert project.notes == []
    assert len(project.stages) == 1
    assert project.stages[0].notes == [note]
    assert project.stages[0].streaks == [datetime.date(2026, 7, 1)]
    assert project.stages[0].deadline == deadline
    assert project.stages[0].streak_status == 'Active'
    assert project.stages[0].max_streak == 1
    assert project.streaks == []
    assert project.deadline == 'Нет'
    assert project.streak_status == 'Off'
    assert project.stages[0].synch == {'type': 'word', 'path': '/tmp/book.docx'}
    assert project.synch is None
    assert project.goal == 1000
    assert project.total_units == 300


def test_project_with_stages_aggregates_goal_total_and_notes():
    project = engine.Project(name='Book', unit='symbols')
    first = engine.Stage(name='Draft', goal=1000, total_symbols=400, parent_project_name='Book')
    second = engine.Stage(name='Edit', goal=500, total_symbols=100, parent_project_name='Book')
    first.notes = [engine.Note(400, 400, 40, datetime.datetime(2026, 7, 2, 10, 0))]
    second.notes = [engine.Note(100, 100, 20, datetime.datetime(2026, 7, 1, 10, 0))]
    project.enable_stages = True
    project.combine_stage_mindmaps = True
    project.stages = [first, second]

    assert project.goal == 1500
    assert project.total_units == 500
    assert round(project.progress, 2) == 33.33
    assert project.get_statistic()['Всего написано в единице проекта'] == 500
    assert [stage_name for stage_name, _ in project.get_notes_with_stage_names()] == ['Edit', 'Draft']


def test_parent_deadline_recalculates_daily_goal_after_stage_changes(monkeypatch):
    monkeypatch.setattr(engine, 'today_for_test', lambda: datetime.date(2026, 7, 18))
    parent_deadline = datetime.date(2026, 7, 30)
    first_deadline = datetime.date(2026, 7, 20)
    second_deadline = datetime.date(2026, 7, 25)
    project = engine.Project(name='Book', deadline=parent_deadline, unit='symbols')
    first = engine.Stage(
        name='Draft',
        goal=1000,
        total_symbols=0,
        deadline=first_deadline,
        personal_goal_for_the_day=100,
        parent_project_name='Book',
    )
    second = engine.Stage(
        name='Edit',
        goal=500,
        total_symbols=0,
        deadline=second_deadline,
        personal_goal_for_the_day=50,
        parent_project_name='Book',
    )
    project.enable_stages = True
    project.stages = [first, second]

    assert project.deadline == parent_deadline
    assert round(project.get_today_goal_value(), 2) == 115.38
    assert round(project.get_today_display_goal_value(), 2) == 115.38

    first.goal = 2000
    assert round(project.get_today_goal_value(), 2) == 192.31

    signature_before_daily_goal_change = project.project_plan['signature']
    first.personal_goal_for_the_day = 200
    assert round(project.get_today_goal_value(), 2) == 192.31
    assert project.project_plan['signature'] != signature_before_daily_goal_change

    third = engine.Stage(
        name='Proofreading',
        goal=500,
        total_symbols=0,
        parent_project_name='Book',
    )
    project.stages.append(third)
    assert round(project.get_today_goal_value(), 2) == 230.77

    project.stages.remove(third)
    assert round(project.get_today_goal_value(), 2) == 192.31


def test_recalculated_daily_goal_does_not_add_todays_progress_twice(monkeypatch):
    today = datetime.date(2026, 7, 18)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = engine.Project(
        name='Book',
        goal=1000,
        total_symbols=100,
        deadline=today + datetime.timedelta(days=9),
        unit='symbols',
    )
    project.notes = [
        engine.Note(100, 100, 10, datetime.datetime(2026, 7, 18, 12, 0)),
    ]

    assert project.get_today_goal_value() == 100

    # После изменения общей цели пересчитывается дневная норма (120), а не
    # добавляется к уже написанным за сегодня 100 символам.
    project.goal = 1200

    assert project.get_today_goal_value() == 120


def test_changed_daily_goal_uses_start_of_day_progress(monkeypatch):
    today = datetime.date(2026, 7, 18)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = engine.Project(
        name='Book',
        goal=2000,
        total_symbols=1100,
        deadline=today + datetime.timedelta(days=9),
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.notes = [
        engine.Note(1100, 100, 5, datetime.datetime(2026, 7, 18, 12, 0)),
    ]

    assert project.get_today_goal_value() == 1100

    # При изменении общей цели та же дневная норма продлевает план, не меняя
    # уже рассчитанную накопительную цель на сегодня.
    project.goal = 2500
    project.deadline = today + datetime.timedelta(days=14)
    assert project.get_today_goal_value() == 1100

    project.personal_goal_for_the_day = 200
    assert project.get_today_goal_value() == 1200

    project.personal_goal_for_the_day = 50
    assert project.get_today_goal_value() == 1050


def test_changed_goal_preserves_existing_todays_accumulated_goal(monkeypatch):
    today = datetime.date(2026, 7, 18)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = engine.Project(
        name='Book',
        goal=5000,
        total_symbols=3500,
        deadline=today + datetime.timedelta(days=3),
        unit='symbols',
        personal_goal_for_the_day=500,
    )

    assert project.get_today_goal_value() == 4000

    # Пользователь отстаёт от старого плана, но меняет общую цель, сохраняя
    # дневную норму. Сегодняшняя цель не должна опуститься до 3700.
    project.total_units = 3200
    project.goal = 7500
    project.deadline = today + datetime.timedelta(days=7)

    assert project.get_today_goal_value() == 4000
    assert project.project_plan[today + datetime.timedelta(days=7)] == 7500


def test_changed_daily_goal_adjusts_today_by_daily_difference(monkeypatch):
    start_day = datetime.date(2026, 7, 16)
    today = start_day + datetime.timedelta(days=2)
    current_day = [start_day]
    monkeypatch.setattr(engine, 'today_for_test', lambda: current_day[0])
    project = engine.Project(
        name='Book',
        goal=5000,
        deadline=start_day + datetime.timedelta(days=10),
        unit='symbols',
        personal_goal_for_the_day=100,
    )

    assert project.get_today_goal_value() == 100

    current_day[0] = today
    assert project.get_today_goal_value() == 300

    project.personal_goal_for_the_day = 200

    assert project.get_today_goal_value() == 400
    assert project.project_plan[start_day] == 100
    assert project.project_plan[today + datetime.timedelta(days=1)] == 600


def test_plan_can_be_recalculated_from_current_progress(monkeypatch):
    today = datetime.date(2026, 8, 5)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = engine.Project(
        name='Book',
        goal=5000,
        total_symbols=2000,
        deadline=today + datetime.timedelta(days=5),
        unit='symbols',
        personal_goal_for_the_day=500,
    )
    project.project_plan = {
        'signature': 'old',
        'daily_goal_symbols': 500,
        today - datetime.timedelta(days=1): 2500,
        today: 3000,
    }

    assert project.get_today_goal_value(
        recalculate_from_current_progress=True
    ) == 2500
    assert project.project_plan[today - datetime.timedelta(days=1)] == 2500
    assert project.project_plan[today + datetime.timedelta(days=1)] == 3000


def test_parent_daily_goal_uses_original_plan_when_stages_have_no_deadlines():
    parent_deadline = engine.today_for_test() + datetime.timedelta(days=9)
    project = engine.Project(name='Book', goal=1000, total_symbols=100, deadline=parent_deadline, unit='symbols')
    first = engine.Stage(name='Draft', goal=600, total_symbols=60, parent_project_name='Book')
    second = engine.Stage(name='Edit', goal=400, total_symbols=40, parent_project_name='Book')
    project.enable_stages = True
    project.stages = [first, second]

    assert project.get_today_goal_value() == 190


def test_stage_can_have_streak_status():
    stage = engine.Stage(
        name='Draft',
        goal=1000,
        total_symbols=1000,
        deadline=datetime.date(2026, 7, 20),
        personal_goal_for_the_day=100,
    )

    assert stage.get_streak_status() == 'Start'
    assert stage.streaks == [engine.today_for_test()]


def test_disabled_project_streak_has_off_status_even_with_deadline():
    project = engine.Project(
        name='Book',
        goal=1000,
        deadline=engine.today_for_test() + datetime.timedelta(days=10),
        streak_status='Off',
    )

    assert project.streak_status == 'Off'
    assert project.get_streak_status() == 'Off'


def test_project_streak_works_without_deadline_when_daily_goal_is_set():
    project = engine.Project(
        name='Book',
        goal=1000,
        personal_goal_for_the_day=100,
    )
    project.get_today_goal_value()
    project.total_units = 100

    assert project.deadline == 'Нет'
    assert project.get_streak_status() == 'Start'
    assert project.streaks == [engine.today_for_test()]


def test_disabled_parent_streak_uses_enabled_stage_sources():
    project = engine.Project(
        name='Book',
        deadline=engine.today_for_test() + datetime.timedelta(days=10),
        streak_status='Off',
    )
    enabled_stage = engine.Stage(name='Draft', goal=1000)
    disabled_stage = engine.Stage(name='Edit', goal=500, streak_status='Off')
    project.enable_stages = True
    project.stages = [enabled_stage, disabled_stage]

    assert engine.get_project_streak_sources(project) == [enabled_stage]


def test_disabling_streak_clears_current_run_and_preserves_maximum():
    today = engine.today_for_test()
    project = engine.Project(name='Book')
    project.streaks = [today - datetime.timedelta(days=1), today]

    project.set_streak_state(False)

    assert project.streak_status == 'Off'
    assert project.streaks == []
    assert project.max_streak == 2


def test_migration_removes_legacy_streak_flag_and_keeps_status():
    enabled = engine.Project(name='Enabled', goal=1000)
    disabled = engine.Project(name='Disabled', goal=1000, streak_status='Off')
    enabled.streak_enabled = True
    disabled.streak_enabled = False

    enabled.migrate()
    disabled.migrate()

    assert not hasattr(enabled, 'streak_enabled')
    assert not hasattr(disabled, 'streak_enabled')
    assert enabled.streak_status == 'No'
    assert disabled.streak_status == 'Off'


def test_migration_enables_auto_freeze_for_existing_projects():
    project = engine.Project(name='Book', goal=1000)
    del project.auto_freeze

    project.migrate()

    assert project.auto_freeze is True


def test_disabled_auto_freeze_loses_streak_without_spending_item(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)
    project = stage_with_missed_yesterday('Draft', today)
    project.auto_freeze = False

    status = project.get_streak_status()

    assert status == 'Lose 1'
    assert project.streaks == []
    assert gamer.items['Предметы']['Заморозка'] == 1
    assert gamer.saved is False


def test_disabled_auto_freeze_does_not_block_manual_freeze(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)
    project = stage_with_unextended_today('Draft', today)
    project.auto_freeze = False

    assert engine.apply_project_freeze_group(project, today) is True
    assert project.streaks == [
        today - datetime.timedelta(days=1),
        engine.STREAK_FREEZE_MARKER,
    ]
    assert gamer.items['Предметы']['Заморозка'] == 0


def test_parent_deadline_transfers_longest_stage_streak():
    project = engine.Project(name='Book', unit='symbols')
    first_deadline = datetime.date(2026, 7, 10)
    second_deadline = datetime.date(2026, 7, 15)
    first = engine.Stage(name='Draft', goal=1000, deadline=first_deadline, parent_project_name='Book')
    second = engine.Stage(name='Edit', goal=500, deadline=second_deadline, parent_project_name='Book')
    first.streaks = [datetime.date(2026, 7, 1)]
    second.streaks = [datetime.date(2026, 7, 1), datetime.date(2026, 7, 2)]
    second.max_streak = 2
    project.enable_stages = True
    project.stages = [first, second]
    project.deadline = datetime.date(2026, 7, 30)

    project.transfer_longest_stage_streak()

    assert project.streaks == [datetime.date(2026, 7, 1), datetime.date(2026, 7, 2)]
    assert project.max_streak == 2
    assert first.streaks == []
    assert second.streaks == []
    assert first.deadline == first_deadline
    assert second.deadline == second_deadline


def test_removing_parent_deadline_preserves_independent_streak_setting():
    project = engine.Project(name='Book', deadline=datetime.date(2026, 7, 30), unit='symbols')
    first = engine.Stage(name='Draft', goal=1000, deadline=datetime.date(2026, 7, 10), parent_project_name='Book')
    project.enable_stages = True
    project.stages = [first]
    project.streaks = [datetime.date(2026, 7, 1), datetime.date(2026, 7, 2)]
    first.streaks = []

    project.deadline = 'Нет'

    assert project.streaks == [datetime.date(2026, 7, 1), datetime.date(2026, 7, 2)]
    assert project.streak_status != 'Off'
    assert first.streaks == []
    assert first.deadline == datetime.date(2026, 7, 10)


def test_removing_parent_deadline_does_not_switch_streak_source_implicitly(monkeypatch):
    today = datetime.date(2026, 7, 18)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(engine, 'load_settings', lambda: {'game_mode': False, 'global_streak': True})

    project = engine.Project(
        name='Book',
        deadline=today + datetime.timedelta(days=10),
        unit='symbols',
    )
    stage = engine.Stage(
        name='Draft',
        goal=1000,
        total_symbols=1000,
        deadline=today + datetime.timedelta(days=10),
        personal_goal_for_the_day=100,
        parent_project_name='Book',
    )
    project.enable_stages = True
    project.stages = [stage]
    project.streaks = [today - datetime.timedelta(days=1)]
    project.streak_status = 'Active'

    project.deadline = 'Нет'

    assert project.streaks == [today - datetime.timedelta(days=1)]
    assert project.streak_status == 'Active'
    assert stage.streaks == []
    assert stage.streak_status == 'No'


def test_parent_without_deadline_freezes_all_active_stage_streaks(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    project = engine.Project(name='Book', unit='symbols')
    first = stage_with_missed_yesterday('Draft', today)
    second = stage_with_missed_yesterday('Edit', today)
    project.enable_stages = True
    project.stages = [first, second]
    data = {
        'projects': {'Book': project},
        'global_streaks': [today - datetime.timedelta(days=2)],
        'global_streak_status': 'Active',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': True, 'freeze_changed': True}
    assert first.streaks == [today - datetime.timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert second.streaks == [today - datetime.timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert project.streaks == []
    assert project.freezes == 1
    assert first.freezes == 0
    assert second.freezes == 0
    assert gamer.items['Предметы']['Заморозка'] == 0
    assert data['global_streaks'] == [today - datetime.timedelta(days=2), engine.STREAK_FREEZE_MARKER]


def test_manual_freeze_group_uses_parent_project_for_stage_streaks(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    project = engine.Project(name='Book', unit='symbols')
    first = stage_with_unextended_today('Draft', today)
    second = stage_with_unextended_today('Edit', today)
    project.enable_stages = True
    project.stages = [first, second]

    assert engine.get_project_freeze_sources(project, today) == [first, second]
    assert engine.apply_project_freeze_group(project, today) is True
    assert first.streaks == [today - datetime.timedelta(days=1), engine.STREAK_FREEZE_MARKER]
    assert second.streaks == [today - datetime.timedelta(days=1), engine.STREAK_FREEZE_MARKER]
    assert project.freezes == 1
    assert first.freezes == 0
    assert second.freezes == 0
    assert gamer.items['Предметы']['Заморозка'] == 0


def test_manual_freeze_group_skips_already_extended_stage(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    project = engine.Project(name='Book', unit='symbols')
    active_stage = stage_with_unextended_today('Draft', today)
    extended_stage = engine.Stage(
        name='Edit',
        goal=1000,
        total_symbols=200,
        deadline=today + datetime.timedelta(days=10),
        unit='symbols',
        personal_goal_for_the_day=100,
        parent_project_name='Book',
    )
    extended_stage.streaks = [today - datetime.timedelta(days=1), today]
    extended_stage.streak_status = 'Go'
    project.enable_stages = True
    project.stages = [active_stage, extended_stage]

    assert engine.get_project_freeze_sources(project, today) == [active_stage]
    assert engine.apply_project_freeze_group(project, today) is True
    assert active_stage.streaks == [today - datetime.timedelta(days=1), engine.STREAK_FREEZE_MARKER]
    assert extended_stage.streaks == [today - datetime.timedelta(days=1), today]
    assert project.freezes == 1
    assert active_stage.freezes == 0
    assert extended_stage.freezes == 0
    assert gamer.items['Предметы']['Заморозка'] == 0


def test_parent_with_deadline_freezes_parent_streak_not_stage_streaks(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    project = engine.Project(
        name='Book',
        goal=1000,
        total_symbols=0,
        deadline=today + datetime.timedelta(days=10),
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.streaks = [today - datetime.timedelta(days=2)]
    project.max_streak = 1
    project.streak_status = 'Active'
    stage = stage_with_missed_yesterday('Draft', today)
    project.enable_stages = True
    project.stages = [stage]
    data = {
        'projects': {'Book': project},
        'global_streaks': [today - datetime.timedelta(days=2)],
        'global_streak_status': 'Active',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': True, 'freeze_changed': True}
    assert project.streaks == [today - datetime.timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert stage.streaks == [today - datetime.timedelta(days=2)]
    assert project.freezes == 1
    assert gamer.items['Предметы']['Заморозка'] == 0


def test_manual_freeze_includes_parent_with_own_deadline_and_streak(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    project = engine.Project(
        name='Book',
        goal=1000,
        total_symbols=0,
        deadline=today + datetime.timedelta(days=10),
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.streaks = [today - datetime.timedelta(days=1)]
    project.streak_status = 'Active'
    project.max_streak = 1
    stage = stage_with_unextended_today('Draft', today)
    project.enable_stages = True
    project.stages = [stage]

    assert engine.get_project_freeze_sources(project, today) == [project]
    assert engine.apply_project_freeze_group(project, today) is True
    assert project.streaks == [today - datetime.timedelta(days=1), engine.STREAK_FREEZE_MARKER]
    assert stage.streaks == [today - datetime.timedelta(days=1)]
    assert project.freezes == 1
    assert gamer.items['Предметы']['Заморозка'] == 0


def test_stage_auto_freeze_does_not_freeze_already_extended_global_streak(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    project = engine.Project(name='Book', unit='symbols')
    stage = stage_with_missed_yesterday('Draft', today)
    project.enable_stages = True
    project.stages = [stage]
    data = {
        'projects': {'Book': project},
        'global_streaks': [today - datetime.timedelta(days=2), today - datetime.timedelta(days=1), today],
        'global_streak_status': 'Go',
        'max_global_streak': 3,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': True, 'freeze_changed': True}
    assert stage.streaks == [today - datetime.timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert project.freezes == 1
    assert stage.freezes == 0
    assert data['global_streaks'] == [
        today - datetime.timedelta(days=2),
        today - datetime.timedelta(days=1),
        today,
    ]


def test_already_extended_stage_streak_is_not_frozen(monkeypatch):
    today = datetime.date(2026, 7, 18)
    gamer = DummyGamer(freeze_count=1)
    enable_freeze_mode(monkeypatch, today, gamer)

    project = engine.Project(name='Book', unit='symbols')
    stage = engine.Stage(
        name='Draft',
        goal=1000,
        total_symbols=200,
        deadline=today + datetime.timedelta(days=10),
        unit='symbols',
        personal_goal_for_the_day=100,
        parent_project_name='Book',
    )
    stage.streaks = [today - datetime.timedelta(days=1), today]
    stage.max_streak = 2
    stage.streak_status = 'Go'
    project.enable_stages = True
    project.stages = [stage]
    data = {
        'projects': {'Book': project},
        'global_streaks': [today - datetime.timedelta(days=1), today],
        'global_streak_status': 'Go',
        'max_global_streak': 2,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }

    result = engine.refresh_project_streak_statuses(data)

    assert result == {'changed': False, 'freeze_changed': False}
    assert stage.streaks == [today - datetime.timedelta(days=1), today]
    assert gamer.items['Предметы']['Заморозка'] == 1


def test_convert_project_with_stages_to_single_rebuilds_chronological_notes():
    project = engine.Project(name='Book', unit='symbols')
    first = engine.Stage(name='Draft', goal=1000, total_symbols=400, parent_project_name='Book')
    second = engine.Stage(name='Edit', goal=500, total_symbols=100, parent_project_name='Book')
    first.notes = [engine.Note(400, 400, 40, datetime.datetime(2026, 7, 2, 10, 0))]
    second.notes = [engine.Note(100, 100, 20, datetime.datetime(2026, 7, 1, 10, 0))]
    project.enable_stages = True
    project.stages = [first, second]

    project.convert_to_single()

    assert not project.has_stages()
    assert project.combine_stage_mindmaps is False
    assert project.goal == 1500
    assert project.total_units == 500
    assert [note.get_added_symbols() for note in project.notes] == [100, 400]
    assert [note.get_new_total() for note in project.notes] == [100, 500]
    assert [round(note.get_added_progress(), 2) for note in project.notes] == [6.67, 26.67]


def test_convert_project_with_stages_to_single_transfers_longest_stage_streak_and_deadline(monkeypatch):
    today = datetime.date(2026, 7, 18)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = engine.Project(name='Book', unit='symbols')
    first_deadline = today + datetime.timedelta(days=5)
    second_deadline = today + datetime.timedelta(days=10)
    first = engine.Stage(name='Draft', goal=1000, total_symbols=200, deadline=first_deadline, parent_project_name='Book')
    second = engine.Stage(name='Edit', goal=500, total_symbols=100, deadline=second_deadline, parent_project_name='Book')
    first.streaks = [datetime.date(2026, 7, 1)]
    first.max_streak = 1
    second.streaks = [datetime.date(2026, 7, 1), datetime.date(2026, 7, 2)]
    second.streak_status = 'Go'
    second.max_streak = 2
    project.enable_stages = True
    project.stages = [first, second]

    project.convert_to_single()

    assert not project.has_stages()
    assert project.streaks == [datetime.date(2026, 7, 1), datetime.date(2026, 7, 2)]
    assert project.streak_status == 'Go'
    assert project.max_streak == 2
    assert project.deadline == second_deadline
    assert round(project.get_today_goal_value(), 2) == 136.36


def test_active_project_and_stage_report_goal_completed_by_deadline():
    deadline = datetime.date(2026, 7, 10)
    project = engine.Project(name='Book', goal=1000, total_symbols=1500, deadline=deadline, status='активен')
    project.notes = [
        engine.Note(1000, 1000, 100, datetime.datetime(2026, 7, 10, 12, 0)),
        engine.Note(1500, 500, 50, datetime.datetime(2026, 7, 11, 12, 0)),
    ]
    stage = engine.Stage(name='Draft', goal=500, total_symbols=500, deadline=deadline, status='активен')
    stage.notes = [engine.Note(500, 500, 100, datetime.datetime(2026, 7, 9, 12, 0))]

    assert project.was_goal_completed_by_deadline()
    assert stage.was_goal_completed_by_deadline()


def test_goal_completed_only_after_deadline_is_not_reported_as_on_time():
    deadline = datetime.date(2026, 7, 10)
    project = engine.Project(name='Book', goal=1000, total_symbols=1000, deadline=deadline)
    project.notes = [engine.Note(1000, 1000, 100, datetime.datetime(2026, 7, 11, 12, 0))]

    assert not project.was_goal_completed_by_deadline()


def test_note_before_start_of_day_counts_towards_previous_deadline(monkeypatch):
    deadline = datetime.date(2026, 7, 25)
    monkeypatch.setattr(engine, 'get_start_day_time', lambda: datetime.time(4, 0))
    project = engine.Project(name='Book', goal=1000, deadline=deadline)
    project.notes = [engine.Note(1000, 1000, 100, datetime.datetime(2026, 7, 26, 1, 20))]

    assert project.was_goal_completed_by_deadline()


def test_remaining_goal_is_zero_when_project_or_stage_exceeds_goal():
    project = engine.Project(name='Book', goal=1000, total_symbols=1100)
    stage = engine.Stage(name='Draft', goal=500, total_symbols=600)

    assert project.get_need_write_value() == 0
    assert project.get_need_write_in_unit() == 0
    assert stage.get_need_write_value() == 0


def test_completed_project_and_stage_have_complete_streak_status(monkeypatch):
    today = datetime.date(2026, 7, 25)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = engine.Project(
        name='Book', goal=1000, total_symbols=1000, deadline=today, status='завершен'
    )
    stage = engine.Stage(
        name='Draft', goal=500, total_symbols=500, deadline=today, status='завершен'
    )
    for entity in (project, stage):
        entity.streaks = [today - datetime.timedelta(days=1), today]
        entity.streak_status = 'Go'

        assert entity.get_streak_status() == 'Complete'
        assert entity.get_streak_status_msg('min') == '🎉 СТРИК ЗАВЕРШЕН'
