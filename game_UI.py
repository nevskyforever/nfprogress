"""
Модуль для связи игрового интерфейса (main_window.py) с игровой логикой (game.py, game_data.py)
"""
import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QLabel, QDialog, QApplication

import engine
import game
import game_data
from UI_fiiles.freeze_project import Ui_freeze_projrct
from UI_fiiles.bank import Ui_Bamk
from UI_fiiles.create_custom_award import Ui_create_castom_item
from engine import load_data, save_data, today_for_test, unit_converter


class GameMenuController:
    """Класс для управления игровым меню"""

    def __init__(self, ui, notifications = None):
        """
        Инициализация контроллера игрового меню

        Args:
            ui: Объект интерфейса (Ui_main_window)
        """
        self.ui = ui
        self.notifications = notifications
        self.gamer = None

        # Загружаем игрока
        self.load_gamer()

        # Настраиваем начальные значения
        self.setup_ui_defaults()

        # Подключаем сигналы
        self.connect_signals()

        # Заполняем списки
        self.refresh_all()

        # Запускаем таймер для обновления (проверка уровня и т.д.)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game_data)
        self.timer.start(1000)  # Обновление каждую секунду

        # Скрываем банк
        self.ui.bank_btn.setVisible(False)

        # Просим выбрать элементы в мазазинах и инвентаре
        self.ui.name_selected_item_on_shop.setText('Выберите товар')
        self.ui.name_selected_potion_on_shop.setText('Выберите товар')
        self.ui.name_selected_custom_award_on_shop.setText('Выберите награду')
        self.ui.name_selected_item.setText('Выберите предмет')

    def load_gamer(self):
        """Загрузка или создание игрока"""
        self.gamer = game.load_game()
        if not self.gamer:
            self.gamer = game.Gamer()
            self.gamer.save()

    def setup_ui_defaults(self):
        """Настройка начальных значений интерфейса"""
        # Устанавливаем максимумы для spinbox'ов
        self.ui.gamer_params_label.setVisible(False)

        self.ui.parameters_tabs.setVisible(False)
        self.ui.quests_label.setVisible(False)
        self.ui.quests_tabs.setVisible(False)

        self.ui.value_for_use_selected_item.setMaximum(999)
        self.ui.value_for_buy_selected_item.setMaximum(999)
        self.ui.value_for_buy_selected_potion.setMaximum(999)
        self.ui.value_for_buy_selected_item_3.setMaximum(999)

        # Очищаем информационные поля
        self.clear_all_info()

    def clear_all_info(self):
        """Очистка всех информационных полей"""
        # Инвентарь
        self.ui.name_selected_item.clear()
        self.ui.description_selected_item.clear()
        self.ui.level_selected_item.clear()
        self.ui.effect_selected_item.clear()

        # Магазин предметов
        for widget in self.ui.scrollAreaWidgetContents_7.findChildren(QLabel):
            widget.clear()

        # Магазин зелий
        for widget in self.ui.scrollAreaWidgetContents_5.findChildren(QLabel):
            widget.clear()

    def connect_signals(self):
        """Подключение сигналов к слотам"""
        # Инвентарь
        self.ui.inventory_list.itemClicked.connect(self.on_inventory_item_selected)
        self.ui.button_for_selected_item.clicked.connect(self.on_use_item)

        # Магазин предметов
        self.ui.item_shop_list.itemClicked.connect(self.on_shop_item_selected)
        self.ui.button_for_buy_selected_item.clicked.connect(self.on_buy_item)

        # Магазин зелий
        self.ui.potion_shop_list.itemClicked.connect(self.on_potion_selected)
        self.ui.button_for_buy_selected_potion.clicked.connect(self.on_buy_potion)

        # Магазин наград
        self.ui.item_shop_list_2.itemClicked.connect(self.on_award_selected)
        self.ui.button_for_buy_selected_item_3.clicked.connect(self.on_buy_award)
        edit_award_button = self.get_edit_custom_award_button()
        if edit_award_button:
            edit_award_button.clicked.connect(self.edit_selected_custom_award)

        # Очистка информации при смене выбора в магазинах
        self.ui.item_shop_list.itemClicked.connect(lambda: self.clear_potion_info())
        self.ui.item_shop_list.itemClicked.connect(lambda: self.clear_award_info())
        self.ui.potion_shop_list.itemClicked.connect(lambda: self.clear_item_info())
        self.ui.potion_shop_list.itemClicked.connect(lambda: self.clear_award_info())
        self.ui.item_shop_list_2.itemClicked.connect(lambda: self.clear_item_info())
        self.ui.item_shop_list_2.itemClicked.connect(lambda: self.clear_potion_info())

        # Банк

        self.ui.bank_btn.clicked.connect(self.bank)

        # Создание своей награды

        self.ui.button_for_create_custom_award.clicked.connect(self.create_custom_award)

    def refresh_all(self):
        """Обновление всех данных в интерфейсе"""
        self.update_game_data()
        self.clear_all_info()
        self.clear_item_info()
        self.clear_award_info()
        self.update_inventory()
        self.update_shops()

    def update_game_data(self):
        """Обновление основных параметров игрока"""
        if not self.gamer:
            return

        # Проверяем уровень

        self.gamer.level_up()

        # Перезагружаем игрока для актуальных данных
        self.gamer = game.load_game()
        self.register_custom_awards()

        # Обновляем отображение
        self.ui.gamer_label.setText(str(self.gamer.level))
        self.ui.gamer_coins.setText(str(round(self.gamer.coins, 1)))

        # Опыт - получаем необходимое для следующего уровня
        current_level = self.gamer.level
        if current_level < len(game_data.levels):
            next_level_exp = game_data.levels[current_level]
            current_exp = self.gamer.exp

            # Форматируем текст
            self.ui.gamer_exp.setText(f"Опыт: {int(current_exp)}/{next_level_exp}")

            # Вычисляем прогресс в процентах
            if next_level_exp > 0:
                exp_progress = (current_exp / next_level_exp) * 100
                self.ui.exp_progressbar.setValue(int(exp_progress))
                self.ui.exp_progressbar.setMaximum(100)
            else:
                self.ui.exp_progressbar.setValue(0)
        else:
            # Максимальный уровень
            self.ui.gamer_exp.setText(f"Опыт: {int(self.gamer.exp)}/MAX")
            self.ui.exp_progressbar.setValue(100)

        # Здоровье
        health = max(0, min(100, self.gamer.health))  # Ограничиваем 0-100
        self.ui.gamer_health.setText(f"Здоровье: {health}/100")
        self.ui.gamer_health_progressbar.setValue(health)
        self.ui.gamer_health_progressbar.setMaximum(100)

        # Проверяем критические состояния
        if self.gamer.health <= 20 and self.gamer.health > 0:
            self.show_health_warning()
        elif self.gamer.health <= 0:
            self.show_death_warning()

    def update_inventory(self):
        """Обновление списка инвентаря"""
        self.ui.inventory_list.clear()

        if not self.gamer:
            return

        self.register_custom_awards()

        # Инвентарь: {категория: {предмет: количество}}
        for category, items in self.gamer.items.items():
            for item_name, count in items.items():
                if count > 0:
                    display_text = f"{item_name} x{count} [{category}]"
                    item = QListWidgetItem(display_text)
                    # Сохраняем данные предмета (категория, имя)
                    item.setData(1, (category, item_name))
                    self.ui.inventory_list.addItem(item)

        for award in self.gamer.custom_awards:
            count = self.get_custom_award_count(award)
            if count > 0:
                display_text = f"{award.name} x{count} [Награды]"
                item = QListWidgetItem(display_text)
                item.setData(1, ('Кастомные награды', award.name))
                self.ui.inventory_list.addItem(item)

    def update_shops(self):
        """Обновление магазинов"""
        self.register_custom_awards()

        # Магазин предметов
        self.ui.item_shop_list.clear()
        if 'Предметы' in game_data.ITEM_REGISTRY:
            for item_name, item_obj in game_data.ITEM_REGISTRY['Предметы'].items():
                if game.load_game().level >= item_obj.level:
                    # Проверяем кол-во заморозок в инвентаре и скрываем их, если их больше 2
                    if item_name == 'Заморозка' and game.load_game().items['Предметы'].get('Заморозка', 0) >= 2:
                        continue
                    display_text = f"{item_name}"
                    item = QListWidgetItem(display_text)
                    item.setData(1, ('Предметы', item_name))
                    self.ui.item_shop_list.addItem(item)
                else:
                    continue

        # Магазин зелий
        self.ui.potion_shop_list.clear()
        if 'Зелья' in game_data.ITEM_REGISTRY:
            for potion_name, potion_obj in game_data.ITEM_REGISTRY['Зелья'].items():
                if game.load_game().level >= potion_obj.level:
                    display_text = f"{potion_name}"
                    item = QListWidgetItem(display_text)
                    item.setData(1, ('Зелья', potion_name))
                    self.ui.potion_shop_list.addItem(item)
                else:
                    continue

        # Магазин кастомных наград
        self.ui.item_shop_list_2.clear()
        for award in self.gamer.custom_awards:
            display_text = f"{award.name}"
            item = QListWidgetItem(display_text)
            item.setData(1, ('Награды', award.name))
            self.ui.item_shop_list_2.addItem(item)

    # === ОБРАБОТЧИКИ ИНВЕНТАРЯ ===

    def on_inventory_item_selected(self, item):
        """Выбор предмета в инвентаре"""
        category, item_name = item.data(1)

        if category == 'Кастомные награды':
            award = self.get_custom_award(item_name)
            if not award:
                return

            count = self.get_custom_award_count(award)
            self.ui.name_selected_item.setText(f"🏆 {award.name}")
            self.ui.description_selected_item.setText(f"📝 {award.description}")
            self.ui.level_selected_item.setText("⭐ Уровень: 1")
            self.ui.effect_selected_item.setText(
                f"⚡ Нет эффекта\n🔢 В наличии: {count}"
            )
            self.ui.value_for_use_selected_item.setMaximum(count)
            return

        # Получаем объект предмета из реестра
        if category in game_data.ITEM_REGISTRY and item_name in game_data.ITEM_REGISTRY[category]:
            item_obj = game_data.ITEM_REGISTRY[category][item_name]

            # Отображаем информацию
            self.ui.name_selected_item.setText(f"📦 {item_obj.name}")
            self.ui.description_selected_item.setText(f"📝 {item_obj.description}")
            self.ui.level_selected_item.setText(f"⭐ Уровень: {item_obj.level}")

            # Получаем эффект, если есть функция
            effect_text = "Нет эффекта"
            if hasattr(item_obj, '_func') and item_obj._func:
                try:
                    effect_text = item_obj._func("?") or "Активируется при использовании"
                except:
                    effect_text = "Активируется при использовании"

            # Добавляем информацию о количестве
            count = self.gamer.items.get(category, {}).get(item_name, 0)
            self.ui.effect_selected_item.setText(
                f"⚡ {effect_text}\n🔢 В наличии: {count}"
            )

            # Устанавливаем максимум для spinbox
            self.ui.value_for_use_selected_item.setMaximum(count)

    def on_use_item(self):
        """Использование выбранного предмета несколько раз"""
        selected = self.ui.inventory_list.currentItem()
        if not selected:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Выберите предмет")
            return

        category, item_name = selected.data(1)
        count = self.ui.value_for_use_selected_item.value()

        if category == 'Кастомные награды':
            self.use_custom_award(item_name, count)
            return

        # Проверяем наличие
        available = self.gamer.items.get(category, {}).get(item_name, 0)
        if count > available:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"У вас только {available} шт."
            )
            return

        # Получаем объект предмета
        if category not in game_data.ITEM_REGISTRY or item_name not in game_data.ITEM_REGISTRY[category]:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Предмет не найден")
            return

        item_obj = game_data.ITEM_REGISTRY[category][item_name]

        # Особый случай: Заморозка (используется один раз за вызов)
        if item_name == 'Заморозка':
            self.freeze_project()
            return

        # Проверяем наличие метода use
        if not hasattr(item_obj, 'use'):
            QMessageBox.information(
                self.ui.centralwidget,
                "Информация",
                f"{item_name} нельзя использовать"
            )
            return

        # Используем предмет count раз
        result_messages = []
        success_count = 0

        for i in range(count):
            try:
                # Вызываем функцию предмета (она сама изменяет состояние игрока и сохраняет)
                result = item_obj.use()
                result_messages.append(f"✓ {result}")
                success_count += 1
            except Exception as e:
                result_messages.append(f"✗ Ошибка: {str(e)}")
                break

        if success_count > 0:
            # Перезагружаем игрока, чтобы получить актуальные монеты/здоровье после всех использований
            self.gamer = game.load_game()
            # Уменьшаем количество использованных предметов в инвентаре (предполагаем, что use не трогает items)
            self.gamer.items[category][item_name] -= success_count
            # Сохраняем обновлённый инвентарь
            self.gamer.save()

            # Обновляем интерфейс
            self.update_inventory()
            self.update_game_data()

            # Очищаем панель информации до показа диалога, чтобы устаревший текст не был виден
            self.clear_inventory_item_info()
            self.clear_item_info()

            QMessageBox.information(
                self.ui.centralwidget,
                "Результат",
                "\n".join(result_messages)
            )
        else:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                "Не удалось использовать предмет"
            )
            self.clear_inventory_item_info()
            self.clear_item_info()

    # === ОБРАБОТЧИКИ МАГАЗИНА ===

    def on_shop_item_selected(self, item):
        """Выбор предмета в магазине"""
        self.clear_potion_info()  # Очищаем информацию о зельях
        category, item_name = item.data(1)
        self.show_item_info(category, item_name, is_potion=False)

    def on_potion_selected(self, item):
        """Выбор зелья в магазине"""
        self.clear_item_info()  # Очищаем информацию о предметах
        category, item_name = item.data(1)
        self.show_item_info(category, item_name, is_potion=True)

    def on_award_selected(self, item):
        """Выбор кастомной награды в магазине"""
        category, item_name = item.data(1)
        self.show_award_info(category, item_name)

    def show_item_info(self, category, item_name, is_potion=False):
        """Отображение информации о предмете в магазине"""
        if category not in game_data.ITEM_REGISTRY or item_name not in game_data.ITEM_REGISTRY[category]:
            return

        item_obj = game_data.ITEM_REGISTRY[category][item_name]

        # Определяем, какой ScrollArea использовать
        if is_potion:
            scroll_area = self.ui.scrollAreaWidgetContents_5
            # Для зелий используем соответствующие виджеты
            name_label = self.ui.name_selected_potion_on_shop
            desc_label = self.ui.description_selected_potion_on_shop
            price_label = self.ui.price_selected_potion_on_shop
            effect_label = self.ui.effect_selected_potion_on_shop
            prefix = "🧪"
        else:
            scroll_area = self.ui.scrollAreaWidgetContents_7
            # Для предметов используем соответствующие виджеты
            name_label = self.ui.name_selected_item_on_shop
            desc_label = self.ui.description_selected_item_on_shop
            price_label = self.ui.peice_selected_item_on_shop
            effect_label = self.ui.effect_selected_item_on_shop
            prefix = "📦"

        # Заполняем информацию
        name_label.setText(f"{prefix} {item_obj.name}")
        desc_label.setText(f"📝 {item_obj.description}")
        price_label.setText(f"💰 Цена: {item_obj.price}")

        # Получаем эффект
        effect_text = "Нет эффекта"
        if hasattr(item_obj, '_func') and item_obj._func:
            try:
                effect_text = item_obj._func("?") or "Активируется при использовании"
            except:
                effect_text = "Активируется при использовании"
        effect_label.setText(f"⚡ {effect_text}")

    def clear_item_info(self):
        """Очистка информации о предметах в магазине"""
        self.ui.name_selected_item_on_shop.setText('Выберите товар')
        self.ui.description_selected_item_on_shop.clear()
        self.ui.peice_selected_item_on_shop.clear()
        self.ui.effect_selected_item_on_shop.clear()

    def clear_potion_info(self):
        """Очистка информации о зельях в магазине"""
        self.ui.name_selected_potion_on_shop.setText('Выберите товар')
        self.ui.description_selected_potion_on_shop.clear()
        self.ui.price_selected_potion_on_shop.clear()
        self.ui.effect_selected_potion_on_shop.clear()

    def show_award_info(self, category, item_name):
        """Отображение информации о кастомной награде в магазине."""
        if category not in game_data.ITEM_REGISTRY or item_name not in game_data.ITEM_REGISTRY[category]:
            return

        award = game_data.ITEM_REGISTRY[category][item_name]
        self.ui.name_selected_custom_award_on_shop.setText(f"🏆 {award.name}")
        self.ui.peice_selected_custom_award_on_shop.setText(f"💰 Цена: {award.price}")

    def clear_award_info(self):
        """Очистка информации о награде в магазине."""
        self.ui.name_selected_custom_award_on_shop.setText('Выберите награду')
        self.ui.peice_selected_custom_award_on_shop.clear()

    def clear_inventory_item_info(self):
        """Очистка информации о предмете"""
        self.ui.name_selected_item.setText("Выберите предмет")
        self.ui.level_selected_item.clear()
        self.ui.description_selected_item.clear()
        self.ui.effect_selected_item.clear()
        self.ui.value_for_use_selected_item.setValue(1)
        self.ui.value_for_use_selected_item.setMaximum(999)

    def on_buy_item(self):
        """Покупка предмета"""
        self.buy_selected_item(
            self.ui.item_shop_list,
            self.ui.value_for_buy_selected_item,
            "Предметы"
        )

    def on_buy_potion(self):
        """Покупка зелья"""
        self.buy_selected_item(
            self.ui.potion_shop_list,
            self.ui.value_for_buy_selected_potion,
            "Зелья"
        )

    def on_buy_award(self):
        """Покупка кастомной награды."""
        self.buy_selected_custom_award()

    def edit_selected_custom_award(self):
        """Редактирование выбранной кастомной награды."""
        selected = self.ui.item_shop_list_2.currentItem()
        if not selected:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Выберите награду")
            return

        category, item_name = selected.data(1)
        if category != "Награды":
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Этот товар не является наградой")
            return

        award = self.get_custom_award(item_name)
        if not award:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Награда не найдена")
            return

        old_name = award.name
        dialog = EditCustomAward(self.gamer, award)
        result = dialog.exec()
        if result != QDialog.Accepted:
            return

        new_name = dialog.get_name()
        new_price = dialog.get_price()

        self.gamer = game.load_game()
        self.register_custom_awards()
        award = self.get_custom_award(old_name)
        if not award:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Награда не найдена")
            return

        if new_name != old_name and self.get_custom_award(new_name):
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                "Награда с таким названием уже существует"
            )
            return

        award.name = new_name
        award._price = new_price
        award.item_type = 'Награды'
        if not getattr(award, 'description', None):
            award.description = 'Кастомная награда без эффекта'

        if hasattr(self.gamer, 'custom_awards_inventory') and old_name in self.gamer.custom_awards_inventory:
            self.gamer.custom_awards_inventory[new_name] = self.gamer.custom_awards_inventory.pop(old_name)

        if 'Награды' in self.gamer.items and old_name in self.gamer.items['Награды']:
            self.gamer.items['Награды'][new_name] = self.gamer.items['Награды'].pop(old_name)

        if 'Награды' in game_data.ITEM_REGISTRY:
            game_data.ITEM_REGISTRY['Награды'].pop(old_name, None)
            game_data.ITEM_REGISTRY['Награды'][new_name] = award

        self.gamer.save()
        self.gamer = game.load_game()
        self.register_custom_awards()
        self.update_shops()
        self.update_inventory()
        self.select_custom_award_in_shop(new_name)
        self.show_award_info('Награды', new_name)
        self.notifications.show_success('Награда изменена')

    def buy_selected_item(self, shop_list, spinbox, expected_category):
        """Общая логика покупки"""
        selected = shop_list.currentItem()
        if not selected:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Выберите товар")
            return

        category, item_name = selected.data(1)

        # Проверяем категорию
        if category != expected_category:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"Этот товар не из категории {expected_category}"
            )
            return

        count = spinbox.value()

        # Если выбрана заморозка и пытаются купить больше одной
        if item_name == 'Заморозка' and count > 1:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"Нельзя купить больше одной заморозки за раз"
            )
        else:

            if category in game_data.ITEM_REGISTRY and item_name in game_data.ITEM_REGISTRY[category]:
                item_obj = game_data.ITEM_REGISTRY[category][item_name]
                total_price = item_obj.price * count

                # Проверяем достаточно ли монет
                if self.gamer.coins < total_price:
                    QMessageBox.warning(
                        self.ui.centralwidget,
                        "Ошибка",
                        f"Недостаточно монет!\nНужно: {total_price}💰\nУ вас: {int(self.gamer.coins)}💰"
                    )
                    return

                # Подтверждение покупки
                reply = QMessageBox.question(
                    self.ui.centralwidget,
                    "Подтверждение покупки",
                    f"Купить {count} x {item_name} за {total_price}💰?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.No:
                    return

                # Покупаем предметы
                success_count = 0
                for i in range(count):
                    result = item_obj.buy()
                    if "Недостаточно" not in result:
                        success_count += 1
                    else:
                        QMessageBox.warning(
                            self.ui.centralwidget,
                            "Ошибка",
                            f"Покупка остановлена: {result}"
                        )
                        break

                if success_count > 0:
                    # Перезагружаем игрока для актуальных данных
                    self.gamer = game.load_game()
                    self.register_custom_awards()
                    self.update_game_data()
                    self.update_inventory()

                    QMessageBox.information(
                        self.ui.centralwidget,
                        "Успех",
                        f"✅ Куплено {success_count} x {item_name}\n"
                        f"Потрачено: {item_obj.price * success_count}💰"
                    )
                    self.clear_item_info()
                    self.clear_award_info()
                    self.clear_inventory_item_info()
                    self.update_shops()

    def buy_selected_custom_award(self):
        """Покупка кастомной награды с хранением в gamer.custom_awards."""
        selected = self.ui.item_shop_list_2.currentItem()
        if not selected:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Выберите награду")
            return

        category, item_name = selected.data(1)
        if category != "Награды":
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Этот товар не является наградой")
            return

        award = self.get_custom_award(item_name)
        if not award:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Награда не найдена")
            return

        count = self.ui.value_for_buy_selected_item_3.value()
        total_price = award.price * count

        if self.gamer.coins < total_price:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"Недостаточно монет!\nНужно: {total_price}💰\nУ вас: {int(self.gamer.coins)}💰"
            )
            return

        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Подтверждение покупки",
            f"Купить {count} x {item_name} за {total_price}💰?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        self.gamer.remove_coins(total_price)
        self.set_custom_award_count(item_name, self.get_custom_award_count(award) + count)
        self.gamer.save()

        self.gamer = game.load_game()
        self.register_custom_awards()
        self.gamer.save()
        self.update_game_data()
        self.update_shops()
        self.clear_award_info()
        self.clear_inventory_item_info()
        self.update_inventory()
        QApplication.processEvents()

        QMessageBox.information(
            self.ui.centralwidget,
            "Успех",
            f"✅ Куплено {count} x {item_name}\nПотрачено: {total_price}💰"
        )

    def use_custom_award(self, item_name, count):
        """Использование кастомной награды без игрового эффекта."""
        award = self.get_custom_award(item_name)
        if not award:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Награда не найдена")
            return

        available = self.get_custom_award_count(award)
        if count > available:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"У вас только {available} шт."
            )
            return

        self.set_custom_award_count(item_name, available - count)
        self.gamer.save()
        self.gamer = game.load_game()
        self.register_custom_awards()
        self.update_inventory()
        self.update_game_data()
        self.clear_inventory_item_info()

        QMessageBox.information(
            self.ui.centralwidget,
            "Результат",
            f"🏆 Использовано {count} x {item_name}\nЭффекта нет."
        )


    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

    def register_custom_awards(self):
        """Синхронизирует сохранённые кастомные награды с реестром предметов."""
        if not self.gamer:
            return

        if not hasattr(self.gamer, 'custom_awards') or self.gamer.custom_awards is None:
            self.gamer.custom_awards = []
        if not hasattr(self.gamer, 'custom_awards_inventory') or self.gamer.custom_awards_inventory is None:
            self.gamer.custom_awards_inventory = {}

        if 'Награды' not in game_data.ITEM_REGISTRY:
            game_data.ITEM_REGISTRY['Награды'] = {}

        changed = False
        for award in self.gamer.custom_awards:
            if getattr(award, 'item_type', None) != 'Награды':
                award.item_type = 'Награды'
                changed = True
            if not hasattr(award, 'level'):
                award.level = 1
                changed = True
            if not getattr(award, 'description', None):
                award.description = 'Кастомная награда без эффекта'
                changed = True
            if not hasattr(award, 'count'):
                award.count = 0
                changed = True
            if award.count > 0:
                self.gamer.custom_awards_inventory[award.name] = (
                    self.gamer.custom_awards_inventory.get(award.name, 0) + award.count
                )
                award.count = 0
                changed = True

            old_inventory_count = self.gamer.items.get('Награды', {}).get(award.name, 0)
            if old_inventory_count > 0:
                self.gamer.custom_awards_inventory[award.name] = (
                    self.gamer.custom_awards_inventory.get(award.name, 0) + old_inventory_count
                )
                self.gamer.items['Награды'].pop(award.name, None)
                changed = True

            game_data.ITEM_REGISTRY['Награды'][award.name] = award

        if 'Награды' not in self.gamer.items:
            self.gamer.items['Награды'] = {}
            changed = True

        if changed:
            self.gamer.save()

    def get_edit_custom_award_button(self):
        """Возвращает кнопку редактирования награды с учётом разных имён в UI."""
        return (
            getattr(self.ui, 'button_for_edit_selected_custom_award', None) or
            getattr(self.ui, 'button_for_edit_aelected_custom_award', None) or
            getattr(self.ui, 'button_for_edit_custom_award', None)
        )

    def select_custom_award_in_shop(self, name):
        """Выбирает награду в списке магазина после изменения."""
        for row in range(self.ui.item_shop_list_2.count()):
            item = self.ui.item_shop_list_2.item(row)
            item_data = item.data(1)
            if item_data == ('Награды', name):
                self.ui.item_shop_list_2.setCurrentItem(item)
                return

    def get_custom_award(self, name):
        """Возвращает кастомную награду игрока по названию."""
        for award in self.gamer.custom_awards:
            if award.name == name:
                return award
        return None

    def get_custom_award_count(self, award):
        """Возвращает количество купленных экземпляров кастомной награды."""
        if not hasattr(self.gamer, 'custom_awards_inventory') or self.gamer.custom_awards_inventory is None:
            self.gamer.custom_awards_inventory = {}
        return self.gamer.custom_awards_inventory.get(award.name, 0)

    def set_custom_award_count(self, award_name, count):
        """Обновляет количество купленных экземпляров кастомной награды."""
        if not hasattr(self.gamer, 'custom_awards_inventory') or self.gamer.custom_awards_inventory is None:
            self.gamer.custom_awards_inventory = {}
        self.gamer.custom_awards_inventory[award_name] = max(0, count)

    def show_health_warning(self):
        """Показать предупреждение о низком здоровье"""
        if hasattr(self, '_health_warning_shown') and self._health_warning_shown:
            return

        self._health_warning_shown = True

        # Проверяем наличие зелий
        has_health_potion = False
        if 'Зелья' in self.gamer.items:
            for potion_name in self.gamer.items['Зелья']:
                if 'здоровья' in potion_name.lower() and self.gamer.items['Зелья'][potion_name] > 0:
                    has_health_potion = True
                    break

        msg = f"⚠️ КРИТИЧЕСКИЙ УРОВЕНЬ ЗДОРОВЬЯ! ⚠️\n\n"
        msg += f"Ваше здоровье: {self.gamer.health}/100\n\n"

        if has_health_potion:
            msg += "💊 У вас есть зелья здоровья в инвентаре!\n"
            msg += "Используйте их немедленно!"
        else:
            msg += "🏪 Купите зелья здоровья в магазине!\n"
            msg += "Цены от 10💰"

        QMessageBox.warning(self.ui.centralwidget, "Критическое здоровье!", msg)

        # Сбрасываем флаг через 30 секунд
        QTimer.singleShot(30000, lambda: setattr(self, '_health_warning_shown', False))

    def show_death_warning(self):
        """Показать предупреждение о смерти и попытаться воскресить персонажа"""
        revival_name = 'Зелье воскрешения'
        has_revival_potion = self.gamer.items.get('Зелья', {}).get(revival_name, 0) > 0

        if has_revival_potion:
            self.gamer.items['Зелья'][revival_name] -= 1
            self.gamer.health = 100
            self.gamer.save()
            self._death_warning_shown = False
            self.update_inventory()
            self.update_game_data()
            QMessageBox.information(
                self.ui.centralwidget,
                "Воскрешение",
                "💀 Ваше здоровье закончилось, но зелье воскрешения спасло вас!\n"
                "Здоровье восстановлено до 100, прогресс сохранён."
            )
            return

        revival_item = game_data.ITEM_REGISTRY['Зелья'][revival_name]
        revival_price = revival_item.price
        if self.gamer.coins >= revival_price:
            choice = QMessageBox.question(
                self.ui.centralwidget,
                "Воскрешение",
                f"💀 Ваше здоровье закончилось!\n\n"
                f"Купить и использовать зелье воскрешения за {revival_price} монет, "
                f"чтобы избежать сброса прогресса?",
                QMessageBox.Yes | QMessageBox.No
            )
            if choice == QMessageBox.Yes:
                self.gamer.coins -= revival_price
                self.gamer.health = 100
                self.gamer.save()
                self._death_warning_shown = False
                self.update_game_data()
                QMessageBox.information(
                    self.ui.centralwidget,
                    "Воскрешение",
                    "Вы воскрешены! Здоровье восстановлено до 100, прогресс сохранён."
                )
                return

        if hasattr(self, '_death_warning_shown') and self._death_warning_shown:
            self.gamer.level = 1
            self.gamer.coins /= 2
            self.gamer.exp = 0
            self.gamer.items = {}
            self.gamer.health = 100
            self.gamer.save()
            return

        self._death_warning_shown = True

        msg = "💀 ВАШ ПЕРСОНАЖ ПОГИБ! 💀\n\n"
        msg += "Прогресс сброшен до 1 уровня, вы потеряли половину монет, весь опыт и предметы в инвентаре.\n"
        msg += "Будьте внимательнее со здоровьем!"

        QMessageBox.critical(self.ui.centralwidget, "Персонаж погиб", msg)

        # Сбрасываем флаг через минуту
        QTimer.singleShot(60000, lambda: setattr(self, '_death_warning_shown', False))

    def add_symbols(self, symbols_count):
        """
        Добавление написанных символов (вызывается из основного окна)

        Args:
            symbols_count: Количество написанных символов
        """
        if not self.gamer:
            return "Игровой режим не активен"

        result = self.gamer.give_symbol_bonus(symbols_count)
        if result:
            level_up_msg = self.gamer.level_up()  # <-- сохраняем сообщение
            if level_up_msg:
                self.notifications.show_success(level_up_msg)  # <-- показываем сразу
            self.gamer.save()
            self.gamer = game.load_game()  # Перезагружаем для актуальности
            self.update_game_data()
            self.update_inventory()
            self.notifications.show_success(result)
            return result
        return

    def give_streak_bonus(self, streak_status, streak_type=None, streak_len=1):
        """
        Добавление написанных символов (вызывается из основного окна)

        Args:
            streak_status: Статус стрика
            streak_type: Вид стрика
            streak_len: Длина стрика в днях
        """
        if not self.gamer:
            return "Игровой режим не активен"

        result = self.gamer.give_streak_bonus(streak_status, streak_type, streak_len)
        if result:
            self.gamer.save()
            self.gamer = game.load_game()  # Перезагружаем для актуальности
            self.update_game_data()
            self.notifications.show_success(result)
            return True
        return

    def give_complete_bonus(self, project_status, project_total, project_unit='symbols'):
        """
        Начисление бонуса за завершение проекта (вызывается из основного окна)

        Args:
            project_status: Статус проекта
            project_total: Общее количество в единицах проекта
            project_unit: Единица измерения проекта ('symbols', 'A4', 'author_list', 'ficbook_pages')
        """
        if not self.gamer:
            return "Игровой режим не активен"

        # Конвертируем количество в символы для передачи в game.py
        symbols_value = unit_converter(project_unit, project_total, 'symbols')

        # Если конвертация не удалась, используем исходное значение
        if symbols_value is None:
            symbols_value = project_total

        # Передаем в game.py уже конвертированное значение в символах
        result = self.gamer.give_complete_bonus(project_status, symbols_value)

        if result:
            # Проверяем, не повысился ли уровень
            level_up_msg = self.gamer.level_up()
            if level_up_msg:
                self.notifications.show_success(level_up_msg)

            self.gamer.save()
            self.gamer = game.load_game()  # Перезагружаем для актуальности
            self.update_game_data()
            self.update_inventory()
            self.notifications.show_success(result)
            return True
        return

    def freeze_project(self):
        dialog = FreezeProject()
        result = dialog.exec_()
        if result == QDialog.Accepted:
            msg = dialog.freeze()
            self.gamer.items['Предметы']['Заморозка'] -= 1
            self.gamer.save()
            self.notifications.show_success(msg)
            self.update_inventory()
            self.refresh_all()
            self.notifications.show_success(result)
            return True
        dialog.close()

    def bank(self):
        dialog = Bank(self.gamer)
        dialog.show()
        result = dialog.exec_()

    def create_custom_award(self):
        dialog = CreateCustomAward(self.gamer)
        dialog.show()
        result = dialog.exec_()

        if result == QDialog.Accepted:
            name = dialog.get_name()
            price = dialog.get_price()
            self.gamer = game.load_game()
            self.register_custom_awards()

            if name in game_data.ITEM_REGISTRY.get('Награды', {}):
                QMessageBox.warning(
                    self.ui.centralwidget,
                    "Ошибка",
                    "Награда с таким названием уже существует"
                )
                return

            new_award = game_data.Item(
                name=name,
                price=price,
                item_type='Награды',
                description='Кастомная награда без эффекта'
            )
            new_award.count = 0

            self.gamer.custom_awards.append(new_award)
            self.gamer.save()
            self.gamer = game.load_game()
            self.register_custom_awards()
            self.update_shops()
            self.update_inventory()
            self.clear_award_info()
            self.notifications.show_success('Награда создана')

