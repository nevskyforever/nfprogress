import os
import sys

from PySide6.QtCore import QTranslator, QLibraryInfo, QDate, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMainWindow, QDialog, QListWidgetItem

import engine as en
import game

from game_UI import GameMenuController

from UI_fiiles.confirm_dialog import Ui_confirm_dialog as confirm_dialog_ui
from UI_fiiles.create_project import Ui_d_create_project as create_project_ui
from UI_fiiles.edit_project import Ui_edit_project as edit_project_ui
from UI_fiiles.main_window import Ui_main_window as main_window_ui
from UI_fiiles.notification import ToastNotification
from UI_fiiles.project_widget import ProjectWidget
from UI_fiiles.settings import Ui_Dialog as settings_ui
from engine import save_data, save_settings


def resource_path(relative_path):
    """Получить путь к ресурсу, работает и в .py, и в .app"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MainWindow(QMainWindow, main_window_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Применяем настройки
        self.applying_settings()
        self.global_streak_mode = en.load_settings().get('global_streak', False)

        # Обновляем проекты
        self.refresh_projects()

        # Подключаем обработчик изменения фильтра
        self.filter_project_box.currentTextChanged.connect(self.on_filter_changed)

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
        self.menu.addAction("Параметры").triggered.connect(self.edit_settings)
        self.menu.addAction("Выход").triggered.connect(self.close)

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
        dialog = CreateProject()
        result = dialog.exec()

        if result == QDialog.Accepted:
            print("Диалог закрыт по OK")
            data = en.load_data()
            name = dialog.le_name.text()
            goal = int(dialog.le_goal.text())

            if dialog.checkBox.isChecked():
                deadline = 'Нет'
            else:
                qdate = dialog.de_deadline.date()
                deadline = qdate.toPython()

            total = int(dialog.le_total_symbols.text())

            new_project = en.Project(name=name, goal=goal, deadline=deadline, total_symbols=total)
            data['projects'][new_project.name] = new_project
            en.save_data(data)

            self.refresh_projects()
            dialog.close()

            QTimer.singleShot(100, lambda: self.notifications.show_success(
                f"Проект '{name}' создан!",
                2000,
                "bottom-left"
            ))

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
                print("Игровая вкладка удалена")
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
                print("Игровая вкладка добавлена")

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
        """Заполняет виджеты информацией о проекте"""
        # Основная информация
        self.status.setText(project.status)
        self.progress.setText(f"{project.progress:.1f}%")
        self.goal.setText(str(project.goal))
        self.total.setText(str(project.total_symbols))

        # Статистика за сегодня
        today_added = project.get_added_symbols_today_value()
        self.added_today.setText(str(today_added))

        # Осталось написать
        need = project.get_need_write_value()
        self.need.setText(str(need))

        # Дедлайн
        if project.deadline != 'Нет':
            self.deadline.setText(project.deadline_str)
            self.label_today_goal.setVisible(True)
            self.today_goal.setVisible(True)
            if project.get_added_symbols_today_value() < project.get_today_goal_value():
                self.today_goal.setText(str(project.get_today_goal_value()))
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
        if en.load_settings()['global_streak']:
            # Показываем все элементы, связанные со стриками
            self.label_streaks.setVisible(True)
            self.label_streak_status.setVisible(True)
            self.label_max_streak.setVisible(True)

            # Показывакм значения
            self.streaks.setVisible(True)
            self.max_streak.setVisible(True)
            self.streak_status.setVisible(True)

            # Устанавливаем значения
            self.streaks.setText(str(len(project.streaks)))
            self.max_streak.setText(str(project.max_streak))
            self.streak_status.setText(project.get_streak_status_msg('min'))
        else:
            # Скрываем все элементы, связанные со стриками
            self.label_streaks.setVisible(False)
            self.label_streak_status.setVisible(False)
            self.label_max_streak.setVisible(False)
            self.streaks.setVisible(False)
            self.max_streak.setVisible(False)
            self.streak_status.setVisible(False)

        # Последняя запись (если есть)
        if project.notes:
            last_note = project.notes[-1]
            self.l.setText(f"{last_note.get_date_create_str()} (+{last_note.added_symbols})")
        else:
            self.l.setText("Нет записей")

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
        """Загружает список заметок проекта"""
        self.note_list.clear()
        for note in reversed(project.notes[-10:]):  # Показываем последние 10 записей
            item = QListWidgetItem(
                f"{note.get_date_create_str()} +{note.added_symbols}/{round(note.added_progress, 2)}%")
            self.note_list.addItem(item)

    def add_note(self, project):
        """Добавляет заметку к проекту"""
        text = self.new_symbols.text().strip()

        # Проверяем, что поле не пустое и содержит только цифры
        if not text or not text.isdigit():
            self.new_symbols.clear()
            self.notifications.show_error('В записи могут быть только цифры!')
            return

        new_total = int(text)

        # Проверяем, что новое значение больше текущего
        if new_total < project.total_symbols:
            self.new_symbols.clear()
            self.notifications.show_error(f'Новое значение должно быть больше текущего ({project.total_symbols})!')
            return

        added = new_total - project.total_symbols
        added_progress = (added / project.goal * 100) if project.goal > 0 else 0

        # Создаём запись
        note = en.Note(new_total, added, added_progress)
        project.set_new_notes(note)
        project.total_symbols = new_total
        if en.load_settings()['game_mode']:
            self.game_controller.add_symbols(added)

        # Сохраняем изменения
        data = en.load_data()
        data['projects'][project.name] = project
        en.save_data(data)

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
        self.notifications.show_success(f'В {project.name} добавлено {added} символов')

        #Обновляем глобальный стрик
        if self.global_streak_mode:
            self.refresh_global_streak_status()

    def delete_selected_note(self, project):
        """Удаляет выбранную заметку из проекта"""
        # Получаем текущий выбранный элемент в списке заметок
        current_item = self.note_list.currentItem()

        if current_item is None:
            # Если ничего не выбрано, показываем предупреждение
            self.notifications.show_warning('Выберите запись для удаления!')
            return

        # Получаем индекс выбранной заметки
        selected_row = self.note_list.currentRow()

        # Показываем диалог подтверждения
        dialog = ConfirmDialog()
        dialog.message.setText('Вы хотите удалить эту запись?\nЭто действие нельзя отменить!')
        result = dialog.exec()

        if result == QDialog.Accepted:
            # Находим индекс заметки в оригинальном списке (с учётом реверса при отображении)
            note_index = len(project.notes) - 1 - selected_row

            # Удаляем заметку
            deleted_note = project.notes.pop(note_index)

            # Обновляем total_symbols, вычитая удалённые символы
            if project.notes:
                # Берём последнюю запись для восстановления корректного total_symbols
                last_note = project.notes[-1]
                project.total_symbols = last_note.new_total
            else:
                # Если записей больше нет, обнуляем total_symbols
                project.total_symbols = 0

            # Сохраняем изменения
            data = en.load_data()
            data['projects'][project.name] = project
            save_data(data)

            # Обновляем отображение
            self.refresh_projects()
            # Восстанавливаем выделение проекта
            self.select_project_by_name(project.name)
            # Обновляем информацию о проекте
            self.show_project_info(project)
            # Перезагружаем список заметок
            self.load_notes(project)

            print(f"Запись от {deleted_note.get_date_create_str()} удалена")

    def edit_project(self, project):
        old_name = project.name
        dialog = EditProject(old_name=old_name)

        # Заполняем поля
        dialog.le_name.setText(project.name)
        dialog.le_goal.setText(str(project.goal))
        dialog.le_total_symbols.setText(str(project.total_symbols))

        if project.deadline != 'Нет':
            dialog.checkBox.setChecked(False)
            qdate = QDate(project.deadline.year, project.deadline.month, project.deadline.day)
            dialog.de_deadline.setDate(qdate)
        else:
            dialog.checkBox.setChecked(True)
            dialog.de_deadline.setDisabled(True)

        result = dialog.exec()

        if result == QDialog.Accepted:
            try:
                # Получаем новые значения
                name = dialog.le_name.text()
                goal = int(dialog.le_goal.text())
                total = int(dialog.le_total_symbols.text())

                if dialog.checkBox.isChecked():
                    deadline = 'Нет'
                else:
                    qdate = dialog.de_deadline.date()
                    deadline = qdate.toPython()

                # Если имя изменилось, нужно удалить старый ключ и создать новый
                if old_name != name:
                    # Удаляем проект из словаря по старому имени
                    data = en.load_data()
                    if old_name in data['projects']:
                        del data['projects'][old_name]

                    # Обновляем поля проекта
                    project.name = name
                    project.goal = goal
                    project.total_symbols = total
                    project.deadline = deadline

                    # Добавляем проект с новым именем
                    data['projects'][name] = project
                    en.save_data(data)
                else:
                    # Имя не изменилось, просто обновляем поля
                    project.goal = goal
                    project.total_symbols = total
                    project.deadline = deadline

                    # Сохраняем изменения
                    data = en.load_data()
                    data['projects'][project.name] = project
                    en.save_data(data)

                # Полностью обновляем список проектов
                self.refresh_projects()

                # Выделяем измененный проект по новому имени
                self.select_project_by_name(project.name)
                self.name_selected_project.setText(project.name)
                self.view_project()
                self.notifications.show_success(f'Изменения в {project.name} сохранены', position="bottom-left")

            except ValueError as e:
                self.notifications.show_error(f"Ошибка при сохранении: {e}")

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
        self.refresh_projects()

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
        current_filter = self.filter_project_box.currentText()

        # Фильтруем проекты по статусу
        if current_filter == "Активен":
            projects = [p for p in projects if p.status == "активен"]
        elif current_filter == "В архиве":
            projects = [p for p in projects if p.status == "в архиве"]
        elif current_filter == "Завершен":
            projects = [p for p in projects if p.status == "завершен"]

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
        try:
            data = en.load_data()
            global_status = data.get('global_streak_status', 'No')

            # Проверяем, начинается ли статус с "Lose"
            if isinstance(global_status, str) and global_status.startswith('Lose'):
                self.notifications.show_error('Глобальный стрик потерян!', position="top-left")
                print(f"Глобальный стрик потерян! Статус: {global_status}")
            else:
                print(f"Глобальный стрик в порядке. Статус: {global_status}")

        except (KeyError, IndexError, AttributeError) as e:
            print(f"Ошибка при проверке глобального стрика: {e}")

class ConfirmDialog(QDialog, confirm_dialog_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class CreateProject(QDialog, create_project_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Скрываем предупреждения при создании
        self.incorrect_name.setVisible(False)
        self.incorrect_data.setVisible(False)

        # Подключаем сигнал чекбокса к обработчику
        self.checkBox.toggled.connect(self.on_checkbox_toggled)
        self.checkBox.toggled.connect(self.all_data_ok)

        # Подключаем сигнал изменения даты
        self.de_deadline.dateChanged.connect(self.all_data_ok)

        # Подключаем сигналы изменения текста
        self.le_name.textChanged.connect(self.all_data_ok)
        self.le_goal.textChanged.connect(self.all_data_ok)
        self.le_total_symbols.textChanged.connect(self.all_data_ok)

        # Устанавливаем начальное состояние
        self.buttons.setDisabled(True)
        self.on_checkbox_toggled(self.checkBox.isChecked())

        # Вызываем проверку после того, как все подключено
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.all_data_ok)

    def on_checkbox_toggled(self, checked):
        """Обработчик изменения состояния чекбокса"""
        if checked:  # Если чекбокс отмечен (Нет дедлайна)
            self.de_deadline.setDisabled(True)
            self.incorrect_data.setVisible(False)  # Скрываем сообщение о дедлайне
        else:  # Если чекбокс не отмечен (Есть дедлайн)
            self.de_deadline.setEnabled(True)
            # Проверим дату сразу при включении
            self.all_data_ok()

    def all_data_ok(self):
        """Проверяет заполненность полей и включает/выключает кнопки"""
        # Получаем список существующих проектов из словаря
        data = en.load_data()
        existing_names = list(data['projects'].keys())

        # Проверяем имя
        current_name = self.le_name.text().strip()
        name_filled = bool(current_name)
        name_incorrect = current_name in existing_names and current_name != ""
        self.incorrect_name.setVisible(name_incorrect)

        # Проверяем дату дедлайна (только если чекбокс НЕ отмечен)
        deadline_incorrect = False
        if not self.checkBox.isChecked():
            deadline_incorrect = self.de_deadline.date() <= en.today_for_test()
            self.incorrect_data.setVisible(deadline_incorrect)
        else:
            # Если чекбокс отмечен, скрываем сообщение о дедлайне
            self.incorrect_data.setVisible(False)

        # Проверяем, что поле goal содержит только цифры и не пустое
        goal_text = self.le_goal.text().strip()
        goal_filled = goal_text.isdigit() if goal_text else False

        # Проверяем, что поле total_symbols содержит только цифры и не пустое
        total_text = self.le_total_symbols.text().strip()
        total_filled = total_text.isdigit() if total_text else False

        # Кнопки включены только если:
        # - имя заполнено И имя НЕ используется
        # - цель заполнена цифрами
        # - total_symbols заполнен цифрами
        # - (если дедлайн есть) дата корректна
        if self.checkBox.isChecked():
            # Если дедлайна нет, не проверяем дату
            buttons_enabled = name_filled and not name_incorrect and goal_filled and total_filled
        else:
            # Если дедлайн есть, проверяем и дату
            buttons_enabled = name_filled and not name_incorrect and goal_filled and total_filled and not deadline_incorrect

        self.buttons.setEnabled(buttons_enabled)


class EditProject(QDialog, edit_project_ui):
    def __init__(self, old_name=""):
        super().__init__()
        self.setupUi(self)

        # Сохраняем старое имя проекта
        self.old_name = old_name

        # Скрываем предупреждения при создании
        self.incorrect_name.setVisible(False)
        self.incorrect_data.setVisible(False)

        # Подключаем сигнал чекбокса к обработчику
        self.checkBox.toggled.connect(self.on_checkbox_toggled)
        self.checkBox.toggled.connect(self.all_data_ok)

        # Подключаем сигнал изменения даты
        self.de_deadline.dateChanged.connect(self.all_data_ok)

        # Подключаем сигналы изменения текста
        self.le_name.textChanged.connect(self.all_data_ok)
        self.le_goal.textChanged.connect(self.all_data_ok)
        self.le_total_symbols.textChanged.connect(self.all_data_ok)

        # Устанавливаем начальное состояние
        self.buttons.setDisabled(True)
        self.on_checkbox_toggled(self.checkBox.isChecked())

        # Вызываем проверку после того, как все подключено
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.all_data_ok)

    def on_checkbox_toggled(self, checked):
        """Обработчик изменения состояния чекбокса"""
        if checked:  # Если чекбокс отмечен (Нет дедлайна)
            self.de_deadline.setDisabled(True)
            self.incorrect_data.setVisible(False)  # Скрываем сообщение о дедлайне
        else:  # Если чекбокс не отмечен (Есть дедлайн)
            self.de_deadline.setEnabled(True)
            # Проверим дату сразу при включении
            self.all_data_ok()

    def all_data_ok(self):
        """Проверяет заполненность полей и включает/выключает кнопки"""
        # Получаем список существующих проектов из словаря
        data = en.load_data()
        existing_names = list(data['projects'].keys())

        # Проверяем имя
        current_name = self.le_name.text().strip()
        name_filled = bool(current_name)

        # Имя некорректно только если:
        # 1. Имя не пустое
        # 2. Имя отличается от старого
        # 3. Такое имя уже существует в других проектах
        name_incorrect = False
        if name_filled and current_name != self.old_name:
            name_incorrect = current_name in existing_names

        self.incorrect_name.setVisible(name_incorrect)

        # Проверяем дату дедлайна (только если чекбокс НЕ отмечен)
        deadline_incorrect = False
        if not self.checkBox.isChecked():
            deadline_incorrect = self.de_deadline.date() <= en.today_for_test()
            self.incorrect_data.setVisible(deadline_incorrect)
        else:
            # Если чекбокс отмечен, скрываем сообщение о дедлайне
            self.incorrect_data.setVisible(False)

        # Проверяем, что поле goal содержит только цифры и не пустое
        goal_text = self.le_goal.text().strip()
        goal_filled = goal_text.isdigit() if goal_text else False

        # Проверяем, что поле total_symbols содержит только цифры и не пустое
        total_text = self.le_total_symbols.text().strip()
        total_filled = total_text.isdigit() if total_text else False

        # Кнопки включены только если:
        # - имя заполнено И (имя не изменилось ИЛИ новое имя не занято)
        # - цель заполнена цифрами
        # - total_symbols заполнен цифрами
        # - (если дедлайн есть) дата корректна
        if self.checkBox.isChecked():
            # Если дедлайна нет, не проверяем дату
            buttons_enabled = name_filled and not name_incorrect and goal_filled and total_filled
        else:
            # Если дедлайн есть, проверяем и дату
            buttons_enabled = name_filled and not name_incorrect and goal_filled and total_filled and not deadline_incorrect

        self.buttons.setEnabled(buttons_enabled)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = QTranslator()
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if translator.load("qt_ru", translations_path):
        app.installTranslator(translator)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())