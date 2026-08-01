from datetime import date

import pytest

import game
import game_data


REFERENCE_DAILY_SYMBOLS = 1000
REFERENCE_STREAK_DAYS_PER_LEVEL = 2

# Допустимое число игровых дней, за которое умеренно активный игрок должен
# накопить на предмет сразу после открытия соответствующего уровня.
AFFORDABILITY_DAYS = {
    60: (0.15, 5),
    60 * 24: (2, 25),
    60 * 24 * 7: (8, 80),
}

CONSUMABLE_AFFORDABILITY_DAYS = (0.03, 3)
PERMANENT_ITEM_AFFORDABILITY_DAYS = (10, 90)


def _timed_coefficient_items():
    for registry_name, item in game_data.ITEM_REGISTRY['Зелья'].items():
        buff = getattr(item, 'buff', None)
        if buff is None or buff.target_cf not in {'coins', 'exp'}:
            continue
        if buff.duration_minutes is None:
            continue
        yield pytest.param(registry_name, item, id=registry_name)


def _other_shop_items():
    for category in ('Предметы', 'Зелья'):
        for registry_name, item in game_data.ITEM_REGISTRY[category].items():
            buffs = [buff for buff in item.get_buffs() if buff is not None]
            if any(
                buff.target_cf in {'coins', 'exp'}
                and buff.duration_minutes is not None
                for buff in buffs
            ):
                continue

            affordability = (
                PERMANENT_ITEM_AFFORDABILITY_DAYS
                if any(buff.duration_minutes is None for buff in buffs)
                else CONSUMABLE_AFFORDABILITY_DAYS
            )
            yield pytest.param(
                category, registry_name, item, affordability,
                id=f'{category}-{registry_name}',
            )


def _reference_daily_income(level):
    coins_cf = game_data.cf_coins[level]
    inflation = 1 + (level - 1) * 0.15
    streak_length = max(1, level * REFERENCE_STREAK_DAYS_PER_LEVEL)
    writing_income = (
        REFERENCE_DAILY_SYMBOLS / 100 * game_data.base_coin_bonus * coins_cf
    )
    streak_income = 10 * coins_cf * streak_length * inflation
    return writing_income + streak_income


@pytest.mark.parametrize(('registry_name', 'item'), list(_timed_coefficient_items()))
def test_timed_item_price_is_realistic_at_unlock_level(
    monkeypatch, registry_name, item,
):
    """Цена должна быть посильной, но не символической в момент открытия."""
    gamer = game.Gamer(level=item.level)
    reference_streak = max(
        1, item.level * REFERENCE_STREAK_DAYS_PER_LEVEL,
    )
    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_data.engine, 'load_data', lambda: {'projects': {}})
    monkeypatch.setattr(
        game_data.engine, 'today_for_test', lambda: date(2026, 8, 1),
    )
    monkeypatch.setattr(
        game_data,
        '_estimate_recent_daily_symbols',
        lambda data, today: REFERENCE_DAILY_SYMBOLS,
    )
    monkeypatch.setattr(
        game_data,
        '_get_active_streak_length',
        lambda data, today: reference_streak,
    )

    duration = item.buff.duration_minutes
    assert duration in AFFORDABILITY_DAYS, (
        f'Для длительности {duration} мин. предмета «{registry_name}» '
        'не задан реалистичный диапазон доступности.'
    )

    days_to_afford = item.price / _reference_daily_income(item.level)
    minimum_days, maximum_days = AFFORDABILITY_DAYS[duration]

    assert minimum_days <= days_to_afford <= maximum_days, (
        f'«{registry_name}» стоит {item.price:g} монет на {item.level} уровне: '
        f'это {days_to_afford:.1f} типичных игровых дней, допустимо '
        f'{minimum_days:g}–{maximum_days:g}.'
    )


@pytest.mark.parametrize(
    ('category', 'registry_name', 'item', 'affordability'),
    list(_other_shop_items()),
)
def test_other_shop_item_price_is_realistic_at_unlock_level(
    monkeypatch, category, registry_name, item, affordability,
):
    """Обычные расходники и постоянные улучшения имеют разные бюджеты."""
    gamer = game.Gamer(level=item.level)
    monkeypatch.setattr(game_data.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(
        game_data.engine,
        'load_data',
        lambda: {'projects': {}, 'global_streaks': []},
    )

    days_to_afford = item.price / _reference_daily_income(item.level)
    minimum_days, maximum_days = affordability

    assert minimum_days <= days_to_afford <= maximum_days, (
        f'«{registry_name}» из категории «{category}» стоит {item.price:g} '
        f'монет на {item.level} уровне: это {days_to_afford:.1f} типичных '
        f'игровых дней, допустимо {minimum_days:g}–{maximum_days:g}.'
    )