class FreezeProject(QDialog, Ui_freeze_projrct):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.load_projects()

    def load_projects(self):
        """Загружает проекты, которые можно заморозить"""
        # Загружаем данные
        data = load_data()
        today = today_for_test()
        yesterday = today - datetime.timedelta(days=1)

        projects = list(data['projects'].values())

        # Очищаем список
        self.list_projects.clear()

        for project in projects:
            # Проверяем, есть ли у проекта стрики
            if not project.streaks:
                continue

            # Получаем последний день стрика
            last_streak_day = project.streaks[-1]

            # Получаем статус стрика
            streak_status = project.get_streak_status()

            # Проект можно заморозить если последний стрик был вчера
            # и статус 'Active' (активный, но не продленный)
            if streak_status in ['Active', 'Freeze']:
                display_text = f"{project.name} (стрик: {len(project.streaks)} дн.)"
                item = QListWidgetItem(display_text)
                # Сохраняем объект проекта или его имя для последующего использования
                item.setData(1, project.name)
                self.list_projects.addItem(item)

        # Если нет проектов для заморозки, показываем информационное сообщение
        if self.list_projects.count() == 0:
            item = QListWidgetItem("❌ Нет проектов для заморозки")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)  # делаем невыбираемым
            self.list_projects.addItem(item)
            # Делаем кнопку подтверждения неактивной
            self.buttonBox.setEnabled(False)
        else:
            self.buttonBox.setEnabled(True)

    def freeze(self):
        """Заморозка выбранного проекта"""
        current_item = self.list_projects.currentItem()
        if not current_item:
            return "Выберите проект для заморозки"

        project_name = current_item.data(1)
        if not project_name:
            return "Ошибка: не удалось определить проект"

        data = load_data()
        today = today_for_test()

        if project_name in data['projects']:
            project = data['projects'][project_name]

            # Добавляем сегодняшний день в стрик (заморозка)
            project.streaks.append(today)
            project.streak_status = 'Freeze'
            project.freezes += 1
            data['global_streaks'].append(today)
            data['global_streak_status'] = 'Freeze'

            # Обновляем максимальный стрик если нужно
            if len(project.streaks) > project.max_streak:
                project.max_streak = len(project.streaks)

            data['projects'][project_name] = project
            save_data(data)
            return f'Проект "{project_name}" заморожен!'

        return f'Ошибка: проект "{project_name}" не найден'

