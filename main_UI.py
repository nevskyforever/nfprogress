import datetime
import os
import sys

from PySide6.QtCore import QTranslator, QLibraryInfo, QDate, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMainWindow, QDialog, QListWidgetItem

import engine as en
from UI_fiiles.confirm_dialog import Ui_confirm_dialog as confirm_dialog_ui
from UI_fiiles.create_project import Ui_create_project as create_project_ui
from UI_fiiles.main_window import Ui_main_window as main_window_ui
from UI_fiiles.notification import ToastNotification
from UI_fiiles.project_widget import ProjectWidget
from UI_fiiles.settings import Ui_Dialog as settings_ui
from UI_fiiles.user_agreement import Ui_user_agreement as user_agreement_ui

from engine import save_data, save_settings, load_settings
from game_UI import GameMenuController


class MainWindow(QMainWindow, main_window_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.unit_to_display = {
            'symbols': 'Символы',
            'A4': 'Листы А4',
            'author_list': 'Авторские листы',
            'ficbook_pages': 'Страницы Фикбука'
        }

        # для отслеживания предыдущей вкладки
        self._previous_tab = None

        # Применяем настройки
        self.applying_settings()
        self.global_streak_mode = en.load_settings().get('global_streak', False)
        self.filter_project_box.setCurrentText(en.load_settings().get('project_filter', 'Активен'))
        self.sort_project_box.setCurrentText(en.load_settings().get('project_sort', 'Прогресс'))

        # Проверяем пользовательское соглашение
        self.check_user_agreement()

        # Обновляем проекты
        self.refresh_projects()

        # Подключаем обработчик изменения фильтра
        self.filter_project_box.currentTextChanged.connect(self.on_filter_changed)
        self.sort_project_box.currentTextChanged.connect(self.on_sort_changed)

        # Подключаем обработчик переключения вкладок
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        # Создаем менеджер уведомлений
        self.notifications = NotificationManager(self)

        # Инициализация игрового контроллера
        self.game_controller = GameMenuController(self, self.notifications)

        # Правильный способ подключения кнопки
        self.project_info.setVisible(False)
        self.note_widget.setVisible(False)
        self.change_project_widget.setVisible(False)
        self.btn_create_project.clicked.connect(self.create_project)
        self.list_projects.itemClicked.connect(self.view_project)

        # Подключаем обработку Enter для поля ввода
        self.new_symbols.returnPressed.connect(self.on_enter_pressed)

        # Добавляем менюбар
        self.menu.addAction("Настройки приложения").triggered.connect(self.edit_settings)
        if self.global_streak_mode:
            self.refresh_global_streak_status()
            QTimer.singleShot(1000, self.check_global_streak)

        self.show()

    def on_enter_pressed(self):
        """Обработчик нажатия Enter в поле ввода"""
        # Получаем текущий выбранный проект
        current_item = self.list_projects.currentItem()
        if current_item is None:
            return

        # Получаем виджет проекта
        widget = self.list_projects.itemWidget(current_item)
        if widget and hasattr(widget, 'project'):
            # Получаем проект и добавляем заметку
            project = widget.project
            self.add_note(project)

    def create_project(self):
        """Создаёт новый проект."""
        dialog = CreateProject()
        result = dialog.exec()

        if result == QDialog.Accepted:
            data = en.load_data()

            name = dialog.get_name()
            goal = dialog.get_goal()
            total = dialog.get_total()
            unit = dialog.get_unit()
            deadline = dialog.get_deadline()

            # Проверяем, что проект с таким именем не существует
            if name in data['projects']:
                self.notifications.show_error(f'Проект "{name}" уже существует!')
                return

            new_project = en.Project(
                name=name,
                goal=goal,
                deadline=deadline,
                total_symbols=total,
                unit=unit
            )

            # Если это бесконечный проект (inf_project), устанавливаем goal = inf
            if en.load_settings().get('inf_project', False) and name == 'Общий проект':
                new_project.goal = float('inf')

            data['projects'][new_project.name] = new_project
            en.save_data(data)

            self.refresh_projects()

            # Выделяем созданный проект
            self.select_project_by_name(new_project.name)

            unit_name = self._get_unit_name(unit)
            self.notifications.show_success(
                f"Проект '{name}' создан! (Цель: {goal} {unit_name})",
                2000,
                "bottom-left"
            )

    def applying_settings(self):
        settings = en.load_settings()

        # 1. СНАЧАЛА находим индекс игровой вкладки (если она есть)
        game_tab_index = -1
        for i in range(self.tabWidget.count()):
            if self.tabWidget.tabText(i) == 'Игровой режим':
                game_tab_index = i
                break

        # 2. Обработка игрового режима
        if not settings['game_mode']:
            # Режим выключен
            if game_tab_index >= 0:
                # Сохраняем виджет ПЕРЕД удалением
                self.game_tab_widget = self.tabWidget.widget(game_tab_index)
                self.tabWidget.removeTab(game_tab_index)
        else:
            # Режим включен
            if game_tab_index < 0:
                # Вкладки нет - добавляем
                if hasattr(self, 'game_tab_widget') and self.game_tab_widget:
                    # Используем сохранённый виджет
                    self.tabWidget.addTab(self.game_tab_widget, 'Игровой режим')
                else:
                    # Создаём новую вкладку (используем существующую из UI)
                    self.tabWidget.addTab(self.game_tab, 'Игровой режим')

        if settings['inf_project'] is True:
            data = en.load_data()
            inf_project = en.Project(name='Общий проект', goal=float('inf'), total_symbols=0)
            data['projects']['inf_project'] = inf_project
            save_data(data)
            self.refresh_projects()
        else:
            data = en.load_data()
            if data['projects'].get('inf_project'):
                del data['projects']['inf_project']
                save_data(data)
                self.refresh_projects()
        if settings.get('global_streak', False):
            self.global_streak_status.setVisible(True)
            self.refresh_projects()
            self.view_project()
        else:
            self.global_streak_status.setVisible(False)
            self.refresh_projects()
            self.view_project()

    def edit_settings(self):
        dialog = Settings()
        result = dialog.exec()
        if result == QDialog.Accepted:
                inf_project = dialog.enable_inf_projects_checkBox.isChecked()
                game_mode = dialog.enable_game_mode_checkBox.isChecked()
                global_streak = dialog.enable_global_streak_checkBox.isChecked()
                settings = en.load_settings()
                settings['inf_project'] = inf_project
                settings['game_mode'] = game_mode
                settings['global_streak'] = global_streak
                en.save_settings(settings)
        self.applying_settings()

    def view_project(self):
        """Отображает информацию о выбранном проекте"""
        # Получаем текущий выбранный элемент
        current_item = self.list_projects.currentItem()

        if current_item is None:
            # Если ничего не выбрано, скрываем панели
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.name_selected_project.setText("Выберите проект")
            return

        # Получаем виджет, связанный с выбранным элементом
        widget = self.list_projects.itemWidget(current_item)

        if widget is None or not hasattr(widget, 'project'):
            self.project_info.setVisible(False)
            return

        # Получаем проект из виджета
        project = widget.project

        # Отображаем информацию о проекте
        self.show_project_info(project)

        # Настраиваем кнопки управления
        self.setup_project_buttons(project)

        # Показываем панели
        self.project_info.setVisible(True)
        self.note_widget.setVisible(True)
        self.change_project_widget.setVisible(True)
        self.name_selected_project.setText(project.name)

    def show_project_info(self, project):
        """Заполняет виджеты информацией о проекте."""
        units_for_view = {
            'symbols': 'Символы',
            'A4': 'Листы А4',
            'author_list': 'Авторские листы',
            'ficbook_pages': 'Страницы Фикбука'
        }

        # Основная информация
        self.status.setText(project.status)
        self.progress.setText(f"{project.progress:.1f}%")
        self.goal.setText(self._format_number(project.goal))
        self.total.setText(self._format_number(project.total_symbols))
        self.unit.setText(units_for_view[project.unit])

        # Статистика за сегодня (в единице проекта)
        added_today = project.get_added_today_in_unit()
        self.added_today.setText(self._format_number(added_today))

        # Осталось написать (в единице проекта)
        need = project.get_need_write_in_unit()
        if need == float('inf'):
            self.need.setText('∞')
        else:
            self.need.setText(self._format_number(need))

        # Дедлайн
        if project.deadline != 'Нет':
            self.deadline.setText(project.deadline_str)
            self.label_today_goal.setVisible(True)
            self.today_goal.setVisible(True)

            # Цель на сегодня (в единице проекта)
            today_goal = project.get_today_goal_in_unit()
            if today_goal == float('inf'):
                self.today_goal.setText('∞')
            else:
                if added_today < today_goal:
                    self.today_goal.setText(self._format_number(today_goal))
                else:
                    self.today_goal.setText('Цель на сегодня выполнена!')

            # Расчёт оставшихся дней
            days_left = (project.deadline - en.today_for_test()).days
            if days_left > 0:
                self.deadline.setText(f"{project.deadline_str} (осталось {days_left} дн.)")
            elif days_left == 0:
                self.deadline.setText(f"{project.deadline_str} (сегодня!)")
            else:
                self.deadline.setText(f"{project.deadline_str} (просрочено на {abs(days_left)} дн.)")
        else:
            self.label_today_goal.setVisible(False)
            self.today_goal.setVisible(False)
            self.deadline.setText("Не установлен")

        # Информация о стриках
        if en.load_settings().get('global_streak', False):
            self.label_streaks.setVisible(True)
            self.label_streak_status.setVisible(True)
            self.label_max_streak.setVisible(True)
            self.streaks.setVisible(True)
            self.max_streak.setVisible(True)
            self.streak_status.setVisible(True)

            self.streaks.setText(str(len(project.streaks)))
            self.max_streak.setText(str(project.max_streak))
            self.streak_status.setText(project.get_streak_status_msg('min'))
        else:
            self.label_streaks.setVisible(False)
            self.label_streak_status.setVisible(False)
            self.label_max_streak.setVisible(False)
            self.streaks.setVisible(False)
            self.max_streak.setVisible(False)
            self.streak_status.setVisible(False)

        # Последняя запись (если есть)
        if project.notes:
            last_note = project.notes[-1]
            added_disp = en.unit_converter('symbols', last_note.added_symbols, project.unit)
            self.l.setText(f"{last_note.get_date_create_str()} (+{self._format_number(added_disp)})")
        else:
            self.l.setText("Нет записей")

    def _format_number(self, num):
        """Форматирует число для отображения."""
        if isinstance(num, float):
            if num.is_integer():
                return str(int(num))
            # Оставляем 1-2 знака после запятой, убираем лишние нули
            return f"{num:.2f}".rstrip('0').rstrip('.') if '.' in f"{num:.2f}" else str(int(num))
        return str(num)

    def select_project_by_name(self, project_name):
        """Выделяет проект по имени в списке"""
        for i in range(self.list_projects.count()):
            item = self.list_projects.item(i)
            widget = self.list_projects.itemWidget(item)
            if widget and hasattr(widget, 'project') and widget.project.name == project_name:
                self.list_projects.setCurrentItem(item)
                # Обновляем отображение информации, используя проект из виджета
                self.show_project_info(widget.project)
                self.setup_project_buttons(widget.project)
                break

    def setup_game_menu(self):
        """Инициализация игрового меню"""
        self.game_controller = GameMenuController(self.ui)

    def setup_project_buttons(self, project):
        """Настраивает кнопки управления проектом"""
        # Безопасное отключение старых соединений
        try:
            self.btn_change_project.clicked.disconnect()
        except:
            pass
        try:
            self.btn_complete_project.clicked.disconnect()
        except:
            pass
        try:
            self.btn_archived_project.clicked.disconnect()
        except:
            pass
        try:
            self.btn_delete_project.clicked.disconnect()
        except:
            pass
        try:
            self.pb_save_flash_note.clicked.disconnect()
        except:
            pass
        try:
            self.delete_note.clicked.disconnect()
        except:
            pass

        # Подключаем новые
        self.btn_change_project.clicked.connect(lambda: self.edit_project(project))
        self.btn_complete_project.clicked.connect(lambda: self.complete_project(project))
        self.btn_archived_project.clicked.connect(lambda: self.archive_project(project))
        self.btn_delete_project.clicked.connect(lambda: self.delete_project(project))
        self.pb_save_flash_note.clicked.connect(lambda: self.add_note(project))
        self.pb_save_flash_note.clicked.connect(lambda: self.refresh_global_streak_status())
        self.delete_note.clicked.connect(lambda: self.delete_selected_note(project))

        # Устанавливаем состояние кнопок в зависимости от статуса проекта
        self.change_project_widget.setEnabled(True)

        if project.status == 'завершен':
            # Проект завершён — отключаем изменение, повторное завершение, архивацию и работу с заметками
            self.btn_change_project.setEnabled(False)
            self.btn_complete_project.setEnabled(False)
            self.btn_archived_project.setEnabled(False)
            self.btn_delete_project.setEnabled(True)  # удаление обычно разрешено
            self.pb_save_flash_note.setEnabled(False)
            self.delete_note.setEnabled(False)
        else:
            # Проект активен или в архиве — настраиваем кнопки по логике
            self.btn_change_project.setEnabled(True)
            # Кнопка завершения активна, если цель достигнута
            self.btn_complete_project.setEnabled(project.goal <= project.total_symbols)

            # Меняем текст кнопки в зависимости от статуса
            if project.status == 'в архиве':
                self.btn_archived_project.setText('Активировать')
            else:
                self.btn_archived_project.setText('В архив')

            self.btn_archived_project.setEnabled(True)
            self.btn_delete_project.setEnabled(True)
            self.pb_save_flash_note.setEnabled(True)
            self.delete_note.setEnabled(True)

        # Загружаем список заметок
        self.load_notes(project)

    def load_notes(self, project):
        """Загружает список заметок проекта."""
        self.note_list.clear()
        for note in reversed(project.notes[-10:]):  # Показываем последние 10 записей
            # Конвертируем добавленные символы в единицу проекта
            added_disp = en.unit_converter('symbols', note.added_symbols, project.unit)
            added_disp_str = self._format_number(added_disp)

            # Прогресс оставляем в процентах
            progress_str = f"{note.added_progress:.2f}" if note.added_progress else "0"

            item_text = f"{note.get_date_create_str()} +{added_disp_str}/{progress_str}%"
            item = QListWidgetItem(item_text)
            self.note_list.addItem(item)

    def add_note(self, project):
        """Добавляет заметку к проекту."""
        text = self.new_symbols.text().strip()

        # Проверяем, что поле не пустое и содержит только цифры
        if not text:
            self.new_symbols.clear()
            self.notifications.show_error('Введите значение!')
            return

        try:
            new_total_in_unit = float(text)
        except ValueError:
            self.new_symbols.clear()
            self.notifications.show_error('Введите число!')
            return

        # Сохраняем старое значение для уведомления
        old_total_in_unit = project.total_symbols

        # Конвертируем в символы для расчётов и сохранения в заметке
        new_total_symbols = en.unit_converter(project.unit, new_total_in_unit, 'symbols')
        current_total_symbols = project.get_total_symbols()
        added_symbols = new_total_symbols - current_total_symbols
        goal_symbols = project.get_goal_symbols()

        if goal_symbols == float('inf'):
            added_progress = 0
        else:
            added_progress = (added_symbols / goal_symbols * 100) if goal_symbols > 0 else 0

        # Создаём заметку (храним new_total в символах)
        note = en.Note(new_total_symbols, added_symbols, added_progress)

        # Обновляем проект (total_symbols обновится в единице проекта через set_new_notes)
        project.set_new_notes(note)

        # Обновляем стрики
        project.get_streak_status()

        # Сохраняем изменения
        data = en.load_data()
        data['projects'][project.name] = project
        en.save_data(data)

        # Обновляем игровой режим если включён
        if en.load_settings().get('game_mode', False) and new_total_symbols > old_total_in_unit:
            self.game_controller.add_symbols(added_symbols)

        # Обновляем состояние кнопок, если цель достигнута
        if project.total_symbols >= project.goal:
            self.setup_project_buttons(project)

        # Очищаем поле ввода
        self.new_symbols.clear()

        # Обновляем текущий виджет в списке
        current_item = self.list_projects.currentItem()
        if current_item:
            widget = self.list_projects.itemWidget(current_item)
            if widget:
                widget.update_display()

        # Обновляем панель информации и список заметок
        self.show_project_info(project)
        self.load_notes(project)

        added_in_unit = new_total_in_unit - old_total_in_unit
        unit_name = self.unit_to_display.get(project.unit, project.unit)
        self.notifications.show_success(
            f'В {project.name} добавлено {added_symbols} символов ({added_in_unit:.1f} {unit_name})'
        )

        # Обновляем глобальный стрик
        if self.global_streak_mode:
            self.refresh_global_streak_status()

    def delete_selected_note(self, project):
        """Удаляет выбранную заметку из проекта."""
        current_item = self.note_list.currentItem()

        if current_item is None:
            self.notifications.show_warning('Выберите запись для удаления!')
            return

        selected_row = self.note_list.currentRow()

        dialog = ConfirmDialog()
        dialog.message.setText('Вы хотите удалить эту запись?\nЭто действие нельзя отменить!')
        result = dialog.exec()

        if result == QDialog.Accepted:
            # Находим индекс заметки в оригинальном списке (с учётом реверса)
            note_index = len(project.notes) - 1 - selected_row

            # Удаляем заметку
            deleted_note = project.notes.pop(note_index)

            # Обновляем total_symbols, беря последнюю запись
            if project.notes:
                last_note = project.notes[-1]
                # last_note.new_total в символах, конвертируем в единицу проекта
                project.total_symbols = en.unit_converter('symbols', last_note.new_total, project.unit)
            else:
                project.total_symbols = 0

            # Сохраняем изменения
            data = en.load_data()
            data['projects'][project.name] = project
            en.save_data(data)

            # Обновляем отображение
            self.refresh_projects()
            self.select_project_by_name(project.name)
            self.show_project_info(project)
            self.load_notes(project)

            self.notifications.show_success('Запись удалена')

    def edit_project(self, project):
        """Редактирует существующий проект."""
        dialog = EditProject(project)
        result = dialog.exec()

        if result == QDialog.Accepted:
            data = en.load_data()
            old_name = project.name

            # Получаем новые значения из диалога
            new_name = dialog.get_name()
            new_goal = dialog.get_goal()
            new_total = dialog.get_total()
            new_unit = dialog.get_unit()
            new_deadline = dialog.get_deadline()

            # Проверяем, изменилась ли единица измерения
            unit_changed = (new_unit != project.unit)

            # Если единица изменилась, показываем предупреждение
            if unit_changed:
                confirm_dialog = ConfirmDialog()
                confirm_dialog.message.setText(
                    'Изменение типа отслеживаемого значения приведет к необратимой конвертации текущей цели, прогресса и записей в новый тип (с округлением в большую сторону).\nПродолжить?'
                )
                if confirm_dialog.exec() != QDialog.Accepted:
                    return  # Отменяем сохранение, если пользователь не согласен

            # Если имя изменилось, удаляем старую запись
            if old_name != new_name and old_name in data['projects']:
                del data['projects'][old_name]

            # Обновляем поля проекта
            project.name = new_name
            project.goal = new_goal
            project.total_symbols = new_total
            project.unit = new_unit
            project.deadline = new_deadline

            # Обновляем статус проекта (если цель достигнута)
            if project.total_symbols >= project.goal and project.status != 'завершен':
                # Не завершаем автоматически, но обновим кнопки позже
                pass

            # Сохраняем под новым именем (или старым, если не изменилось)
            data['projects'][project.name] = project
            en.save_data(data)

            # Обновляем интерфейс
            self.refresh_projects()
            self.select_project_by_name(project.name)
            self.name_selected_project.setText(project.name)
            self.view_project()

            unit_name = self._get_unit_name(project.unit)
            self.notifications.show_success(
                f'Проект "{project.name}" обновлён',
                position="bottom-left"
            )

    def _get_unit_name(self, unit_code):
        """Возвращает название единицы по коду."""
        units = {
            'symbols': 'Символы',
            'A4': 'Листы А4',
            'author_list': 'Авторские листы',
            'ficbook_pages': 'Страницы Фикбука'
        }
        return units.get(unit_code, unit_code)

    def complete_project(self, project):
        """Завершает проект"""
        dialog = ConfirmDialog()
        dialog.message.setText(
            'Вы хотите завершить проект?\nЭто действие нельзя отменить\nЗавершенный проект можно только просматривать и удалить')
        result = dialog.exec()

        if result == QDialog.Accepted:
            project.status = "завершен"
            project.complete_date = en.today_for_test()

            data = en.load_data()
            data['projects'][project.name] = project
            en.save_data(data)

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.notifications.show_success(f'{project.name} завершен!')

    def archive_project(self, project):
        """Отправляет проект в архив или активирует его"""
        dialog = ConfirmDialog()

        if project.status == 'активен':
            dialog.message.setText(
                'Вы хотите архивировать проект?\nДедлайн проекта будет удален,\nпроект можно будет восстановить')
        else:
            dialog.message.setText('Вы хотите активировать проект?')

        result = dialog.exec()

        if result == QDialog.Accepted:
            if project.status == 'активен':
                project.status = "в архиве"
                project.deadline = 'Нет'
                msg = f'{project.name} архивирован.'
            else:
                project.status = "активен"
                msg = f'{project.name} снова активен.'
                # При активации дедлайн остается пустым, пользователь может установить его позже

            data = en.load_data()
            data['projects'][project.name] = project
            en.save_data(data)

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.notifications.show_success(msg, position="bottom-left")

    def delete_project(self, project):
        """Удаляет проект"""
        dialog = ConfirmDialog()
        dialog.message.setText('Вы хотите удалить проект?\nЭто действие нельзя отменить!')
        result = dialog.exec()

        if result == QDialog.Accepted:
            data = en.load_data()
            if project.name in data['projects']:
                del data['projects'][project.name]
                en.save_data(data)
                self.notifications.show_success(f'{project.name} удален.', position="bottom-left")

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)

    def generate_project_widget(self, project):
        return ProjectWidget(project, en.load_settings()['global_streak'])

    def on_filter_changed(self):
        """Обработчик изменения фильтра проектов"""
        settings = en.load_settings()
        settings['project_filter'] = self.filter_project_box.currentText()
        save_settings(settings)
        self.refresh_projects()

    def on_sort_changed(self):
        '''Обработчик изменения сортировки проектов'''
        settings = en.load_settings()
        settings['project_sort'] = self.sort_project_box.currentText()
        save_settings(settings)
        self.refresh_projects()

    def on_tab_changed(self, index):
        """Обработчик переключения вкладок"""
        current_tab = self.tabWidget.tabText(index)

        # Если текущая вкладка - "Проекты", обновляем список
        if current_tab == "Проекты":
            self.refresh_projects()
            self.refresh_global_streak_status()

            # Если есть выбранный проект, обновляем его информацию
            current_item = self.list_projects.currentItem()
            if current_item:
                widget = self.list_projects.itemWidget(current_item)
                if widget and hasattr(widget, 'project'):
                    self.show_project_info(widget.project)
                    self.setup_project_buttons(widget.project)

    def refresh_global_streak_status(self):
        # Загружаем глобальный стрик
        data = en.load_data()
        # Обновляем глобальный стрик на основе проектов
        global_status = en.global_streak_status(data)
        status_msg = en.global_streak_status_msg(data, global_status)
        self.global_streak_status.setText(status_msg if status_msg else "Глобальный стрик не начат")

    def refresh_projects(self):
        data = en.load_data()
        projects = list(data['projects'].values())

        # Обнововляем глобальный стрик
        if en.load_settings()['global_streak']:
            self.refresh_global_streak_status()

        # Получаем выбранный фильтр
        current_sort = self.sort_project_box.currentText()
        current_filter = self.filter_project_box.currentText()

        # Фильтруем проекты по статусу
        if current_filter == "Активен":
            projects = [p for p in projects if p.status == "активен"]
        elif current_filter == "В архиве":
            projects = [p for p in projects if p.status == "в архиве"]
        elif current_filter == "Завершен":
            projects = [p for p in projects if p.status == "завершен"]
        # Сортируем проекты
        if current_sort == 'Название':
            projects = sorted(projects, key=lambda p: p.name)
        elif current_sort == 'Дедлайн':
            # Исправленная сортировка по дедлайну
            def get_deadline_key(project):
                if project.deadline == 'Нет' or project.deadline is None:
                    return datetime.date.max  # проекты без дедлайна в конец
                return project.deadline

            projects = sorted(projects, key=get_deadline_key)
        elif current_sort == 'Прогресс':
            projects = sorted(projects, key=lambda p: p.progress, reverse=True)

        list_p = self.list_projects

        # Сохраняем текущий выбранный проект (если есть)
        current_project_name = None
        current_item = self.list_projects.currentItem()
        if current_item:
            widget = self.list_projects.itemWidget(current_item)
            if widget and hasattr(widget, 'project'):
                current_project_name = widget.project.name

        list_p.clear()

        for project in projects:
            widget = self.generate_project_widget(project)

            # Принудительно обновляем layout, чтобы sizeHint был актуальным
            widget.layout().activate()
            widget.widget.layout().activate()
            size = widget.sizeHint()

            item = QListWidgetItem()
            item.setSizeHint(size)
            list_p.addItem(item)
            list_p.setItemWidget(item, widget)

            if current_project_name and project.name == current_project_name:
                list_p.setCurrentItem(item)

        # Если после фильтрации текущий проект не найден, скрываем панели информации
        if current_project_name and not list_p.currentItem():
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)
            self.name_selected_project.setText("Выберите проект")

        if current_project_name:
            self.select_project_by_name(current_project_name)

    def check_global_streak(self):
        """Проверяет глобальный стрик и показывает уведомление"""
        data = en.load_data()
        global_status = data.get('global_streak_status', 'No')

    def user_agreement(self):
        dialog = UserAgreement()
        result = dialog.exec()
        agree = dialog.agree_checkBox.isChecked()
        settings = load_settings()

        if result == QDialog.Accepted and agree:
            settings['user_agreement'] = True
            save_settings(settings)
            dialog.close()
        else:
            sys.exit(0)


    def check_user_agreement(self):
        settings = en.load_settings()
        user_agreement = settings.get('user_agreement', False)
        if not user_agreement:
            self.user_agreement()


