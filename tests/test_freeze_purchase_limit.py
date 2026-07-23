import game
import game_UI
from PySide6.QtCore import Qt


class FakeList:
    def __init__(self):
        self.items = []

    def clear(self):
        self.items = []

    def addItem(self, item):
        self.items.append(item)


def make_controller(gamer):
    controller = game_UI.GameMenuController.__new__(game_UI.GameMenuController)
    controller.gamer = gamer
    controller.ui = type('FakeUi', (), {
        'item_shop_list': FakeList(),
        'potion_shop_list': FakeList(),
        'item_shop_list_2': FakeList(),
    })()
    controller.register_custom_awards = lambda: None
    return controller


def test_freeze_stays_in_shop_when_inventory_is_full(monkeypatch):
    gamer = game.Gamer(level=3)
    gamer.items = {'Предметы': {'Заморозка': 2}, 'Зелья': {}, 'Награды': {}}
    gamer.custom_awards = []
    controller = make_controller(gamer)

    monkeypatch.setattr(game_UI.game, 'load_game', lambda: gamer)

    controller.update_shops()

    shop_items = [
        item.data(Qt.ItemDataRole.UserRole)
        for item in controller.ui.item_shop_list.items
    ]
    assert ('Предметы', 'Заморозка') in shop_items
    assert all(
        item.data(Qt.ItemDataRole.DecorationRole) is None
        for item in controller.ui.item_shop_list.items
    )


def test_freeze_purchase_limit_allows_two_but_not_more(monkeypatch):
    gamer = game.Gamer(level=3)
    gamer.items = {'Предметы': {'Заморозка': 0}, 'Зелья': {}, 'Награды': {}}
    controller = make_controller(gamer)
    _, freeze_item = game_UI.game_data.find_registry_item('Предметы', 'Заморозка')

    monkeypatch.setattr(game_UI.game, 'load_game', lambda: gamer)

    assert controller.validate_registry_purchase_limit('Предметы', 'Заморозка', freeze_item, 2) is None

    gamer.items['Предметы']['Заморозка'] = 1
    assert controller.validate_registry_purchase_limit('Предметы', 'Заморозка', freeze_item, 1) is None
    assert controller.validate_registry_purchase_limit('Предметы', 'Заморозка', freeze_item, 2)

    gamer.items['Предметы']['Заморозка'] = 2
    assert controller.validate_registry_purchase_limit('Предметы', 'Заморозка', freeze_item, 1)


def test_single_copy_shop_items_cannot_be_purchased_twice():
    gamer = game.Gamer(level=3)
    gamer.items = {'Предметы': {'Печатная машинка Хемингуэя': 1}, 'Зелья': {}, 'Награды': {}}
    controller = make_controller(gamer)
    _, typewriter = game_UI.game_data.find_registry_item('Предметы', 'Печатная машинка Хемингуэя')

    assert typewriter.maximum_quantity_in_stock == 1
    assert controller.validate_registry_purchase_limit(
        'Предметы', 'Печатная машинка Хемингуэя', typewriter, 1
    )


def test_literary_slave_bonuses_stack_for_each_copy(monkeypatch):
    monkeypatch.setattr(game.Gamer, 'save', lambda self: None)
    gamer = game.Gamer(level=3)
    gamer.items = {'Предметы': {'Литературный раб': 2}, 'Зелья': {}, 'Награды': {}}
    gamer.update_cf()

    assert gamer.get_cf_value('exp') == game.game_data.cf_exp[3] + 0.5
    assert gamer.get_cf_value('coins') == gamer.round_cf(gamer.cf['coins']['base_value'] + 0.5)
