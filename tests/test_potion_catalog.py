from datetime import date, datetime, timedelta
from types import SimpleNamespace

import game
import game_data


def test_timed_potions_progress_from_hour_to_week(monkeypatch):
    gamer = game.Gamer(level=1)
    monkeypatch.setattr(
        game_data.game, 'load_game', lambda: gamer,
    )
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {'projects': {}})

    potion_families = (
        (
            game_data.exp_potion_1hrs,
            game_data.exp_potion_24hrs,
            game_data.exp_potion_7days,
            (100, 1200, 5400),
        ),
        (
            game_data.coin_potion_1hrs,
            game_data.coin_potion_24hrs,
            game_data.coin_potion_7days,
            (60, 720, 3240),
        ),
        (
            game_data.super_exp_potion_1hrs,
            game_data.super_exp_potion_24hrs,
            game_data.super_exp_potion_7days,
            (1000, 12000, 54000),
        ),
        (
            game_data.super_coin_potion_1hrs,
            game_data.super_coin_potion_24hrs,
            game_data.super_coin_potion_7days,
            (1200, 14400, 64800),
        ),
    )

    for hourly, daily, weekly, expected_prices in potion_families:
        assert hourly.level < daily.level < weekly.level
        assert (hourly.price, daily.price, weekly.price) == expected_prices
        assert [
            hourly.buff.duration_minutes,
            daily.buff.duration_minutes,
            weekly.buff.duration_minutes,
        ] == [60, 60 * 24, 60 * 24 * 7]

    assert (
        game_data.super_exp_potion_1hrs.price
        == game_data.exp_potion_1hrs.price * 10
    )
    assert game_data.exp_potion_24hrs.price == game_data.exp_potion_1hrs.price * 12
    assert game_data.exp_potion_7days.price == game_data.exp_potion_24hrs.price * 5 * 0.9
    assert (
        game_data.super_coin_potion_1hrs.price
        == game_data.coin_potion_1hrs.price * 20
    )
    assert (
        game_data.super_coin_potion_24hrs.price
        == game_data.coin_potion_24hrs.price * 20
    )
    assert (
        game_data.super_coin_potion_7days.price
        == game_data.coin_potion_7days.price * 20
    )


def test_coin_potion_price_tracks_expected_profit(monkeypatch):
    gamer = game.Gamer(level=34)
    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(
        game_data, '_estimate_recent_daily_symbols', lambda data, today: 2000,
    )
    monkeypatch.setattr(
        game_data, '_get_active_streak_length', lambda data, today: 100,
    )
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {'projects': {}})

    daily_profit = 2000 / 100 * game_data.base_coin_bonus * 10
    daily_profit += 10 * 10 * 100 * gamer.calculate_inflation()
    weekly_profit = sum(
        2000 / 100 * game_data.base_coin_bonus * 10
        + 10 * 10 * (100 + day_offset) * gamer.calculate_inflation()
        for day_offset in range(7)
    )

    assert game_data.super_coin_potion_24hrs.price == gamer.round_money(
        daily_profit * 0.9,
    )
    assert game_data.super_coin_potion_7days.price == gamer.round_money(
        weekly_profit * 0.85,
    )


def test_recent_writing_estimate_ignores_old_and_future_notes():
    today = date(2026, 8, 1)
    notes = [
        SimpleNamespace(date_create=datetime(2026, 7, 10), added_symbols=15000),
        SimpleNamespace(date_create=datetime(2026, 7, 20), added_symbols=15000),
        SimpleNamespace(date_create=datetime(2026, 6, 1), added_symbols=50000),
        SimpleNamespace(date_create=datetime(2026, 8, 2), added_symbols=50000),
    ]
    project = SimpleNamespace(notes=notes, stages=[])

    daily_symbols = game_data._estimate_recent_daily_symbols(
        {'projects': {'test': project}}, today,
    )

    assert daily_symbols == 1000


def test_weekly_potions_are_registered():
    potions = game_data.ITEM_REGISTRY['Зелья']

    assert potions['Недельное зелье познания'] is game_data.exp_potion_7days
    assert potions['Недельное зелье доходности'] is game_data.coin_potion_7days
    assert potions['Недельное зелье просвещения'] is game_data.super_exp_potion_7days
    assert potions['Недельное зелье супердоходности'] is game_data.super_coin_potion_7days
