from datetime import timedelta
from types import SimpleNamespace

import engine
import game
import game_data


def make_project(streak_len=0, freezes=0, status='активен'):
    today = engine.today_for_test()
    streaks = [today - timedelta(days=day) for day in range(streak_len - 1, -1, -1)]
    return SimpleNamespace(status=status, streaks=streaks, freezes=freezes)


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
