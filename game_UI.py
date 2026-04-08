"""
Модуль для связи игрового интерфейса (main_window.py) с игровой логикой (game.py, game_data.py)
"""
import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QLabel, QDialog

import engine
import game
import game_data
from UI_fiiles.freeze_project import Ui_freeze_projrct
from UI_fiiles.bank import Ui_Bamk
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

        # Очистка информации при смене выбора в магазинах
        self.ui.item_shop_list.itemClicked.connect(lambda: self.clear_potion_info())
        self.ui.potion_shop_list.itemClicked.connect(lambda: self.clear_item_info())

        # Банк

        self.ui.bank_btn.clicked.connect(self.bank)

    def refresh_all(self):
        """Обновление всех данных в интерфейсе"""
        self.update_game_data()
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

        if not self.gamer or not self.gamer.items:
            return

        # Инвентарь: {категория: {предмет: количество}}
        for category, items in self.gamer.items.items():
            for item_name, count in items.items():
                if count > 0:
                    display_text = f"{item_name} x{count} [{category}]"
                    item = QListWidgetItem(display_text)
                    # Сохраняем данные предмета (категория, имя)
                    item.setData(1, (category, item_name))
                    self.ui.inventory_list.addItem(item)

    def update_shops(self):
        """Обновление магазинов"""
        # Магазин предметов
        self.ui.item_shop_list.clear()
        if 'Предметы' in game_data.ITEM_REGISTRY:
            for item_name, item_obj in game_data.ITEM_REGISTRY['Предметы'].items():
                if game.load_game().level >= item_obj.level:
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

    # === ОБРАБОТЧИКИ ИНВЕНТАРЯ ===

    def on_inventory_item_selected(self, item):
        """Выбор предмета в инвентаре"""
        category, item_name = item.data(1)

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

    def clear_inventory_item_info(self):
        self.ui.name_selected_item.setText("Выберите предмет")
        self.ui.description_selected_item.clear()
        self.ui.peice_selected_item.clear()
        self.ui.effect_selected_item.clear()

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
                self.update_game_data()
                self.update_inventory()

                QMessageBox.information(
                    self.ui.centralwidget,
                    "Успех",
                    f"✅ Куплено {success_count} x {item_name}\n"
                    f"Потрачено: {item_obj.price * success_count}💰"
                )
                self.clear_item_info()


    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

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
        """Показать предупреждение о смерти"""
        if hasattr(self, '_death_warning_shown') and self._death_warning_shown:
            return

        self._death_warning_shown = True

        msg = "💀 ВАШ ПЕРСОНАЖ ПОГИБ! 💀\n\n"
        msg += "Прогресс сброшен до 1 уровня.\n"
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

