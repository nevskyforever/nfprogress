from datetime import date, datetime, timedelta

import game
import engine


def disable_persistence(monkeypatch):
    monkeypatch.setattr(game.Gamer, 'save', lambda self: None)
    monkeypatch.setattr(game.engine, 'load_data', lambda: {})
    monkeypatch.setattr(game.engine, 'save_data', lambda data: None)


def test_legacy_gamer_gets_skill_points_once_on_migration(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=5)
    del gamer.skills
    del gamer.available_skill_points
    del gamer.skill_points_awarded_for_level

    gamer.migrate()

    assert gamer.available_skill_points == 8
    assert gamer.skill_points_awarded_for_level == 5

    gamer.migrate()

    assert gamer.available_skill_points == 8


def test_skill_points_update_character_coefficients(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=3)
    gamer.available_skill_points = 3

    assert gamer.increase_skill('productivity', save=False)[0]
    assert gamer.increase_skill('profitability', save=False)[0]
    assert gamer.increase_skill('endurance', save=False)[0]

    assert gamer.get_cf_value('exp') == game.game_data.cf_exp[3] + game.SKILL_CF_STEP
    assert gamer.get_cf_value('coins') == game.game_data.cf_coins[3] + game.SKILL_CF_STEP
    assert gamer.get_cf_value('health_recovery') == game.SKILL_CF_STEP


def test_health_recovery_uses_recovery_coefficient(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=1, health=50)
    gamer.available_skill_points = 1
    gamer.increase_skill('endurance', save=False)
    now = datetime.now()
    gamer.last_health_recovery_at = now - timedelta(hours=4)

    message = gamer.recover_health_by_time(now=now, save=False)

    assert gamer.health == 51.0
    assert 'Здоровье восстановлено' in message


def test_health_recovery_uses_developer_mode_date(monkeypatch):
    disable_persistence(monkeypatch)
    monkeypatch.setattr(
        game.engine,
        'now_for_test',
        lambda: datetime.combine(date(2026, 7, 13), datetime.now().time()),
    )
    gamer = game.Gamer(level=1, health=50)
    gamer.available_skill_points = 1
    gamer.increase_skill('endurance', save=False)
    gamer.last_health_recovery_at = datetime.combine(date(2026, 7, 12), datetime.now().time())

    message = gamer.recover_health_by_time(save=False)

    assert gamer.health >= 56
    assert 'Здоровье восстановлено' in message


def test_health_recovery_resets_future_marker_after_developer_time_rollback(monkeypatch):
    disable_persistence(monkeypatch)
    current_test_now = datetime(2026, 7, 10, 20, 30)
    monkeypatch.setattr(game.engine, 'now_for_test', lambda: current_test_now)
    gamer = game.Gamer(level=1, health=75)
    gamer.available_skill_points = 1
    gamer.increase_skill('endurance', save=False)
    gamer.last_health_recovery_at = datetime(2026, 7, 12, 19, 22)

    assert gamer.recover_health_by_time(save=False) is None
    assert gamer.health == 75
    assert gamer.last_health_recovery_at == current_test_now

    current_test_now = datetime(2026, 7, 10, 21, 30)
    message = gamer.recover_health_by_time(save=False)

    assert gamer.health == 75.2
    assert 'Здоровье восстановлено' in message


def test_level_up_grants_two_skill_points(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=1, exp=game.game_data.levels[1])

    gamer.level_up()

    assert gamer.level == 2
    assert gamer.available_skill_points == game.SKILL_POINTS_PER_LEVEL
    assert gamer.skill_points_awarded_for_level == 2


def test_max_health_increases_by_ten_every_five_levels(monkeypatch):
    disable_persistence(monkeypatch)

    assert game.Gamer(level=1).get_max_health() == 100
    assert game.Gamer(level=5).get_max_health() == 100
    assert game.Gamer(level=6).get_max_health() == 110
    assert game.Gamer(level=11).get_max_health() == 120


def test_migration_updates_max_health_for_existing_level(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=11, health=100)
    del gamer.max_health

    gamer.migrate()

    assert gamer.get_max_health() == 120
    assert gamer.health == 120