class ConfirmDialog(QDialog, confirm_dialog_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class CreateProject(QDialog, create_project_ui):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Словари для преобразования
        self.text_to_unit = {
            'Символы': 'symbols',
            'Листы A4': 'A4',
            'Авторские листы': 'author_list',
            'Страницы Фикбука': 'ficbook_pages'
        }
        self.unit_to_text = {v: k for k, v in self.text_to_unit.items()}

        # Текущая единица
        self.current_unit = self.text_to_unit[self.cb_unit.currentText()]

        # Скрываем предупреждения
        self.incorrect_name.setVisible(False)
        self.incorrect_data.setVisible(False)

        # Подключаем сигналы
        self.checkBox.toggled.connect(self.on_checkbox_toggled)
        self.de_deadline.dateChanged.connect(self.validate_all)
        self.le_name.textChanged.connect(self.validate_all)
        self.le_goal.textChanged.connect(self.validate_all)
        self.le_total_symbols.textChanged.connect(self.validate_all)
        self.cb_unit.currentTextChanged.connect(self.on_unit_changed)

        # Устанавливаем минимальную дату - сегодня
        self.de_deadline.setMinimumDate(en.today_for_test())

        # Изначально кнопки должны быть активны, т.к. данные корректны
        self.buttons.setEnabled(True)

        # Вызываем обработчик чекбокса для начальной настройки
        self.on_checkbox_toggled(self.checkBox.isChecked())

        # Вызываем валидацию для проверки всех полей
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.validate_all)

    def on_checkbox_toggled(self, checked):
        """Обработчик чекбокса 'Нет дедлайна'."""
        if checked:
            self.de_deadline.setDisabled(True)
            self.incorrect_data.setVisible(False)
        else:
            self.de_deadline.setEnabled(True)
            self.de_deadline.setMinimumDate(en.today_for_test())
        self.validate_all()

    def on_unit_changed(self, new_unit_text):
        """Конвертирует значения полей при смене единицы."""
        new_unit = self.text_to_unit[new_unit_text]

        # Если поля пустые - просто обновляем текущую единицу
        if not self.le_goal.text() or not self.le_total_symbols.text():
            self.current_unit = new_unit
            self.validate_all()
            return

        try:
            goal_val = float(self.le_goal.text())
            total_val = float(self.le_total_symbols.text())
        except ValueError:
            self.current_unit = new_unit
            self.validate_all()
            return

        # Конвертируем значения
        new_goal = en.unit_converter(self.current_unit, goal_val, new_unit)
        new_total = en.unit_converter(self.current_unit, total_val, new_unit)

        # Округляем до 2 знаков для отображения
        self.le_goal.setText(f"{new_goal:.2f}".rstrip('0').rstrip('.') if '.' in f"{new_goal:.2f}" else f"{new_goal:.0f}")
        self.le_total_symbols.setText(f"{new_total:.2f}".rstrip('0').rstrip('.') if '.' in f"{new_total:.2f}" else f"{new_total:.0f}")

        self.current_unit = new_unit
        self.validate_all()

    def validate_all(self):
        """Валидация всех полей."""
        data = en.load_data()
        existing_names = list(data['projects'].keys())

        # Сбрасываем сообщения об ошибках (кроме имени, если оно есть)
        self.incorrect_data.setVisible(False)
        error_messages = []

        # Проверка имени
        current_name = self.le_name.text().strip()
        name_filled = bool(current_name)
        name_incorrect = current_name in existing_names and current_name != ""
        self.incorrect_name.setVisible(name_incorrect)
        if name_incorrect:
            error_messages.append("Проект с таким именем уже существует")

        # Проверка дедлайна
        deadline_incorrect = False
        if not self.checkBox.isChecked():
            selected_date = self.de_deadline.date().toPython()
            if selected_date < en.today_for_test():
                deadline_incorrect = True
                error_messages.append("Дедлайн не может быть в прошлом")

        # Проверка цели
        goal_text = self.le_goal.text().strip()
        goal_valid = False
        if goal_text:
            try:
                goal_val = float(goal_text)
                if goal_val > 0:
                    goal_valid = True
                else:
                    error_messages.append("Цель должна быть положительным числом")
            except ValueError:
                error_messages.append("Цель должна быть числом")
        else:
            error_messages.append("Введите цель")

        # Проверка текущего значения
        total_text = self.le_total_symbols.text().strip()
        total_valid = False
        if total_text:
            try:
                total_val = float(total_text)
                if total_val >= 0:
                    total_valid = True
                else:
                    error_messages.append("Текущее значение не может быть отрицательным")
            except ValueError:
                error_messages.append("Текущее значение должно быть числом")
        else:
            error_messages.append("Введите текущее значение")

        # Проверка что цель >= текущее значение (если оба валидны)
        goal_ge_total = True
        if goal_valid and total_valid:
            goal_val = float(goal_text)
            total_val = float(total_text)
            if goal_val < total_val:
                goal_ge_total = False
                error_messages.append("Цель должна быть больше или равна текущему значению")

        # Если есть ошибки, показываем первую в incorrect_data
        if error_messages:
            self.incorrect_data.setVisible(True)
            self.incorrect_data.setText("\n".join(error_messages[:1]))  # показываем первую ошибку
        else:
            self.incorrect_data.setVisible(False)

        # Финальное состояние кнопок
        buttons_enabled = (
            name_filled and not name_incorrect and
            not deadline_incorrect and
            goal_valid and total_valid and goal_ge_total
        )
        self.buttons.setEnabled(buttons_enabled)

    def get_goal(self):
        try:
            return float(self.le_goal.text())
        except:
            return 0

    def get_total(self):
        try:
            return float(self.le_total_symbols.text())
        except:
            return 0

    def get_unit(self):
        return self.current_unit

    def get_deadline(self):
        if self.checkBox.isChecked():
            return 'Нет'
        return self.de_deadline.date().toPython()

    def get_name(self):
        return self.le_name.text().strip()


