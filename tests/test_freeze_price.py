from datetime import timedelta
import pytest
import engine
import game
import game_data


def make_project(streak_len=0, freezes=0, status='активен'):
    today = engine.today_for_test()
    streaks = [today - timedelta(days=day) for day in range(streak_len - 1, -1, -1)]
    project = engine.Project(name='Черновик', goal=1_000, status=status)
    project.streaks = streaks
    project.freezes = freezes
    return project


def make_project_with_source(source_status, streak_len=50, freezes=0):
    project = make_project(status='активен')
    stage = engine.Stage(
        name='Источник', goal=1_000, status=source_status,
        parent_project_name=project.name,
    )
    today = engine.today_for_test()
    stage.streaks = [
        today - timedelta(days=day) for day in range(streak_len - 1, -1, -1)
    ]
    stage.freezes = freezes
    project.enable_stages = True
    project.stages = [stage]
    return project


def test_freeze_price_is_positive_on_first_available_levels(monkeypatch):
    gamer = game.Gamer(level=3)
    gamer.update_cf()

    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'draft': make_project()},
        'global_streaks': [],
    })

    assert game_data.calculate_freeze_price() > 0


def test_freeze_price_grows_with_streak_value_and_used_freezes(monkeypatch):
    gamer = game.Gamer(level=10)
    gamer.update_cf()

    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'draft': make_project(streak_len=3, freezes=0)},
        'global_streaks': [],
    })
    short_streak_price = game_data.calculate_freeze_price()

    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'draft': make_project(streak_len=30, freezes=2)},
        'global_streaks': [],
    })
    long_streak_price = game_data.calculate_freeze_price()

    assert long_streak_price > short_streak_price


def test_freeze_price_does_not_explode_on_long_streak_history(monkeypatch):
    gamer = game.Gamer(level=29)
    gamer.set_cf_value('coins', 10.1)
    global_streaks = make_project(streak_len=96).streaks

    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'draft': make_project(streak_len=34, freezes=17)},
        'global_streaks': global_streaks,
    })

    assert game_data.calculate_freeze_price() < 50000


def test_freeze_price_keeps_growing_after_many_used_freezes(monkeypatch):
    gamer = game.Gamer(level=29)
    gamer.set_cf_value('coins', 10.1)
    global_streaks = make_project(streak_len=96).streaks

    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'draft': make_project(streak_len=34, freezes=17)},
        'global_streaks': global_streaks,
    })
    price_after_17_freezes = game_data.calculate_freeze_price()

    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'draft': make_project(streak_len=34, freezes=50)},
        'global_streaks': global_streaks,
    })
    price_after_50_freezes = game_data.calculate_freeze_price()

    assert price_after_50_freezes > price_after_17_freezes


def test_freeze_price_uses_only_active_projects_and_sources(monkeypatch):
    gamer = game.Gamer(level=10)
    gamer.set_cf_value('coins', 100)
    active = make_project_with_source('активен', streak_len=80, freezes=2)
    completed_source = make_project_with_source('завершен', streak_len=500, freezes=50)
    archived_source = make_project_with_source('в архиве', streak_len=500, freezes=50)
    completed_project = make_project(streak_len=500, freezes=50, status='завершен')
    archived_project = make_project(streak_len=500, freezes=50, status='в архиве')

    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'active': active}, 'global_streaks': [],
    })
    active_only = game_data.calculate_freeze_price()

    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {
            'active': active,
            'completed-source': completed_source,
            'archived-source': archived_source,
            'completed-project': completed_project,
            'archived-project': archived_project,
        },
        'global_streaks': [],
    })

    assert game_data.calculate_freeze_price() == active_only


@pytest.mark.parametrize('source_status', ['завершен', 'в архиве'])
def test_freeze_price_ignores_an_inactive_source_in_an_active_project(
    monkeypatch, source_status,
):
    gamer = game.Gamer(level=10)
    gamer.set_cf_value('coins', 100)
    active = make_project_with_source('активен', streak_len=20, freezes=1)
    inactive_source = make_project_with_source(source_status, streak_len=500, freezes=50)

    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'active': active}, 'global_streaks': [],
    })
    expected = game_data.calculate_freeze_price()
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'active': active, 'inactive-source': inactive_source},
        'global_streaks': [],
    })

    assert game_data.calculate_freeze_price() == expected


@pytest.mark.parametrize('project_status', ['завершен', 'в архиве'])
def test_freeze_price_ignores_an_inactive_project(monkeypatch, project_status):
    gamer = game.Gamer(level=10)
    gamer.set_cf_value('coins', 100)
    active = make_project_with_source('активен', streak_len=20, freezes=1)
    inactive_project = make_project(streak_len=500, freezes=50, status=project_status)

    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'active': active}, 'global_streaks': [],
    })
    expected = game_data.calculate_freeze_price()
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {
        'projects': {'active': active, 'inactive-project': inactive_project},
        'global_streaks': [],
    })

    assert game_data.calculate_freeze_price() == expected