def test_inventory_aliases_are_merged_to_registry_keys(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer()
    gamer.items = {
        'Предметы': {
            'Заморозка': 0,
            '❄️Заморозка': 1,
        },
        'Зелья': {},
        'Награды': {},
    }

    assert gamer.normalize_inventory_item_names() is True
    assert gamer.items['Предметы'] == {'Заморозка': 1}


def test_global_lose_bonus_rechecks_streak_before_damage(monkeypatch):
    disable_persistence(monkeypatch)
    monkeypatch.setattr(game.engine, 'load_data', lambda: {'global_streaks': [game.engine.today_for_test()]})
    monkeypatch.setattr(game.engine, 'global_streak_status', lambda data: 'Active')

    gamer = game.Gamer(level=1, health=10)

    assert gamer.give_streak_bonus('Lose 5', 'Global', 5) is None
    assert gamer.health == 10
    assert gamer.last_lose_global_streak_damage is None


def test_global_lose_bonus_applies_auto_freeze_before_damage(monkeypatch):
    disable_persistence(monkeypatch)
    today = date(2026, 7, 8)
    monkeypatch.setattr(game.engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(
        game.engine,
        'load_settings',
        lambda: {'game_mode': True, 'global_streak': True},
    )

    project = engine.Project(
        name='Book',
        goal=1000,
        deadline=today + timedelta(days=10),
        total_symbols=0,
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.streaks = [today - timedelta(days=2)]
    project.streak_status = 'Active'
    data = {
        'projects': {'Book': project},
        'global_streaks': [today - timedelta(days=2)],
        'global_streak_status': 'Active',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }
    gamer = game.Gamer(level=1, health=10)
    gamer.items = {'Предметы': {'Заморозка': 1}, 'Зелья': {}, 'Награды': {}}

    monkeypatch.setattr(game.engine, 'load_data', lambda: data)
    monkeypatch.setattr(game, 'load_game', lambda: gamer)

    assert gamer.give_streak_bonus('Lose 1', 'Global', 1) is None
    assert gamer.health == 10
    assert gamer.items['Предметы']['Заморозка'] == 0
    assert project.streaks == [today - timedelta(days=2), engine.STREAK_FREEZE_MARKER]
    assert data['global_streak_status'] == 'Active'


def test_global_auto_freeze_syncs_loaded_gamer_inventory(monkeypatch):
    disable_persistence(monkeypatch)
    today = date(2026, 7, 8)
    monkeypatch.setattr(game.engine, 'today_for_test', lambda: today)
    monkeypatch.setattr(
        game.engine,
        'load_settings',
        lambda: {'game_mode': True, 'global_streak': True},
    )

    project = engine.Project(
        name='Book',
        goal=1000,
        deadline=today + timedelta(days=10),
        total_symbols=0,
        unit='symbols',
        personal_goal_for_the_day=100,
    )
    project.streaks = [today - timedelta(days=2)]
    project.streak_status = 'Active'
    data = {
        'projects': {'Book': project},
        'global_streaks': [today - timedelta(days=2)],
        'global_streak_status': 'Active',
        'max_global_streak': 1,
        'last_global_streak_lost_date': None,
        'last_global_streak_lose_len': 0,
    }
    ui_gamer = game.Gamer(level=1, health=10)
    ui_gamer.items = {'Предметы': {'Заморозка': 1}, 'Зелья': {}, 'Награды': {}}
    disk_gamer = game.Gamer(level=1, health=10)
    disk_gamer.items = {'Предметы': {'Заморозка': 1}, 'Зелья': {}, 'Награды': {}}

    monkeypatch.setattr(game.engine, 'load_data', lambda: data)
    monkeypatch.setattr(game, 'load_game', lambda: disk_gamer)

    assert ui_gamer.give_streak_bonus('Lose 1', 'Global', 1) is None
    assert ui_gamer.health == 10
    assert ui_gamer.items['Предметы']['Заморозка'] == 0
    assert disk_gamer.items['Предметы']['Заморозка'] == 0


def test_migration_keeps_damaged_health_when_max_health_increases(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=11, health=80)
    del gamer.max_health

    gamer.migrate()

    assert gamer.get_max_health() == 120
    assert gamer.health == 80


def test_health_recovery_uses_level_max_health(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=6, health=108)
    gamer.available_skill_points = 4
    gamer.increase_skill('endurance', 4, save=False)
    now = datetime.now()
    gamer.last_health_recovery_at = now - timedelta(hours=4)

    gamer.recover_health_by_time(now=now, save=False)

    assert gamer.health == 110