class EditProject(QDialog, create_project_ui):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Редактирование проекта')

        self.project = project
        self.original_name = project.name

        # Словари для преобразования
        self.text_to_unit = {
            'Символы': 'symbols',
            'Листы A4': 'A4',
            'Авторские листы': 'author_list',
            'Страницы Фикбука': 'ficbook_pages'
        }
        self.unit_to_text = {v: k for k, v in self.text_to_unit.items()}

        # Текущая единица (из проекта)
        self.current_unit = project.unit
        self.cb_unit.setCurrentText(self.unit_to_text[self.current_unit])

        # Скрываем предупреждения
        self.incorrect_name.setVisible(False)
        self.incorrect_data.setVisible(False)

        # Заполняем поля данными из проекта
        self.le_name.setText(project.name)
        self.le_goal.setText(self._format_number(project.goal))
        self.le_total_symbols.setText(self._format_number(project.total_symbols))

        # Дедлайн
        if project.deadline != 'Нет':
            self.checkBox.setChecked(False)
            qdate = QDate(project.deadline.year, project.deadline.month, project.deadline.day)
            self.de_deadline.setDate(qdate)
            self.de_deadline.setEnabled(True)
        else:
            self.checkBox.setChecked(True)
            self.de_deadline.setDisabled(True)

        # Подключаем сигналы
        self.checkBox.toggled.connect(self.on_checkbox_toggled)
        self.de_deadline.dateChanged.connect(self.validate_all)
        self.le_name.textChanged.connect(self.validate_all)
        self.le_goal.textChanged.connect(self.validate_all)
        self.le_total_symbols.textChanged.connect(self.validate_all)
        self.cb_unit.currentTextChanged.connect(self.on_unit_changed)

        # Устанавливаем минимальную дату - сегодня
        self.de_deadline.setMinimumDate(en.today_for_test())

        # Начальное состояние кнопок (после заполнения данных они должны быть активны)
        self.buttons.setEnabled(True)
        self.on_checkbox_toggled(self.checkBox.isChecked())

        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.validate_all)

    def _format_number(self, num):
        if isinstance(num, float) and num.is_integer():
            return str(int(num))
        return str(num)

    def on_checkbox_toggled(self, checked):
        if checked:
            self.de_deadline.setDisabled(True)
            self.incorrect_data.setVisible(False)
        else:
            self.de_deadline.setEnabled(True)
            self.de_deadline.setMinimumDate(en.today_for_test())
        self.validate_all()

    def on_unit_changed(self, new_unit_text):
        new_unit = self.text_to_unit[new_unit_text]

        if not self.le_goal.text() or not self.le_total_symbols.text():
            self.current_unit = new_unit
            self.validate_all()
            return

        try:
            goal_val = float(self.le_goal.text())
            total_val = float(self.le_total_symbols.text())
        except ValueError:
            self.current_unit = new_unit
            self.validate_all()
            return

        new_goal = en.unit_converter(self.current_unit, goal_val, new_unit)
        new_total = en.unit_converter(self.current_unit, total_val, new_unit)

        self.le_goal.setText(self._format_number(new_goal))
        self.le_total_symbols.setText(self._format_number(new_total))

        self.current_unit = new_unit
        self.validate_all()

    def validate_all(self):
        data = en.load_data()
        existing_names = list(data['projects'].keys())

        self.incorrect_data.setVisible(False)
        error_messages = []

        # Имя
        current_name = self.le_name.text().strip()
        name_filled = bool(current_name)
        name_incorrect = False
        if name_filled and current_name != self.original_name:
            name_incorrect = current_name in existing_names
        self.incorrect_name.setVisible(name_incorrect)
        if name_incorrect:
            error_messages.append("Проект с таким именем уже существует")

        # Дедлайн
        deadline_incorrect = False
        if not self.checkBox.isChecked():
            selected_date = self.de_deadline.date().toPython()
            if selected_date < en.today_for_test():
                deadline_incorrect = True
                error_messages.append("Дедлайн не может быть в прошлом")

        # Цель
        goal_text = self.le_goal.text().strip()
        goal_valid = False
        if goal_text:
            try:
                goal_val = float(goal_text)
                if goal_val > 0:
                    goal_valid = True
                else:
                    error_messages.append("Цель должна быть положительным числом")
            except ValueError:
                error_messages.append("Цель должна быть числом")
        else:
            error_messages.append("Введите цель")

        # Текущее значение
        total_text = self.le_total_symbols.text().strip()
        total_valid = False
        if total_text:
            try:
                total_val = float(total_text)
                if total_val >= 0:
                    total_valid = True
                else:
                    error_messages.append("Текущее значение не может быть отрицательным")
            except ValueError:
                error_messages.append("Текущее значение должно быть числом")
        else:
            error_messages.append("Введите текущее значение")

        # Цель >= текущее
        goal_ge_total = True
        if goal_valid and total_valid:
            goal_val = float(goal_text)
            total_val = float(total_text)
            if goal_val < total_val:
                goal_ge_total = False
                error_messages.append("Цель должна быть больше или равна текущему значению")

        if error_messages:
            self.incorrect_data.setVisible(True)
            self.incorrect_data.setText("\n".join(error_messages[:1]))
        else:
            self.incorrect_data.setVisible(False)

        buttons_enabled = (
            name_filled and not name_incorrect and
            not deadline_incorrect and
            goal_valid and total_valid and goal_ge_total
        )
        self.buttons.setEnabled(buttons_enabled)

    def get_goal(self):
        try:
            return float(self.le_goal.text())
        except:
            return self.project.goal

    def get_total(self):
        try:
            return float(self.le_total_symbols.text())
        except:
            return self.project.total_symbols

    def get_unit(self):
        return self.current_unit

    def get_deadline(self):
        if self.checkBox.isChecked():
            return 'Нет'
        return self.de_deadline.date().toPython()

    def get_name(self):
        return self.le_name.text().strip()