class Bank(QDialog, Ui_Bamk):
    def __init__(self, gamer: game.Gamer):
        super().__init__()
        self.setupUi(self)
        self.gamer = gamer

        # Скрываем кнопку взятия кредита, если уровень меньше 3
        if gamer.level < 3:
            self.credit_status.setVisible(False)
            self.take_credit_btn.setVisible(False)

        # Убираем кнопки возврата продуктов
        self.return_credit_btn.setVisible(False)
        self.return_deposit_btn.setVisible(False)

        # Убираем даты возврата
        self.return_credit_date.setVisible(False)
        self.return_deposit_date.setVisible(False)

        # Убираем суммы к возврату
        self.credit_total_sum.setVisible(False)
        self.deposit_total_sum.setVisible(False)

        # Получаем банковский аккаунт
        account: game_data.BankAccount = self.gamer.bank_account
        # Получаем из него продукты
        credit: game_data.Credit = account.credit
        deposit: game_data.Deposit = account.deposit

        # Устанавливаем статусы продуктов и даты возврата
        if credit:
            self.credit_status.setText(credit.get_status())
            self.return_credit_date.setVisible(True)
            self.return_credit_date.setText(credit.get_return_date())
            # Скрываем кнопку взятия
            self.take_credit_btn.setVisible(False)
            # Показываем кнопку возврата
            self.return_credit_btn.setVisible(True)
        if deposit:
            # Получаем данные
            self.deposit_status.setText(deposit.get_status())
            self.return_deposit_date.setVisible(True)
            self.return_deposit_date.setText(deposit.get_return_date())
            # Скрываем кнопку взятия
            self.make_deposit_btn.setVisible(False)
            if deposit.get_return_date() <= engine.today_for_test():
                self.return_deposit_btn.setVisible(True)

        def take_credit():
            """Метод дял взятия кредита''"""
            pass

class CreateCustomAward(QDialog, Ui_create_castom_item):
    def __init__(self, gamer: game.Gamer):
        super().__init__()
        self.setupUi(self)
        self.gamer = gamer
        self.awards = gamer.custom_awards

        try:
            self.buttonBox.accepted.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.buttonBox.accepted.connect(self.on_accept)

    def on_accept(self):
        try:
            self.get_price()
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка", str(error))
            return

        self.accept()

    def get_name(self):
        name = self.award_name_le.text().strip()
        return name or "Новая награда"

    def get_price(self):
        price_text = self.award_price_le.text().strip().replace(',', '.')
        if not price_text:
            return 1

        try:
            price = float(price_text)
        except ValueError:
            raise ValueError("Стоимость должна быть числом")

        if price <= 0:
            raise ValueError("Стоимость должна быть больше 0")
        return round(price, 1)


class EditCustomAward(CreateCustomAward):
    def __init__(self, gamer: game.Gamer, award: game_data.Item):
        super().__init__(gamer)
        self.award = award
        self.setWindowTitle('Редактирование награды')
        self.award_name_le.setText(award.name)
        self.award_price_le.setText(str(award.price))
