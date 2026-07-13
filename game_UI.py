"""
Модуль для связи игрового интерфейса (main_window.py) с игровой логикой (game.py, game_data.py)
"""
import datetime

from PySide6.QtCore import QDate, QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QLabel, QDialog, QApplication

import engine
import game
import game_data
from UI_fiiles.freeze_project import Ui_freeze_projrct
from UI_fiiles.bank import Ui_Bamk
from UI_fiiles.new_bank_product import Ui_Dialog as Ui_NewBankProduct
from UI_fiiles.create_custom_award import Ui_create_castom_item
from engine import load_data, save_data, today_for_test, unit_converter


class GameMenuController:
    """Класс для управления игровым меню"""
    INVENTORY_FILTER_ALL = 'Все'
    FREEZE_CATEGORY = 'Предметы'
    FREEZE_ITEM_KEY = 'Заморозка'
    FREEZE_MAX_COUNT = 2

    def __init__(self, ui, notifications = None):
        """
        Инициализация контроллера игрового меню

        Args:
            ui: Объект интерфейса (Ui_main_window)
        """
        self.ui = ui
        self.notifications = notifications
        self.gamer = None
        self._last_quest_check_at = None

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

        # Банк доступен из игрового меню.
        self.ui.bank_btn.setVisible(True)
        self.ui.bank_btn.setEnabled(True)

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

        self.setup_quests()
        self.setup_skill_controls()

        self.ui.value_for_use_selected_item.setMaximum(999)
        self.ui.value_for_buy_selected_item.setMaximum(999)
        self.ui.value_for_buy_selected_potion.setMaximum(999)
        self.ui.value_for_buy_selected_item_3.setMaximum(999)
        self.ui.value_for_buy_selected_item.setMinimum(1)

        # Очищаем информационные поля
        self.clear_all_info()

    def setup_skill_controls(self):
        for spinbox in self.get_skill_widgets().values():
            spinbox.setMinimum(0)
            spinbox.setSingleStep(1)
            spinbox.setKeyboardTracking(False)

    def setup_quests(self):
        """Включает вкладки квестов и приводит поля к начальному состоянию."""
        self.ui.quests_label.setVisible(True)
        self.ui.quests_tabs.setVisible(True)
        self.ui.quests_tabs.setEnabled(True)

        for label in (
            self.ui.name_selected_available_quest,
            self.ui.description_selected_available_quest,
            self.ui.prize_selected_available_quest,
            self.ui.name_selected_active_quest,
            self.ui.description_selected_active_quest,
            self.ui.prize_selected_active_quest,
            self.ui.date_start_selected_active_quest,
            self.ui.date_end_selected_active_quest,
            self.ui.name_selected_completed_quest,
            self.ui.description_selected_completed_quest,
            self.ui.prize_selected_completed_quest,
            self.ui.date_start_selected_completed_quest,
            self.ui.date_end_selected_completed_quest,
        ):
            label.setVisible(True)

        self.ui.button_for_start_selected_quest.setVisible(True)
        self.ui.button_for_stop_selected_quest.setVisible(True)
        self.clear_quest_info(game.Quest.AVAILABLE)
        self.clear_quest_info(game.Quest.ACTIVE)
        self.clear_quest_info(game.Quest.COMPLETED)

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
        self.ui.inventory_filter_comboBox.currentTextChanged.connect(self.on_inventory_filter_changed)

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
        delete_award_button = self.get_delete_custom_award_button()
        if delete_award_button:
            delete_award_button.clicked.connect(self.delete_selected_custom_award)

        # Очистка информации при смене выбора в магазинах
        self.ui.item_shop_list.itemClicked.connect(lambda: self.clear_potion_info())
        self.ui.item_shop_list.itemClicked.connect(lambda: self.clear_award_info())
        self.ui.potion_shop_list.itemClicked.connect(lambda: self.clear_item_info())
        self.ui.potion_shop_list.itemClicked.connect(lambda: self.clear_award_info())
        self.ui.item_shop_list_2.itemClicked.connect(lambda: self.clear_item_info())
        self.ui.item_shop_list_2.itemClicked.connect(lambda: self.clear_potion_info())

        # Банк

        self.ui.bank_btn.clicked.connect(self.bank)

        # Квесты
        self.ui.available_quests_list.itemClicked.connect(
            lambda item: self.on_quest_selected(item, game.Quest.AVAILABLE)
        )
        self.ui.active_quests_list.itemClicked.connect(
            lambda item: self.on_quest_selected(item, game.Quest.ACTIVE)
        )
        self.ui.completed_quests_list.itemClicked.connect(
            lambda item: self.on_quest_selected(item, game.Quest.COMPLETED)
        )
        self.ui.button_for_start_selected_quest.clicked.connect(self.on_start_selected_quest)
        self.ui.button_for_stop_selected_quest.clicked.connect(self.on_abandon_selected_quest)

        # Параметры персонажа
        self.ui.gamer_parameters_list.itemClicked.connect(self.on_gamer_parameter_selected)
        self.ui.gamer_parameters_list.currentItemChanged.connect(
            lambda current, previous: self.on_gamer_parameter_selected(current)
        )
        self.ui.buf_list.itemClicked.connect(lambda item: self.on_buff_selected(item, positive=True))
        self.ui.buf_list.currentItemChanged.connect(
            lambda current, previous: self.on_buff_selected(current, positive=True)
        )
        self.ui.debuf_list.itemClicked.connect(lambda item: self.on_buff_selected(item, positive=False))
        self.ui.debuf_list.currentItemChanged.connect(
            lambda current, previous: self.on_buff_selected(current, positive=False)
        )
        for skill_key, spinbox in self.get_skill_widgets().items():
            spinbox.valueChanged.connect(
                lambda value, current_skill_key=skill_key: self.on_skill_points_changed(current_skill_key, value)
            )

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
        self.load_gamer_parameters_list()
        self.update_skills_tab()
        self.update_buffs_lists()
        self.update_quests_lists()

    def update_game_data(self, force_quests=False):
        """Обновление основных параметров игрока"""
        if not self.gamer:
            return

        self.refresh_streaks_before_game_events()

        # Проверяем уровень

        level_up_msg = self.gamer.level_up()

        # Перезагружаем игрока для актуальных данных
        self.gamer = game.load_game()
        self.gamer.update_cf()
        recovery_msg = self.gamer.recover_health_by_time(save=True)
        self.register_custom_awards()
        self.process_bank_events(show_toasts=True)
        if level_up_msg and self.notifications:
            self.notifications.show_success(level_up_msg)
        if recovery_msg and self.notifications:
            self.notifications.show_info(recovery_msg)
        now = datetime.datetime.now()
        should_check_quests = (
            force_quests
            or self._last_quest_check_at is None
            or (now - self._last_quest_check_at).total_seconds() >= 5
        )
        quest_messages = []
        if should_check_quests:
            self._last_quest_check_at = now
            quest_messages = self.gamer.update_quests(save=True)
            if quest_messages:
                self.gamer = game.load_game()
                self.register_custom_awards()
                self.update_inventory()
                for message in quest_messages:
                    if self.notifications:
                        self.notifications.show_success(
                            message,
                            duration=self.get_quest_notification_duration(message)
                        )

        # Обновляем отображение
        self.ui.gamer_label.setText(str(self.gamer.level))
        self.ui.gamer_coins.setText(str(self.gamer.get_coins()))

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
        max_health = self.gamer.get_max_health()
        health = max(0, min(max_health, self.gamer.health))
        health_text = f"{health:g}" if isinstance(health, float) else str(health)
        self.ui.gamer_health.setText(f"Здоровье: {health_text}/{max_health}")
        self.ui.gamer_health_progressbar.setValue(int(health))
        self.ui.gamer_health_progressbar.setMaximum(max_health)
        self.update_gamer_parameters_list()
        self.update_skills_tab()
        self.update_buffs_lists()
        if should_check_quests or level_up_msg:
            self.update_quests_lists()

        if self.gamer.health <= 0 and engine.load_settings().get('global_streak', False):
            data = engine.load_data()
            refresh_result = engine.refresh_project_streak_statuses(data)
            global_status = engine.global_streak_status(data)
            if refresh_result.get('freeze_changed'):
                self.gamer = game.load_game()
                self.update_inventory()
                self.update_shops()
            if (
                    isinstance(global_status, str)
                    and 'Lose' not in global_status.split()
                    and self.gamer.last_lose_global_streak_damage == engine.today_for_test()
            ):
                restored = getattr(self.gamer, 'last_lose_global_streak_damage_amount', 0) or 1
                self.gamer.health = min(self.gamer.get_max_health(), max(1, self.gamer.health + restored))
                self.gamer.last_lose_global_streak_damage = None
                self.gamer.last_lose_global_streak_damage_amount = 0
                self.gamer.save()

        # Проверяем критические состояния
        if self.gamer.health <= 20 and self.gamer.health > 0:
            self.show_health_warning()
        elif self.gamer.health <= 0:
            self.show_death_warning()

    def refresh_streaks_before_game_events(self):
        """Даёт автозаморозкам сработать до урона, банка и проверки смерти."""
        if not engine.load_settings().get('global_streak', False):
            return

        data = engine.load_data()
        refresh_result = engine.refresh_project_streak_statuses(data)
        engine.global_streak_status(data)
        if refresh_result.get('freeze_changed'):
            self.gamer = game.load_game()
            self.update_inventory()
            self.update_shops()

    def process_bank_events(self, show_toasts=True):
        if not self.gamer:
            return []
        messages = self.gamer.process_bank_events(save=True)
        if show_toasts:
            for message in messages:
                self.show_bank_message(message)
        return messages

    def get_quest_notification_duration(self, message):
        return max(20000, min(45000, 12000 + len(message) * 80))

    def show_bank_message(self, message):
        if not self.notifications or not message:
            return
        lowered = message.casefold()
        if 'просроч' in lowered or 'недостаточно' in lowered:
            self.notifications.show_warning(message)
        elif 'автоплатеж' in lowered or 'погашен' in lowered or 'возвращено' in lowered:
            self.notifications.show_success(message)
        else:
            self.notifications.show_info(message)

    def get_quest_list_widget(self, status):
        if status == game.Quest.ACTIVE:
            return self.ui.active_quests_list
        if status == game.Quest.COMPLETED:
            return self.ui.completed_quests_list
        return self.ui.available_quests_list

    def get_quest_labels(self, status):
        if status == game.Quest.ACTIVE:
            return {
                'name': self.ui.name_selected_active_quest,
                'description': self.ui.description_selected_active_quest,
                'reward': self.ui.prize_selected_active_quest,
                'start': self.ui.date_start_selected_active_quest,
                'end': self.ui.date_end_selected_active_quest,
            }
        if status == game.Quest.COMPLETED:
            return {
                'name': self.ui.name_selected_completed_quest,
                'description': self.ui.description_selected_completed_quest,
                'reward': self.ui.prize_selected_completed_quest,
                'start': self.ui.date_start_selected_completed_quest,
                'end': self.ui.date_end_selected_completed_quest,
            }
        return {
            'name': self.ui.name_selected_available_quest,
            'description': self.ui.description_selected_available_quest,
            'reward': self.ui.prize_selected_available_quest,
        }

    def format_quest_date(self, value):
        if not value:
            return 'Дата не указана'
        return value.strftime('%d.%m.%Y %H:%M')

    def clear_quest_info(self, status):
        labels = self.get_quest_labels(status)
        labels['name'].setText('Выберите квест')
        labels['description'].clear()
        labels['reward'].clear()
        if 'start' in labels:
            labels['start'].clear()
        if 'end' in labels:
            labels['end'].clear()

    def get_quest_list_snapshot(self, list_widget):
        return [
            (list_widget.item(row).data(1), list_widget.item(row).text())
            for row in range(list_widget.count())
        ]

    def update_quests_list(self, status, quests=None):
        list_widget = self.get_quest_list_widget(status)
        current_item = list_widget.currentItem()
        current_quest_id = current_item.data(1) if current_item else None
        scroll_bar = list_widget.verticalScrollBar()
        scroll_value = scroll_bar.value()

        quests = quests if quests is not None else (self.gamer.get_quests_by_status(status) if self.gamer else [])
        next_snapshot = [(quest.quest_id, quest.name) for quest in quests]
        if self.get_quest_list_snapshot(list_widget) == next_snapshot:
            return

        list_widget.blockSignals(True)
        list_widget.clear()
        for quest in quests:
            item = QListWidgetItem(quest.name)
            item.setData(1, quest.quest_id)
            list_widget.addItem(item)
        list_widget.blockSignals(False)

        scroll_bar.setValue(min(scroll_value, scroll_bar.maximum()))

        if current_quest_id:
            for row in range(list_widget.count()):
                item = list_widget.item(row)
                if item.data(1) == current_quest_id:
                    list_widget.setCurrentRow(row)
                    self.on_quest_selected(item, status)
                    return

        self.clear_quest_info(status)

    def update_quests_lists(self):
        if not self.gamer:
            self.clear_quest_info(game.Quest.AVAILABLE)
            self.clear_quest_info(game.Quest.ACTIVE)
            self.clear_quest_info(game.Quest.COMPLETED)
            return

        self.gamer.sync_quests()
        for status in (game.Quest.AVAILABLE, game.Quest.ACTIVE, game.Quest.COMPLETED):
            quests = [
                quest for quest in self.gamer.quests
                if quest.status == status and self.gamer.level >= quest.level
            ]
            self.update_quests_list(status, quests)

    def on_quest_selected(self, item, status):
        if not item or not self.gamer:
            self.clear_quest_info(status)
            return

        quest = self.gamer.get_quest(item.data(1))
        if not quest:
            self.clear_quest_info(status)
            return

        labels = self.get_quest_labels(status)
        labels['name'].setText(quest.name)
        labels['description'].setText(f'{quest.description}\n\nУровень: {quest.level}')
        labels['reward'].setText(quest.format_reward())
        if 'start' in labels:
            labels['start'].setText(f'Дата начала: {self.format_quest_date(quest.start_date)}')
        if 'end' in labels:
            labels['end'].setText(f'Дата завершения: {self.format_quest_date(quest.end_date)}')

    def on_start_selected_quest(self):
        selected = self.ui.available_quests_list.currentItem()
        if not selected:
            QMessageBox.warning(self.ui.centralwidget, 'Ошибка', 'Выберите квест')
            return

        ok, message = self.gamer.start_quest(selected.data(1))
        self.gamer = game.load_game()
        self.update_game_data()
        self.update_quests_lists()

        if ok:
            if self.notifications:
                self.notifications.show_success(message)
        else:
            QMessageBox.warning(self.ui.centralwidget, 'Ошибка', message)

    def on_abandon_selected_quest(self):
        selected = self.ui.active_quests_list.currentItem()
        if not selected:
            QMessageBox.warning(self.ui.centralwidget, 'Ошибка', 'Выберите активный квест')
            return

        ok, message = self.gamer.abandon_quest(selected.data(1))
        self.gamer = game.load_game()
        self.update_game_data()
        self.update_quests_lists()

        if ok:
            if self.notifications:
                self.notifications.show_info(message)
        else:
            QMessageBox.warning(self.ui.centralwidget, 'Ошибка', message)

    def format_gamer_parameter_value(self, value):
        """Форматирует числовой коэффициент для списка параметров."""
        return f"{value:g}"

    def get_skill_widgets(self):
        return {
            'productivity': self.ui.productivity_skill_points,
            'profitability': self.ui.skill_points_profitability,
            'endurance': self.ui.endurance_skill_points,
        }

    def update_skills_tab(self):
        if not self.gamer:
            return

        self.gamer.normalize_skills()
        available_points = self.gamer.available_skill_points
        self.ui.available_skill_points.setText(f'Доступные баллы умений: {available_points}')

        for skill_key, spinbox in self.get_skill_widgets().items():
            skill_value = self.gamer.skills.get(skill_key, 0)
            with QSignalBlocker(spinbox):
                spinbox.setMinimum(skill_value)
                spinbox.setMaximum(skill_value + available_points)
                spinbox.setValue(skill_value)

        self.ui.skill_description_productivity.setText(
            f'Влияет на количество получаемого опыта. +{game.SKILL_CF_STEP:g} к коэффициенту опыта за балл.'
        )
        self.ui.skill_description_profitability.setText(
            f'Влияет на количество получаемых монет. +{game.SKILL_CF_STEP:g} к коэффициенту монет за балл.'
        )
        self.ui.endurance_skill_description.setText(
            f'Влияет на восстановление здоровья. +{game.SKILL_CF_STEP:g} здоровья в час за балл.'
        )

    def on_skill_points_changed(self, skill_key, new_value):
        if not self.gamer:
            return

        self.gamer.normalize_skills()
        current_value = self.gamer.skills.get(skill_key, 0)
        points_to_add = new_value - current_value
        if points_to_add <= 0:
            self.update_skills_tab()
            return

        ok, message = self.gamer.increase_skill(skill_key, points_to_add, save=True)
        self.gamer = game.load_game()
        self.update_skills_tab()
        self.update_gamer_parameters_list()

        if ok:
            if self.notifications:
                self.notifications.show_success(message)
        else:
            if self.notifications:
                self.notifications.show_warning(message)
            else:
                QMessageBox.warning(self.ui.centralwidget, 'Умения', message)

    def load_gamer_parameters_list(self):
        """Загружает список параметров персонажа."""
        self.ui.gamer_parameters_list.clear()

        if not self.gamer:
            self.ui.description_selected_parameter.clear()
            return

        for parameter in self.gamer.get_cf_parameters():
            value = self.format_gamer_parameter_value(parameter['value'])
            item = QListWidgetItem(f"{parameter['name']} - х{value}")
            item.setData(1, parameter['key'])
            self.ui.gamer_parameters_list.addItem(item)

        if self.ui.gamer_parameters_list.count() > 0:
            self.ui.gamer_parameters_list.setCurrentRow(0)
            self.on_gamer_parameter_selected(self.ui.gamer_parameters_list.currentItem())
        else:
            self.ui.description_selected_parameter.clear()

    def update_gamer_parameters_list(self):
        """Обновляет список параметров персонажа, сохраняя текущий выбор."""
        current_item = self.ui.gamer_parameters_list.currentItem()
        current_key = current_item.data(1) if current_item else None

        self.load_gamer_parameters_list()

        if current_key is None:
            return

        for row in range(self.ui.gamer_parameters_list.count()):
            item = self.ui.gamer_parameters_list.item(row)
            if item.data(1) == current_key:
                self.ui.gamer_parameters_list.setCurrentRow(row)
                self.on_gamer_parameter_selected(item)
                return

    def on_gamer_parameter_selected(self, item):
        """Показывает описание выбранного параметра персонажа."""
        if not item or not self.gamer:
            self.ui.description_selected_parameter.clear()
            return

        parameter_key = item.data(1)
        for parameter in self.gamer.get_cf_parameters():
            if parameter['key'] == parameter_key:
                self.ui.description_selected_parameter.setText(parameter['description'])
                return

        self.ui.description_selected_parameter.clear()

    def format_buff_remaining_time(self, buff):
        remaining = buff.remaining_time()
        if remaining is None:
            return "Бессрочно"

        total_minutes = max(0, int(remaining.total_seconds() // 60))
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60

        parts = []
        if days:
            parts.append(f"{days} д.")
        if hours:
            parts.append(f"{hours} ч.")
        parts.append(f"{minutes} мин.")
        return " ".join(parts)

    def format_buff_datetime(self, value):
        if value is None:
            return "Бессрочно"
        return value.strftime("%d.%m.%Y %H:%M")

    def get_cf_display_name(self, cf_key):
        if self.gamer:
            self.gamer.normalize_cf()
            parameter = self.gamer.cf.get(cf_key)
            if isinstance(parameter, dict):
                return parameter.get('name', cf_key)

        return game.CF_META.get(cf_key, {}).get('name', cf_key)

    def get_buff_display_text(self, buff, stacks=1):
        stack_text = f" x{stacks}" if stacks > 1 else ""
        name = f"{buff.name}{stack_text}"
        if buff.end_time is None:
            return name
        return f"{name} - {self.format_buff_remaining_time(buff)}"

    def load_buffs_list(self, positive=True):
        list_widget = self.ui.buf_list if positive else self.ui.debuf_list
        list_widget.clear()

        if not self.gamer:
            self.clear_buff_info(positive)
            return

        for buff, stacks in self.gamer.get_all_buffs(positive=positive):
            item = QListWidgetItem(self.get_buff_display_text(buff, stacks))
            item.setData(Qt.ItemDataRole.UserRole, buff)
            item.setData(Qt.ItemDataRole.UserRole + 1, stacks)
            list_widget.addItem(item)

    def update_buffs_list(self, positive=True):
        list_widget = self.ui.buf_list if positive else self.ui.debuf_list
        current_item = list_widget.currentItem()
        current_buff = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
        current_name = current_buff.name if current_buff else None

        self.load_buffs_list(positive)

        if current_name is None:
            self.clear_buff_info(positive)
            return

        for row in range(list_widget.count()):
            item = list_widget.item(row)
            buff = item.data(Qt.ItemDataRole.UserRole)
            if buff and buff.name == current_name:
                list_widget.setCurrentRow(row)
                self.on_buff_selected(item, positive)
                return

        self.clear_buff_info(positive)

    def update_buffs_lists(self):
        if not self.gamer:
            self.clear_buff_info(True)
            self.clear_buff_info(False)
            return

        self.update_buffs_list(True)
        self.update_buffs_list(False)

    def clear_buff_info(self, positive=True):
        labels = (
            [self.ui.label_40, self.ui.label_39, self.ui.label_38, self.ui.label_41, self.ui.label_37]
            if positive else
            [self.ui.label_45, self.ui.label_44, self.ui.label_43, self.ui.label_46, self.ui.label_42]
        )
        for label in labels:
            label.clear()

    def on_buff_selected(self, item, positive=True):
        if not item:
            self.clear_buff_info(positive)
            return

        buff = item.data(Qt.ItemDataRole.UserRole)
        stacks = item.data(Qt.ItemDataRole.UserRole + 1) or 1
        if not buff:
            self.clear_buff_info(positive)
            return

        labels = (
            [self.ui.label_40, self.ui.label_39, self.ui.label_38, self.ui.label_41, self.ui.label_37]
            if positive else
            [self.ui.label_45, self.ui.label_44, self.ui.label_43, self.ui.label_46, self.ui.label_42]
        )
        sign = "+" if buff.is_positive() else "-"
        stack_text = f"\nКоличество: {stacks}" if stacks > 1 else ""
        total_text = f"\nИтого: {sign}{abs(buff.value * stacks):g}" if stacks > 1 else ""
        parameter_name = self.get_cf_display_name(buff.target_cf)

        labels[0].setText(buff.name)
        labels[1].setText(buff.description)
        labels[2].setText(
            f"Параметр: {parameter_name}\n"
            f"Значение за награду: {sign}{abs(buff.value):g}"
            f"{stack_text}{total_text}"
        )
        labels[3].clear()
        if buff.end_time is None:
            labels[4].clear()
        else:
            labels[4].setText(f"Осталось: {self.format_buff_remaining_time(buff)}")

    def describe_item_buff(self, item_obj):
        buff = getattr(item_obj, 'buff', None)
        if not buff:
            return ""

        sign = "+" if buff.is_positive() else "-"
        duration = "бессрочно" if buff.duration_minutes is None else f"{buff.duration_minutes} мин."
        parameter_name = self.get_cf_display_name(buff.target_cf)
        return f"\nЭффект: {buff.name} ({parameter_name} {sign}{abs(buff.value):g}, {duration})"

    def update_inventory(self):
        """Обновление списка инвентаря"""
        self.ui.inventory_list.clear()

        if not self.gamer:
            return

        self.register_custom_awards()
        self.update_inventory_filter_combo()
        selected_filter = self.get_selected_inventory_filter()

        # Инвентарь: {категория: {предмет: количество}}
        for category, items in self.gamer.items.items():
            for item_name, count in items.items():
                if count > 0:
                    _, item_obj = game_data.find_registry_item(category, item_name)
                    item_type = self.get_inventory_item_type(category, item_obj)
                    if selected_filter != self.INVENTORY_FILTER_ALL and item_type != selected_filter:
                        continue
                    display_name = getattr(item_obj, 'name', item_name)
                    display_text = f"{display_name} x{count} [{category}]"
                    item = QListWidgetItem(display_text)
                    # Сохраняем данные предмета (категория, имя)
                    item.setData(1, (category, item_name))
                    self.ui.inventory_list.addItem(item)

        for award in self.gamer.custom_awards:
            count = self.get_custom_award_count(award)
            if count > 0:
                item_type = self.get_inventory_item_type('Награды', award)
                if selected_filter != self.INVENTORY_FILTER_ALL and item_type != selected_filter:
                    continue
                display_text = f"{award.name} x{count} [Награды]"
                item = QListWidgetItem(display_text)
                item.setData(1, ('Кастомные награды', award.name))
                self.ui.inventory_list.addItem(item)

    def get_inventory_item_type(self, category, item_obj=None):
        """Возвращает тип предмета для фильтрации инвентаря."""
        return getattr(item_obj, 'item_type', None) or category

    def get_inventory_item_types(self):
        """Собирает типы предметов, которые реально есть в инвентаре."""
        item_types = set()
        if not self.gamer:
            return item_types

        for category, items in self.gamer.items.items():
            if not isinstance(items, dict):
                continue
            for item_name, count in items.items():
                if count <= 0:
                    continue
                _, item_obj = game_data.find_registry_item(category, item_name)
                item_types.add(self.get_inventory_item_type(category, item_obj))

        for award in getattr(self.gamer, 'custom_awards', []):
            if self.get_custom_award_count(award) > 0:
                item_types.add(self.get_inventory_item_type('Награды', award))

        item_types.discard(None)
        return item_types

    def get_selected_inventory_filter(self):
        selected_filter = self.ui.inventory_filter_comboBox.currentText()
        return selected_filter or self.INVENTORY_FILTER_ALL

    def update_inventory_filter_combo(self):
        """Наполняет фильтр типами предметов из текущего инвентаря."""
        current_filter = self.get_selected_inventory_filter()
        if current_filter == self.INVENTORY_FILTER_ALL:
            current_filter = engine.load_settings().get('inventory_filter', self.INVENTORY_FILTER_ALL)

        available_filters = [self.INVENTORY_FILTER_ALL, *sorted(self.get_inventory_item_types())]
        if current_filter not in available_filters:
            current_filter = self.INVENTORY_FILTER_ALL

        combo = self.ui.inventory_filter_comboBox
        current_items = [combo.itemText(index) for index in range(combo.count())]
        if current_items == available_filters and combo.currentText() == current_filter:
            return

        with QSignalBlocker(combo):
            combo.clear()
            combo.addItems(available_filters)
            combo.setCurrentText(current_filter)

    def on_inventory_filter_changed(self, selected_filter):
        """Применяет фильтр инвентаря и сохраняет его для игрового режима."""
        if engine.load_settings().get('game_mode', False):
            settings = engine.load_settings()
            settings['inventory_filter'] = selected_filter or self.INVENTORY_FILTER_ALL
            engine.save_settings(settings)

        self.clear_inventory_item_info()
        self.update_inventory()

    def update_shops(self):
        """Обновление магазинов"""
        self.register_custom_awards()

        # Магазин предметов
        self.ui.item_shop_list.clear()
        if 'Предметы' in game_data.ITEM_REGISTRY:
            for item_name, item_obj in game_data.ITEM_REGISTRY['Предметы'].items():
                if game.load_game().level >= item_obj.level:
                    display_text = f"{item_obj.name}"
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
                    display_text = f"{potion_obj.name}"
                    item = QListWidgetItem(display_text)
                    item.setData(1, ('Зелья', potion_name))
                    self.ui.potion_shop_list.addItem(item)
                else:
                    continue

        # Магазин кастомных наград
        self.ui.item_shop_list_2.clear()
        for award in self.gamer.custom_awards:
            if not self.is_custom_award_in_shop(award):
                continue
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
        registry_key, item_obj = game_data.find_registry_item(category, item_name)
        if item_obj:

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
            count = self.get_inventory_item_count(category, item_obj, registry_key, item_name)
            self.ui.effect_selected_item.setText(
                f"⚡ {effect_text}{self.describe_item_buff(item_obj)}\n🔢 В наличии: {count}"
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

        registry_key, item_obj = game_data.find_registry_item(category, item_name)
        if not item_obj:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Предмет не найден")
            return

        # Проверяем наличие
        available = self.get_inventory_item_count(category, item_obj, registry_key, item_name)
        if count > available:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"У вас только {available} шт."
            )
            return

        # Особый случай: Заморозка (используется один раз за вызов)
        if registry_key == 'Заморозка':
            self.freeze_project(item_obj=item_obj, fallback_names=(item_name, registry_key))
            return

        # Проверяем наличие метода use
        if not hasattr(item_obj, 'use'):
            QMessageBox.information(
                self.ui.centralwidget,
                "Информация",
                f"{item_obj.name} нельзя использовать"
            )
            return

        self.ensure_inventory_item_name(category, item_obj, registry_key, item_name)

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
            self.decrease_inventory_item(category, item_obj, success_count, registry_key, item_name)
            # Сохраняем обновлённый инвентарь
            self.gamer.save()

            # Обновляем интерфейс
            self.update_inventory()
            self.update_game_data(force_quests=True)

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
        _, item_obj = game_data.find_registry_item(category, item_name)
        if not item_obj:
            return

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
        effect_label.setText(f"⚡ {effect_text}{self.describe_item_buff(item_obj)}")
        self.update_shop_purchase_controls(category, item_name, item_obj, is_potion=is_potion)

    def clear_item_info(self):
        """Очистка информации о предметах в магазине"""
        self.ui.name_selected_item_on_shop.setText('Выберите товар')
        self.ui.description_selected_item_on_shop.clear()
        self.ui.peice_selected_item_on_shop.clear()
        self.ui.effect_selected_item_on_shop.clear()
        self.ui.button_for_buy_selected_item.setEnabled(True)
        self.ui.value_for_buy_selected_item.setMaximum(999)
        self.ui.value_for_buy_selected_item.setValue(1)

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

    def delete_selected_custom_award(self):
        """Убирает выбранную кастомную награду из магазина."""
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
        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Удаление награды",
            f"Убрать награду «{item_name}» из магазина?\n"
            "Купленные экземпляры останутся в инвентаре.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        self.gamer = game.load_game()
        self.register_custom_awards()
        award = self.get_custom_award(old_name)
        if not award:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Награда не найдена")
            return

        award.available_in_shop = False
        self.cleanup_removed_custom_awards()
        self.gamer.save()
        self.gamer = game.load_game()
        self.register_custom_awards()
        self.update_shops()
        self.update_inventory()
        self.clear_award_info()
        self.notifications.show_success('Награда удалена из магазина')

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

        _, item_obj = game_data.find_registry_item(category, item_name)
        if item_obj:
            limit_message = self.validate_registry_purchase_limit(category, item_name, item_obj, count)
            if limit_message:
                QMessageBox.warning(self.ui.centralwidget, "Ошибка", limit_message)
                self.update_shop_purchase_controls(category, item_name, item_obj, expected_category == "Зелья")
                return

            item_display_name = item_obj.name
            total_price = item_obj.price * count

            # Проверяем достаточно ли монет
            if self.gamer.get_coins() < total_price:
                if not getattr(item_obj, 'credit_allowed', True):
                    QMessageBox.warning(
                        self.ui.centralwidget,
                        "Ошибка",
                        f"Недостаточно монет!\n"
                        f"Нужно: {total_price}💰\n"
                        f"У вас: {self.gamer.get_coins()}💰\n\n"
                        f"Этот предмет нельзя купить в кредит."
                    )
                    return
                if not self.offer_purchase_credit(total_price, f"{count} x {item_display_name}"):
                    return
                skip_confirmation = True
            else:
                skip_confirmation = False

            if not skip_confirmation:
                reply = QMessageBox.question(
                    self.ui.centralwidget,
                    "Подтверждение покупки",
                    f"Купить {count} x {item_display_name} за {total_price}💰?",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.No:
                    return

            # Покупаем предметы
            success_count = self.purchase_registry_item(item_obj, count, total_price)

            if success_count > 0:
                self.gamer = game.load_game()
                self.register_custom_awards()
                self.update_game_data()
                self.update_inventory()

                QMessageBox.information(
                    self.ui.centralwidget,
                    "Успех",
                    f"✅ Куплено {success_count} x {item_display_name}\n"
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

        if self.gamer.get_coins() < total_price:
            if not self.offer_purchase_credit(total_price, f"{count} x {item_name}"):
                return
            skip_confirmation = True
        else:
            skip_confirmation = False

        if not skip_confirmation:
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

    def offer_purchase_credit(self, total_price, purchase_name):
        """Предлагает кредит на недостающую сумму и оформляет его перед покупкой."""
        self.gamer = game.load_game()
        self.register_custom_awards()
        account = self.gamer.bank_account
        account.normalize()
        deficit = self.gamer.round_money(total_price - self.gamer.get_coins())

        if deficit <= 0:
            return True

        message = f"Недостаточно монет!\nНужно: {total_price}💰\nУ вас: {self.gamer.get_coins()}💰"

        can_offer_credit = (
            self.gamer.level >= 3
            and not account.credit
            and account.get_credit_limit(self.gamer) >= deficit
        )
        if not can_offer_credit:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", message)
            return False

        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Недостаточно монет",
            f"{message}\n\nВзять кредит минимум на {deficit}💰 для покупки «{purchase_name}»?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return False

        dialog = NewBankProduct(self.gamer, 'credit', min_amount=deficit, initial_amount=deficit)
        if dialog.exec_() != QDialog.Accepted:
            return False

        ok, credit_message = account.open_credit(self.gamer, dialog.get_amount(), dialog.get_days())
        if not ok:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", credit_message)
            return False

        self.gamer = game.load_game()
        self.register_custom_awards()
        if self.notifications:
            self.notifications.show_success(credit_message)

        if self.gamer.get_coins() < total_price:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"После оформления кредита всё ещё не хватает монет.\nНужно: {total_price}💰\nУ вас: {self.gamer.get_coins()}💰"
            )
            return False
        return True

    def purchase_registry_item(self, item_obj, count, total_price):
        self.gamer = game.load_game()
        self.register_custom_awards()
        registry_key, _ = game_data.find_registry_item(item_obj.item_type, item_obj.name)
        limit_message = self.validate_registry_purchase_limit(item_obj.item_type, registry_key, item_obj, count)
        if limit_message:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", limit_message)
            return 0

        if self.gamer.get_coins() < total_price:
            credit_text = ''
            if not getattr(item_obj, 'credit_allowed', True):
                credit_text = '\nЭтот предмет нельзя купить в кредит.'
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"Покупка остановлена: недостаточно монет.\n"
                f"Нужно: {total_price}💰\n"
                f"У вас: {self.gamer.get_coins()}💰"
                f"{credit_text}"
            )
            return 0

        self.gamer.remove_coins(total_price)
        items = self.gamer.get_items()
        if item_obj.item_type not in items:
            items[item_obj.item_type] = {}
        if item_obj.name not in items[item_obj.item_type]:
            items[item_obj.item_type][item_obj.name] = 0
        items[item_obj.item_type][item_obj.name] += count
        self.gamer.set_items(items)
        self.gamer.save()
        return count

    def is_freeze_shop_item(self, category, item_name=None, item_obj=None):
        if category != self.FREEZE_CATEGORY:
            return False

        registry_key = None
        if item_name:
            registry_key, _ = game_data.find_registry_item(category, item_name)
        elif item_obj is not None:
            registry_key, _ = game_data.find_registry_item(category, getattr(item_obj, 'name', None))
        return registry_key == self.FREEZE_ITEM_KEY

    def get_freeze_inventory_count(self):
        self.gamer = game.load_game()
        _, freeze_item = game_data.find_registry_item(self.FREEZE_CATEGORY, self.FREEZE_ITEM_KEY)
        return self.get_inventory_item_count(self.FREEZE_CATEGORY, freeze_item, self.FREEZE_ITEM_KEY)

    def get_freeze_purchase_remaining(self):
        return max(0, self.FREEZE_MAX_COUNT - self.get_freeze_inventory_count())

    def validate_registry_purchase_limit(self, category, item_name, item_obj, count):
        if not self.is_freeze_shop_item(category, item_name, item_obj):
            return None

        current_count = self.get_freeze_inventory_count()
        if current_count >= self.FREEZE_MAX_COUNT:
            return 'В инвентаре уже 2 заморозки. Больше купить нельзя.'

        if current_count + count > self.FREEZE_MAX_COUNT:
            remaining = self.FREEZE_MAX_COUNT - current_count
            return f'Можно иметь не больше 2 заморозок. Сейчас доступно к покупке: {remaining}.'

        return None

    def update_shop_purchase_controls(self, category, item_name, item_obj, is_potion=False):
        if is_potion:
            spinbox = self.ui.value_for_buy_selected_potion
            button = self.ui.button_for_buy_selected_potion
        else:
            spinbox = self.ui.value_for_buy_selected_item
            button = self.ui.button_for_buy_selected_item

        button.setEnabled(True)
        spinbox.setMaximum(999)
        if spinbox.value() < 1:
            spinbox.setValue(1)

        if is_potion or not self.is_freeze_shop_item(category, item_name, item_obj):
            return

        remaining = self.get_freeze_purchase_remaining()
        if remaining <= 0:
            spinbox.setMaximum(1)
            spinbox.setValue(1)
            button.setEnabled(False)
            self.ui.effect_selected_item_on_shop.setText(
                f'{self.ui.effect_selected_item_on_shop.text()}\nВ инвентаре уже 2 заморозки.'
            )
            return

        spinbox.setMaximum(remaining)
        if spinbox.value() > remaining:
            spinbox.setValue(remaining)

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
        if available - count <= 0 and not self.is_custom_award_in_shop(award):
            self.cleanup_removed_custom_awards()
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

    def get_inventory_item_aliases(self, item_obj, *fallback_names):
        aliases = []
        for name in (getattr(item_obj, 'name', None), *fallback_names):
            if name and name not in aliases:
                aliases.append(name)
        return aliases

    def get_inventory_item_count(self, category, item_obj, *fallback_names):
        category_items = self.gamer.items.get(category, {})
        if not isinstance(category_items, dict):
            return 0

        return sum(
            category_items.get(name, 0)
            for name in self.get_inventory_item_aliases(item_obj, *fallback_names)
        )

    def decrease_inventory_item(self, category, item_obj, count, *fallback_names):
        category_items = self.gamer.items.setdefault(category, {})
        remaining = count

        for name in self.get_inventory_item_aliases(item_obj, *fallback_names):
            if remaining <= 0:
                break
            available = category_items.get(name, 0)
            if available <= 0:
                continue

            used = min(available, remaining)
            category_items[name] = available - used
            remaining -= used

        return count - remaining

    def ensure_inventory_item_name(self, category, item_obj, *fallback_names):
        category_items = self.gamer.items.setdefault(category, {})
        item_name = getattr(item_obj, 'name', None)
        if not item_name:
            return

        for fallback_name in fallback_names:
            if fallback_name == item_name:
                continue
            fallback_count = category_items.pop(fallback_name, 0)
            if fallback_count > 0:
                category_items[item_name] = category_items.get(item_name, 0) + fallback_count
                self.gamer.save()

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
            if not hasattr(award, 'available_in_shop'):
                award.available_in_shop = True
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

    def get_delete_custom_award_button(self):
        """Возвращает кнопку удаления награды, если она есть в UI."""
        return getattr(self.ui, 'button_for_delete_selected_custom_award', None)

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

    def is_custom_award_in_shop(self, award):
        """Проверяет, должна ли кастомная награда показываться в магазине."""
        return getattr(award, 'available_in_shop', True)

    def cleanup_removed_custom_awards(self):
        """Удаляет скрытые из магазина награды, если их больше нет в инвентаре."""
        if not hasattr(self.gamer, 'custom_awards_inventory') or self.gamer.custom_awards_inventory is None:
            self.gamer.custom_awards_inventory = {}

        remaining_awards = []
        for award in self.gamer.custom_awards:
            count = self.gamer.custom_awards_inventory.get(award.name, 0)
            if self.is_custom_award_in_shop(award) or count > 0:
                remaining_awards.append(award)
            else:
                self.gamer.custom_awards_inventory.pop(award.name, None)
                if 'Награды' in game_data.ITEM_REGISTRY:
                    game_data.ITEM_REGISTRY['Награды'].pop(award.name, None)
        self.gamer.custom_awards = remaining_awards

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
                if 'здоровья' in str(potion_name).casefold() and self.gamer.items['Зелья'][potion_name] > 0:
                    has_health_potion = True
                    break

        msg = f"⚠️ КРИТИЧЕСКИЙ УРОВЕНЬ ЗДОРОВЬЯ! ⚠️\n\n"
        msg += f"Ваше здоровье: {self.gamer.health:g}/{self.gamer.get_max_health()}\n\n"

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
        max_health = self.gamer.get_max_health()

        if has_revival_potion:
            self.gamer.items['Зелья'][revival_name] -= 1
            self.gamer.health = max_health
            self.gamer.save()
            self._death_warning_shown = False
            self.update_inventory()
            self.update_game_data(force_quests=True)
            QMessageBox.information(
                self.ui.centralwidget,
                "Воскрешение",
                "💀 Ваше здоровье закончилось, но зелье воскрешения спасло вас!\n"
                f"Здоровье восстановлено до {max_health}, прогресс сохранён."
            )
            return

        revival_item = game_data.ITEM_REGISTRY['Зелья'][revival_name]
        revival_price = revival_item.price
        if self.gamer.get_coins() >= revival_price:
            choice = QMessageBox.question(
                self.ui.centralwidget,
                "Воскрешение",
                f"💀 Ваше здоровье закончилось!\n\n"
                f"Купить и использовать зелье воскрешения за {revival_price} монет, "
                f"чтобы избежать сброса прогресса?",
                QMessageBox.Yes | QMessageBox.No
            )
            if choice == QMessageBox.Yes:
                self.gamer.remove_coins(revival_price, process_bank_events=False, save=False)
                self.gamer.health = max_health
                self.gamer.save()
                self._death_warning_shown = False
                self.update_game_data(force_quests=True)
                QMessageBox.information(
                    self.ui.centralwidget,
                    "Воскрешение",
                    f"Вы воскрешены! Здоровье восстановлено до {max_health}, прогресс сохранён."
                )
                return

        if hasattr(self, '_death_warning_shown') and self._death_warning_shown:
            self.gamer.level = 1
            self.gamer.coins = self.gamer.round_money(self.gamer.get_coins() / 2)
            self.gamer.exp = 0
            self.gamer.items = {}
            self.gamer.update_max_health()
            self.gamer.health = self.gamer.get_max_health()
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
            self.update_game_data(force_quests=True)
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
            self.update_game_data(force_quests=True)
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
            self.update_game_data(force_quests=True)
            self.update_inventory()
            self.notifications.show_success(result)
            return True
        return

    def freeze_project(self, item_obj=None, fallback_names=()):
        dialog = FreezeProject()
        result = dialog.exec_()
        if result == QDialog.Accepted:
            msg = dialog.freeze()
            self.gamer = game.load_game()
            self.notifications.show_success(msg)
            self.update_inventory()
            self.refresh_all()
            self.notifications.show_success(result)
            return True
        dialog.close()

    def bank(self):
        dialog = Bank(self.gamer, self.notifications)
        dialog.show()
        result = dialog.exec_()
        if result in (QDialog.Accepted, QDialog.Rejected):
            self.gamer = dialog.gamer
            self.update_game_data(force_quests=True)

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
            new_award.available_in_shop = True

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

            # Получаем статус стрика
            streak_status = project.get_streak_status()

            # Проект можно заморозить если последний стрик был вчера
            # и статус 'Active' (активный, но не продленный)
            if streak_status in ['Active', 'Freeze']:
                display_text = f"{project.name} (стрик: {engine.streak_length(project.streaks)} дн.)"
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

            if not engine.apply_project_freeze(project, today):
                return 'Не удалось применить заморозку: проверьте инвентарь и статус проекта.'

            if engine.streak_last_day(data['global_streaks']) == today - datetime.timedelta(days=1):
                data['global_streaks'].append(engine.STREAK_FREEZE_MARKER)
            data['global_streak_status'] = 'Freeze'

            data['projects'][project_name] = project
            save_data(data)
            return f'Проект "{project_name}" заморожен!'

        return f'Ошибка: проект "{project_name}" не найден'

class NewBankProduct(QDialog, Ui_NewBankProduct):
    def __init__(self, gamer: game.Gamer, product_type, min_amount=None, initial_amount=None):
        super().__init__()
        self.setupUi(self)
        self.gamer = gamer
        self.product_type = product_type
        self.min_amount = min_amount
        self.account = gamer.bank_account
        self.account.normalize()

        today = engine.today_for_test()
        self.return_date_dateedit.setMinimumDate(QDate(today.year, today.month, today.day).addDays(1))
        default_days = 7
        if product_type == 'credit':
            self.max_credit_days = self.account.get_max_credit_days()
            self.return_date_dateedit.setMaximumDate(
                QDate(today.year, today.month, today.day).addDays(self.max_credit_days)
            )
            default_days = min(default_days, self.max_credit_days)
        self.return_date_dateedit.setDate(QDate(today.year, today.month, today.day).addDays(default_days))
        default_amount = initial_amount if initial_amount is not None else min_amount
        self.lineEdit.setText(str(round(default_amount, 1) if default_amount else 100))

        if product_type == 'credit':
            limit = self.account.get_credit_limit(self.gamer)
            self.setWindowTitle('Новый кредит')
            description = (
                f'Кредитный рейтинг: {self.account.calculate_credit_score(self.gamer)}\n'
                f'Лимит кредита: {limit} монет\n'
                f'Максимальный срок: {self.max_credit_days} дн.'
            )
            if self.min_amount:
                description += f'\nМинимальная сумма: {self.min_amount} монет'
            self.product_description.setText(description)
        else:
            self.setWindowTitle('Новый вклад')
            self.product_description.setText(
                f'Кредитный рейтинг: {self.account.calculate_credit_score(self.gamer)}\n'
                f'Доступно на счете: {self.gamer.get_coins()} монет'
            )

        try:
            self.buttonBox.accepted.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.buttonBox.accepted.connect(self.on_accept)
        self.lineEdit.textChanged.connect(self.update_preview)
        self.return_date_dateedit.dateChanged.connect(self.update_preview)
        self.update_preview()

    def _parse_amount(self):
        text = self.lineEdit.text().strip().replace(',', '.')
        if not text:
            raise ValueError('Введите сумму')
        amount = self.gamer.round_money(float(text))
        if amount <= 0:
            raise ValueError('Сумма должна быть больше 0')
        if self.min_amount is not None and amount < self.min_amount:
            raise ValueError(f'Сумма не может быть меньше {self.min_amount} монет')
        return amount

    def get_days(self):
        return max(1, (self.return_date_dateedit.date().toPython() - engine.today_for_test()).days)

    def validate_product(self):
        amount = self._parse_amount()
        days = self.get_days()
        if self.product_type == 'credit':
            limit = self.account.get_credit_limit(self.gamer)
            if amount > limit:
                raise ValueError(f'Сумма выше кредитного лимита: {limit} монет')
            max_days = self.account.get_max_credit_days()
            if days > max_days:
                raise ValueError(f'Максимальный срок кредита: {max_days} дн.')
        elif self.gamer.get_coins() < amount:
            raise ValueError(f'Недостаточно монет. Доступно: {self.gamer.get_coins()}')
        return amount, days

    def update_preview(self):
        try:
            amount, days = self.validate_product()
            preview = self.account.preview_product(self.gamer, self.product_type, amount, days)
            self.product_interest_rates.setText(
                f'Ставка: {preview["rate"]}% в день\n'
                f'Проценты за {days} д.: {preview["interest"]} монет'
            )
            if self.product_type == 'credit':
                self.total_amount_to_be_refunded.setText(
                    f'К возврату: {preview["total"]} монет\n'
                    f'Ежедневный платеж: {round(preview["total"] / days, 1)} монет'
                )
            else:
                self.total_amount_to_be_refunded.setText(f'К снятию в конце срока: {preview["total"]} монет')
            self.buttonBox.button(self.buttonBox.StandardButton.Ok).setEnabled(True)
        except ValueError as error:
            self.product_interest_rates.setText(str(error))
            self.total_amount_to_be_refunded.setText('')
            self.buttonBox.button(self.buttonBox.StandardButton.Ok).setEnabled(False)

    def on_accept(self):
        try:
            self.validate_product()
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка", str(error))
            return
        self.accept()

    def get_amount(self):
        return self._parse_amount()


class Bank(QDialog, Ui_Bamk):
    def __init__(self, gamer: game.Gamer, notifications=None):
        super().__init__()
        self.setupUi(self)
        self.gamer = gamer
        self.notifications = notifications
        self.account: game_data.BankAccount = self.gamer.bank_account
        self.account.normalize()

        messages = self.account.process_daily_events(self.gamer, auto_pay=True, notify=True, save=False)
        self._show_messages(messages)
        if messages:
            self.gamer.save()

        self.take_credit_btn.clicked.connect(self.take_credit)
        self.make_deposit_btn.clicked.connect(self.make_deposit)
        self.return_credit_btn.clicked.connect(self.return_credit)
        self.make_a_loan_payment.clicked.connect(self.make_loan_payment)
        self.partial_loan_repayment.clicked.connect(self.make_partial_loan_repayment)
        self.loan_partial_repayment_amount.textChanged.connect(self.update_partial_repayment_button)
        self.active_deposit_topup_amount.textChanged.connect(self.update_deposit_topup_button)
        self.active_deposit_topup_amount.returnPressed.connect(self.top_up_deposit)
        self.return_deposit_btn.clicked.connect(self.return_deposit)
        self.withdraw_interest_from_a_deposit.clicked.connect(self.withdraw_deposit_interest)

        self.refresh()

    def _show_message(self, message):
        if not message:
            return
        if self.notifications:
            self.notifications.show_success(message)
        else:
            QMessageBox.information(self, "Банк", message)

    def _show_messages(self, messages):
        for message in messages:
            self._show_message(message)

    def refresh(self):
        self.account = self.gamer.bank_account
        self.account.normalize()
        score = self.account.calculate_credit_score(self.gamer)
        credit_rate = self.account.get_credit_rate(self.gamer)
        deposit_rate = self.account.get_deposit_rate(self.gamer)
        credit_limit = self.account.get_credit_limit(self.gamer)
        income = self.account.estimate_daily_income_details(self.gamer)

        self.credit_score.setText(
            f'Кредитный рейтинг: {score}\n'
            f'Лимит: {credit_limit}'
        )
        self.label_2.setText(f'Кредит: {credit_rate}%/д.\nВклад: {deposit_rate}%/д.')
        self.label.setText(
            f'Оценочный доход: {income["total"]} м./д.\n'
            f'Письмо: {income["symbols"]}, стрики: {income["streaks"]}, надёжность: {income["reliability"]}'
        )

        today = engine.today_for_test()

        self.take_credit_btn.setVisible(True)
        self.return_credit_btn.setVisible(True)
        self.make_a_loan_payment.setVisible(True)
        self.partial_loan_repayment.setVisible(True)
        self.loan_partial_repayment_amount.setVisible(True)
        self.make_deposit_btn.setVisible(True)
        self.return_deposit_btn.setVisible(True)
        self.withdraw_interest_from_a_deposit.setVisible(True)
        self.active_deposit_topup_amount.setVisible(True)

        self.take_credit_btn.setEnabled(False)
        self.return_credit_btn.setEnabled(False)
        self.make_a_loan_payment.setEnabled(False)
        self.partial_loan_repayment.setEnabled(False)
        self.loan_partial_repayment_amount.setEnabled(False)
        self.make_deposit_btn.setEnabled(False)
        self.return_deposit_btn.setEnabled(False)
        self.withdraw_interest_from_a_deposit.setEnabled(False)
        self.active_deposit_topup_amount.setEnabled(False)

        self.credit_status.setVisible(True)
        self.return_credit_date.setVisible(False)
        self.credit_total_sum.setVisible(False)

        if self.gamer.level < 3:
            self.credit_status.setText('Кредиты доступны с 3 уровня')
        elif self.account.credit:
            credit = self.account.credit
            credit.normalize()
            self.credit_status.setText(
                f'{credit.get_status()}\n'
                f'Осталось: {credit.get_remaining_sum()} монет\n'
                f'Платеж: {credit.get_daily_payment()} монет'
            )
            self.return_credit_date.setVisible(True)
            self.return_credit_date.setText(f'До {credit.get_return_date().strftime("%d.%m.%Y")}')
            self.credit_total_sum.setVisible(True)
            self.credit_total_sum.setText(
                f'Всего по графику: {credit.get_total_sum()}\n'
                f'К погашению: {credit.get_full_repayment_sum()}'
            )
            self.return_credit_btn.setEnabled(credit.get_full_repayment_sum() <= self.gamer.get_coins())
            self.make_a_loan_payment.setEnabled(
                today >= credit.get_first_payment_date()
                and credit.last_payment_date != today
                and credit.get_daily_payment() <= self.gamer.get_coins()
            )
            self.loan_partial_repayment_amount.setEnabled(self.gamer.get_coins() > 0)
            self.update_partial_repayment_button()
        else:
            self.credit_status.setText('В банке нет кредита')
            self.take_credit_btn.setEnabled(self.gamer.level >= 3)

        self.make_deposit_btn.setText('Внести вклад')
        self.make_deposit_btn.setEnabled(not self.account.deposit and self.gamer.get_coins() > 0)
        self.return_deposit_date.setVisible(False)
        self.deposit_total_sum.setVisible(False)

        if self.account.deposit:
            deposit = self.account.deposit
            deposit.normalize()
            self.deposit_status.setText(
                f'{deposit.get_status()}\n'
                f'Вклад: {deposit.get_sum()} монет\n'
                f'Доступные проценты: {deposit.get_available_interest()}'
            )
            self.return_deposit_date.setVisible(True)
            self.return_deposit_date.setText(f'До {deposit.get_return_date().strftime("%d.%m.%Y")}')
            self.deposit_total_sum.setVisible(True)
            self.deposit_total_sum.setText(f'К снятию: {deposit.get_total_sum()}')
            self.return_deposit_btn.setEnabled(True)
            self.withdraw_interest_from_a_deposit.setEnabled(
                today > deposit.give_date
                and deposit.last_interest_withdraw_date != today
                and deposit.get_available_interest() > 0
            )
            self.make_deposit_btn.setText('Пополнить вклад')
            self.active_deposit_topup_amount.setEnabled(self.gamer.get_coins() > 0)
            self.update_deposit_topup_button()
        else:
            self.deposit_status.setText('В банке нет вклада')

    def get_partial_repayment_amount(self):
        text = self.loan_partial_repayment_amount.text().strip().replace(',', '.')
        if not text:
            return None
        try:
            amount = round(float(text), 1)
        except ValueError:
            return None
        if amount <= 0:
            return None
        return amount

    def update_partial_repayment_button(self):
        amount = self.get_partial_repayment_amount()
        self.partial_loan_repayment.setEnabled(
            bool(self.account.credit)
            and amount is not None
            and amount <= self.gamer.get_coins()
        )

    def get_deposit_topup_amount(self):
        text = self.active_deposit_topup_amount.text().strip().replace(',', '.')
        if not text:
            return None
        try:
            amount = round(float(text), 1)
        except ValueError:
            return None
        if amount <= 0:
            return None
        return amount

    def update_deposit_topup_button(self):
        amount = self.get_deposit_topup_amount()
        self.make_deposit_btn.setEnabled(
            bool(self.account.deposit)
            and amount is not None
            and amount <= self.gamer.get_coins()
        )

    def _reload_after_action(self, message):
        self._show_message(message)
        self.gamer.bank_account = self.account
        self.account = self.gamer.bank_account
        self.refresh()

    def take_credit(self):
        dialog = NewBankProduct(self.gamer, 'credit')
        if dialog.exec_() == QDialog.Accepted:
            ok, message = self.account.open_credit(self.gamer, dialog.get_amount(), dialog.get_days())
            self._reload_after_action(message)

    def make_deposit(self):
        if self.account.deposit:
            self.top_up_deposit()
            return
        dialog = NewBankProduct(self.gamer, 'deposit')
        if dialog.exec_() == QDialog.Accepted:
            ok, message = self.account.open_deposit(self.gamer, dialog.get_amount(), dialog.get_days())
            self._reload_after_action(message)

    def top_up_deposit(self):
        if not self.account.deposit:
            return
        amount = self.get_deposit_topup_amount()
        if amount is None:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму пополнения")
            return
        message = self.account.top_up_deposit(self.gamer, amount)
        self.active_deposit_topup_amount.clear()
        self._reload_after_action(message)

    def return_credit(self):
        message = self.account.return_credit(self.gamer)
        self._reload_after_action(message)

    def make_loan_payment(self):
        message = self.account.make_loan_payment(self.gamer)
        self._reload_after_action(message)

    def make_partial_loan_repayment(self):
        amount = self.get_partial_repayment_amount()
        if amount is None:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму погашения")
            return
        message = self.account.partial_repay_credit(self.gamer, amount)
        self.loan_partial_repayment_amount.clear()
        self._reload_after_action(message)

    def return_deposit(self):
        deposit = self.account.deposit
        early = False
        if deposit and deposit.get_return_date() > engine.today_for_test():
            choice = QMessageBox.question(
                self,
                "Досрочное снятие вклада",
                f"Срок вклада еще не наступил.\n\n"
                f"При досрочном снятии на счет вернется только сумма вклада: "
                f"{deposit.get_sum()} монет.\n"
                f"Проценты сгорят: {deposit.get_interest()} монет.\n\n"
                f"Снять вклад досрочно?",
                QMessageBox.Yes | QMessageBox.No
            )
            if choice != QMessageBox.Yes:
                return
            early = True

        message = self.account.return_deposit(self.gamer, early=early)
        self._reload_after_action(message)

    def withdraw_deposit_interest(self):
        message = self.account.withdraw_deposit_interest(self.gamer)
        self._reload_after_action(message)

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