class NotificationManager:
    """Менеджер для показа уведомлений с поддержкой очереди и накопления."""

    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.toasts = []          # все активные уведомления в порядке добавления
        self.spacing = 10        # отступ между уведомлениями
        self.max_toasts = 5        # максимальное количество одновременно видимых
        self.margin = 5           # отступ от края окна

    def _compute_x(self, toast, position):
        """Вычисляет x-координату для уведомления в зависимости от его позиции и ширины."""
        parent_rect = self.parent.rect()
        width = toast.width()
        if position in ("top-right", "bottom-right"):
            return parent_rect.width() - width - self.margin
        elif position in ("top-left", "bottom-left"):
            return self.margin
        elif position in ("top-center", "bottom-center"):
            return (parent_rect.width() - width) // 2
        else:   # по умолчанию правый нижний
            return parent_rect.width() - width - self.margin

    def _rearrange_toasts(self):
        """Пересчитывает позиции всех уведомлений в зависимости от их положения."""
        # Группируем по позиции
        groups = {}
        for toast in self.toasts:
            pos = toast.position
            groups.setdefault(pos, []).append(toast)

        parent_rect = self.parent.rect()

        for position, toasts in groups.items():
            if position.startswith("top"):      # верхние позиции – новые сверху
                current_y = self.margin
                for toast in reversed(toasts):   # от новых к старым
                    x = self._compute_x(toast, position)
                    toast.set_global_position(x, current_y)
                    current_y += toast.height() + self.spacing

            elif position.startswith("bottom"): # нижние позиции – новые снизу
                current_y = parent_rect.height() - self.margin
                for toast in reversed(toasts):   # от новых к старым
                    x = self._compute_x(toast, position)
                    current_y -= toast.height()
                    toast.set_global_position(x, current_y)
                    current_y -= self.spacing

            else:   # на случай других значений – просто по порядку сверху
                current_y = self.margin
                for toast in toasts:
                    x = self._compute_x(toast, position)
                    toast.set_global_position(x, current_y)
                    current_y += toast.height() + self.spacing

    def remove_toast_before_fade(self, toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
            self._rearrange_toasts()

    def _add_toast(self, toast):
        self.toasts.append(toast)
        # Убираем подключение к destroyed, теперь удаление происходит в remove_toast_before_fade
        if len(self.toasts) > self.max_toasts:
            oldest = self.toasts[0]
            oldest.start_fade_out()

        self._rearrange_toasts()
        toast.show()
        toast.fade_in_anim.start()

    # В каждом методе показа передаём manager=self
    def show_success(self, message, duration=3000, position="bottom-right"):
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        toast.setStyleSheet("""
            QFrame {
                background-color: rgba(76, 175, 80, 220);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self._add_toast(toast)

    def show_error(self, message, duration=5000, position="bottom-right"):
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        toast.setStyleSheet("""
            QFrame {
                background-color: rgba(244, 67, 54, 220);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self._add_toast(toast)

    def show_warning(self, message, duration=4000, position="bottom-right"):
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        toast.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 152, 0, 220);
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self._add_toast(toast)

    def show_info(self, message, duration=3000, position="bottom-right"):
        toast = ToastNotification(self.parent, message, duration, position, manager=self)
        self._add_toast(toast)

class Settings(QDialog, settings_ui):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Обрабатываем настройки
        settings = en.load_settings()
        if settings['inf_project'] is False:
            self.enable_inf_projects_checkBox.setChecked(False)
        else:
            self.enable_inf_projects_checkBox.setChecked(True)
        if settings['game_mode'] is False:
            self.enable_game_mode_checkBox.setChecked(False)
        else:
            self.enable_game_mode_checkBox.setChecked(True)
        if settings['global_streak'] is False:
            self.enable_global_streak_checkBox.setChecked(False)
        else:
            self.enable_global_streak_checkBox.setChecked(True)

class UserAgreement(QDialog, user_agreement_ui):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = QTranslator()
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if translator.load("qt_ru", translations_path):
        app.installTranslator(translator)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())