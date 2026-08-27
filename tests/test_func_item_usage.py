from datetime import datetime, timedelta, timezone

import game
import game_data


class FakeGamer:
    def __init__(self, items):
        self.items = items
        self.applied_buffs = []

    def get_items(self):
        return self.items

    def add_buff(self, buff):
        self.applied_buffs.append(buff)


def functional_item_aliases():
    return [
        (category, registry_key, item)
        for category, registry_items in game_data.ITEM_REGISTRY.items()
        for registry_key, item in registry_items.items()
        if isinstance(item, game_data.FuncItem) and registry_key != item.name
    ]


def test_all_functional_items_can_use_normalized_inventory_names(monkeypatch):
    for category, registry_key, item in functional_item_aliases():
        gamer = FakeGamer({category: {registry_key: 1}})
        monkeypatch.setattr(game_data.game, 'load_game', lambda gamer=gamer: gamer)
        monkeypatch.setattr(item, '_func', None)

        result = item.use()

        assert result, f'Не удалось использовать {registry_key}'


def test_timed_buff_accepts_timezone_aware_developer_clock(monkeypatch):
    current = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(game.engine, 'now_for_test', lambda: current)
    buff = game_data.Buff(
        'Тестовое зелье', 'Тестовый эффект', game_data.Buff.POSITIVE,
        'coins', 1, duration_minutes=60,
    )

    active = buff.activate()

    assert active.start_time.tzinfo is None
    assert active.remaining_time(current + timedelta(minutes=30)) == timedelta(minutes=30)
