import game
import game_UI


class FakeInventoryItem:
    def __init__(self, data):
        self._data = data

    def data(self, role):
        return self._data


class FakeInventoryList:
    def __init__(self, item):
        self._item = item

    def currentItem(self):
        return self._item


class FakeSpinBox:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


def make_controller(gamer, item_data, count):
    controller = game_UI.GameMenuController.__new__(game_UI.GameMenuController)
    controller.gamer = gamer
    controller.ui = type('FakeUi', (), {
        'centralwidget': None,
        'inventory_list': FakeInventoryList(FakeInventoryItem(item_data)),
        'value_for_use_selected_item': FakeSpinBox(count),
    })()
    controller.register_custom_awards = lambda: None
    controller.update_inventory = lambda: None
    controller.update_game_data = lambda **kwargs: None
    controller.clear_inventory_item_info = lambda: None
    controller.clear_item_info = lambda: None
    controller.update_after_inventory_sale = lambda item_name, sold_count, total_price: None
    return controller


class FakeNotifications:
    def __init__(self):
        self.successes = []
        self.errors = []

    def show_success(self, message):
        if not isinstance(message, str):
            raise TypeError(type(message).__name__)
        self.successes.append(message)

    def show_error(self, message):
        if not isinstance(message, str):
            raise TypeError(type(message).__name__)
        self.errors.append(message)


def test_sell_inventory_item_adds_75_percent_price_and_decreases_count(monkeypatch):
    monkeypatch.setattr(game.Gamer, 'save', lambda self: None)
    gamer = game.Gamer(level=1, coins=0)
    gamer.items = {
        'Предметы': {},
        'Зелья': {'Микро зелье здоровья': 2},
        'Награды': {},
    }
    controller = make_controller(gamer, ('Зелья', 'Микро зелье здоровья'), 1)

    monkeypatch.setattr(game_UI.game, 'load_game', lambda: gamer)
    monkeypatch.setattr(game_UI.QMessageBox, 'question', lambda *args, **kwargs: game_UI.QMessageBox.Yes)
    monkeypatch.setattr(game_UI.QMessageBox, 'warning', lambda *args, **kwargs: None)

    controller.on_sell_item()

    assert gamer.get_coins() == 7.5
    assert gamer.items['Зелья']['🧪  Микро зелье здоровья'] == 1


def test_item_sellable_flag_and_sell_price():
    item = game_UI.game_data.Item('Тест', price=100, sellable=False)

    assert item.sellable is False
    assert item.sell_price == 75


def test_freeze_project_does_not_show_dialog_result_as_notification(monkeypatch):
    gamer = game.Gamer(level=3)
    gamer.items = {'Предметы': {'Заморозка': 1}, 'Зелья': {}, 'Награды': {}}
    notifications = FakeNotifications()
    controller = game_UI.GameMenuController.__new__(game_UI.GameMenuController)
    controller.gamer = gamer
    controller.notifications = notifications
    controller.update_inventory = lambda: None
    controller.refresh_all = lambda: None

    class FakeFreezeProject:
        def __init__(self, gamer=None):
            self.gamer = gamer

        def exec_(self):
            return game_UI.QDialog.Accepted

        def freeze(self):
            assert self.gamer is gamer
            return 'Проект "Book" заморожен!'

    monkeypatch.setattr(game_UI, 'FreezeProject', FakeFreezeProject)
    monkeypatch.setattr(game_UI.game, 'load_game', lambda: game.Gamer(level=3))

    assert controller.freeze_project() is True
    assert notifications.successes == ['Проект "Book" заморожен!']
    assert notifications.errors == []


def test_freeze_project_does_not_open_dialog_without_inventory(monkeypatch):
    gamer = game.Gamer(level=3)
    gamer.items = {'Предметы': {'Заморозка': 0}, 'Зелья': {}, 'Награды': {}}
    notifications = FakeNotifications()
    controller = game_UI.GameMenuController.__new__(game_UI.GameMenuController)
    controller.gamer = gamer
    controller.notifications = notifications
    controller.update_inventory = lambda: None

    class FakeFreezeProject:
        def __init__(self, gamer=None):
            raise AssertionError('dialog should not open')

    monkeypatch.setattr(game_UI, 'FreezeProject', FakeFreezeProject)
    monkeypatch.setattr(game_UI.game, 'load_game', lambda: gamer)

    assert controller.freeze_project() is False
    assert notifications.successes == []
    assert notifications.errors == ['В инвентаре нет заморозки.']
