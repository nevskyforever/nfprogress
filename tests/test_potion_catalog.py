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


def test_writing_motivation_items_are_registered():
    potions = game_data.ITEM_REGISTRY['Зелья']
    items = game_data.ITEM_REGISTRY['Предметы']

    assert potions['Большое зелье вдохновения'] is game_data.large_inspiration_potion
    assert items['Компас рукописи'] is game_data.manuscript_compass
    assert potions['Искра вдохновения'] is game_data.inspiration_spark
    assert potions['Эликсир вдохновения'] is game_data.grand_inspiration_elixir
    assert items['Учебник мастерства'] is game_data.mastery_manual
    assert items['Жетон новой цели'] is game_data.daily_route_token
    assert items['Нить ритуала'] is game_data.session_streak_thread
    assert items['Медаль качества'] is game_data.session_grade_medal


def test_mastery_manual_adds_selected_specialization_xp(monkeypatch):
    gamer = game.Gamer(level=4)
    gamer.specialization = 'editor'
    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(gamer, 'save', lambda: None)

    result = game_data.mastery_manual_func('use', 2)

    assert gamer.specialization_mastery['editor'] == 2
    assert '2 опыта' in result


def test_daily_route_token_changes_goal_without_spending_inspiration(monkeypatch):
    gamer = game.Gamer(level=2)
    gamer.inspiration = 20
    gamer.ensure_daily_challenge(target=1000)
    first_id = gamer.daily_challenge['option_id']
    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(gamer, 'save', lambda: None)

    result = game_data.daily_route_token_func('use')

    assert gamer.daily_challenge['option_id'] != first_id
    assert gamer.inspiration == 20
    assert 'бесплатно заменена' in result


def test_session_shop_effects_enforce_stack_limits(monkeypatch):
    gamer = game.Gamer(level=5)
    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(gamer, 'save', lambda: None)

    for _ in range(3):
        game_data.session_streak_thread_func('use')
    game_data.session_grade_medal_func('use')

    assert gamer.session_streak_shields == 3
    assert gamer.session_grade_boosts == 1

    try:
        game_data.session_streak_thread_func('use')
    except ValueError as error:
        assert 'максимум' in str(error)
    else:
        raise AssertionError('Защита серии превысила лимит накопления')

    try:
        game_data.session_grade_medal_func('use')
    except ValueError as error:
        assert 'уже подготовлена' in str(error)
    else:
        raise AssertionError('Вторая медаль качества была принята')


def test_new_item_descriptions_do_not_load_save(monkeypatch):
    monkeypatch.setattr(
        game_data.game, 'load_game',
        lambda: (_ for _ in ()).throw(AssertionError('save must not be loaded')),
    )

    assert 'мастерства' in game_data.mastery_manual_func('?')
    assert 'цель дня' in game_data.daily_route_token_func('?')
    assert 'максимум 3' in game_data.session_streak_thread_func('?')
    assert 'одну ступень' in game_data.session_grade_medal_func('?')
