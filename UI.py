import sys
from datetime import date
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QListWidgetItem
from PySide6.scripts.project_lib import new_project
from PySide6.QtWidgets import QApplication, QSizePolicy
from PySide6.QtCore import QTranslator, QLibraryInfo, QSize
import engine as en
from UI_fiiles.main_window import Ui_main_window as main_window_ui
from UI_fiiles.create_project import Ui_d_create_project as create_project_ui
from UI_fiiles.project_widget import Ui_Form as project_form_ui
from UI_fiiles.confirm_dialog import Ui_confirm_dialog as confirm_dialog_ui
from UI_fiiles.edit_project import Ui_edit_project as edit_project_ui


class MainWindow(QMainWindow, main_window_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.refresh_projects()

        # Правильный способ подключения кнопки
        self.project_info.setVisible(False)
        self.note_widget.setVisible(False)
        self.change_project_widget.setVisible(False)
        self.btn_create_project.clicked.connect(self.create_project)
        self.list_projects.itemClicked.connect(self.view_project)

        self.show()

    def create_project(self):
        dialog = CreateProject()
        result = dialog.exec_()

        if result == QDialog.Accepted:
            print("Диалог закрыт по OK")
            data = en.load_data()
            name = dialog.le_name.text()
            goal = int(dialog.le_goal.text())

            if dialog.checkBox.isChecked():
                deadline = 'Нет'
            else:
                qdate = dialog.de_deadline.date()
                deadline = qdate.toPython()  # преобразуем

            total = int(dialog.le_total_symbols.text())

            new_project = en.Project(name=name, goal=goal, deadline=deadline, total_symbols=total)
            data['projects'].append(new_project)
            en.save_data(data)

            self.refresh_projects()
            dialog.close()

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

            # Расчёт оставшихся дней
            days_left = (project.deadline - en.today_for_test()).days
            if days_left > 0:
                self.deadline.setText(f"{project.deadline_str} (осталось {days_left} дн.)")
            elif days_left == 0:
                self.deadline.setText(f"{project.deadline_str} (сегодня!)")
            else:
                self.deadline.setText(f"{project.deadline_str} (просрочено на {abs(days_left)} дн.)")
        else:
            self.deadline.setText("Не установлен")

        # Информация о стриках
        self.streaks.setText(str(len(project.streaks)))
        self.max_streak.setText(str(project.max_streak))
        self.streak_status.setText(project.get_streak_status_msg())

        # Последняя запись (если есть)
        if project.notes:
            last_note = project.notes[-1]
            self.l.setText(f"{last_note.get_date_create_str()} (+{last_note.added_symbols})")
        else:
            self.l.setText("Нет записей")

    def setup_project_buttons(self, project):
        """Настраивает кнопки управления проектом"""
        # Отключаем старые соединения
        try:
            self.btn_change_project.clicked.disconnect()
            self.btn_complete_project.clicked.disconnect()
            self.btn_archived_project.clicked.disconnect()
            self.btn_delete_project.clicked.disconnect()
            self.pb_save_flash_note.clicked.disconnect()
        except:
            pass  # Если не было соединений

        # Подключаем новые
        self.btn_change_project.clicked.connect(lambda: self.edit_project(project))
        self.btn_complete_project.clicked.connect(lambda: self.complete_project(project))
        self.btn_archived_project.clicked.connect(lambda: self.archive_project(project))
        self.btn_delete_project.clicked.connect(lambda: self.delete_project(project))
        self.pb_save_flash_note.clicked.connect(lambda: self.add_note(project))

        # Включаем кнопки (если они были отключены в дизайнере)
        self.change_project_widget.setEnabled(True)
        self.btn_change_project.setEnabled(True)
        if project.goal <= project.total_symbols:
            self.btn_complete_project.setEnabled(True)
        self.btn_archived_project.setEnabled(True)
        self.btn_delete_project.setEnabled(True)
        self.pb_save_flash_note.setEnabled(True)

        # Загружаем список заметок
        self.load_notes(project)

    def load_notes(self, project):
        """Загружает список заметок проекта"""
        self.note_list.clear()
        for note in reversed(project.notes[-10:]):  # Показываем последние 10 записей
            item = QListWidgetItem(f"{note.get_date_create_str()} +{note.added_symbols}/{round(note.added_progress, 2)}%")
            self.note_list.addItem(item)

    def add_note(self, project):
        """Добавляет заметку к проекту"""
        text = self.new_symbols.text().strip()
        if not text or not text.isdigit():
            return

        new_total = int(text)
        added = new_total - project.total_symbols
        added_progress = (added / project.goal * 100) if project.goal > 0 else 0

        # Создаём запись
        note = en.Note(new_total, added, added_progress)
        project.set_new_notes(note)
        project.total_symbols = new_total

        # Сохраняем изменения
        data = en.load_data()
        # Находим и обновляем проект в данных
        en.save_project(project)

        # Очищаем поле ввода
        self.new_symbols.clear()

        # Обновляем отображение
        self.refresh_projects()
        self.show_project_info(project)
        self.load_notes(project)

    def edit_project(self, project):
        """Редактирует проект"""
        dialog = EditProject(old_name=project.name)  # Передаём старое имя

        # Заполняем поля текущими значениями проекта
        dialog.le_name.setText(project.name)
        dialog.le_goal.setText(str(project.goal))
        dialog.le_total_symbols.setText(str(project.total_symbols))

        # Настраиваем дедлайн
        if project.deadline != 'Нет':
            dialog.checkBox.setChecked(False)
            # Преобразуем date в QDate
            from PySide6.QtCore import QDate
            qdate = QDate(project.deadline.year, project.deadline.month, project.deadline.day)
            dialog.de_deadline.setDate(qdate)
        else:
            dialog.checkBox.setChecked(True)
            dialog.de_deadline.setDisabled(True)

        result = dialog.exec_()

        if result == QDialog.Accepted:
            print("Диалог редактирования закрыт по OK")

            # Получаем новые значения
            name = dialog.le_name.text()
            goal = int(dialog.le_goal.text())
            total = int(dialog.le_total_symbols.text())

            if dialog.checkBox.isChecked():
                deadline = 'Нет'
            else:
                qdate = dialog.de_deadline.date()
                deadline = qdate.toPython()

            # Обновляем проект
            project.name = name
            project.goal = goal
            project.total_symbols = total
            project.deadline = deadline

            # Сохраняем изменения
            en.save_project(project)

            self.refresh_projects()
            # Восстанавливаем выделение проекта
            self.select_project_by_name(project.name)

    def complete_project(self, project):
        """Завершает проект"""
        project.status = "завершен"
        project.complete_date = en.today_for_test()

        data = en.load_data()
        en.save_data(data)

        self.refresh_projects()
        self.project_info.setVisible(False)
        self.note_widget.setVisible(False)
        self.change_project_widget.setVisible(False)

    def archive_project(self, project):
        """Отправляет проект в архив"""
        dialog = ConfirmDialog()
        dialog.message.setText('Вы хотите архивировать проект?\nДедлайн проекта будет удален,\nпроект можно будет восстановить')
        result = dialog.exec_()
        dialog.show()
        if result == QDialog.Accepted:

            project.status = "в архиве"
            project.deadline = 'Нет'
            data = en.load_data()
            en.save_data(data)

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)

    def delete_project(self, project):
        """Удаляет проект"""
        dialog = ConfirmDialog()
        dialog.message.setText('Вы хотите удалить проект?\nЭто действие нельзя отменить!')
        result = dialog.exec_()
        dialog.show()
        if result == QDialog.Accepted:
            data = en.load_data()
            data['projects'] = [p for p in data['projects'] if p.name != project.name]
            en.save_data(data)

            self.refresh_projects()
            self.project_info.setVisible(False)
            self.note_widget.setVisible(False)
            self.change_project_widget.setVisible(False)

    def generate_project_widget(self, project):
        return ProjectWidget(project)

    def refresh_projects(self):
        data = en.load_data()
        projects = data['projects']
        list_p = self.list_projects
        list_p.clear()
        for project in projects:
            widget = self.generate_project_widget(project)
            item = QListWidgetItem()

            # !!! ВАЖНО: устанавливаем размер элемента на основе виджета
            item.setSizeHint(QSize(200, 200))

            list_p.addItem(item)
            list_p.setItemWidget(item, widget)


class ProjectWidget(QWidget, project_form_ui):
    def __init__(self, project):
        super().__init__()
        self.setupUi(self)

        self.name.setText(project.name)
        self.progressBar.setValue(project.progress)
        self.symbols.setText(f'{project.total_symbols}/{project.goal}')
        if project.deadline_str != 'Нет':
            self.deadline.setText(f'Дедлайн: {project.deadline_str}')
            self.streak.setText(f'Стрик: {len(project.streaks)} д.')
            self.streak_status.setText(f'{project.get_streak_status_msg('min')}')
        else:
            self.deadline.setVisible(False)
            self.streak.setVisible(False)
            self.streak_status.setVisible(False)
        self.project = project

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
        self.checkBox.toggled.connect(self.all_data_ok)  # ДОБАВИТЬ!

        # Подключаем сигнал изменения даты
        self.de_deadline.dateChanged.connect(self.all_data_ok)  # ДОБАВИТЬ!

        # Подключаем сигналы изменения текста
        self.le_name.textChanged.connect(self.all_data_ok)
        self.le_goal.textChanged.connect(self.all_data_ok)
        self.le_total_symbols.textChanged.connect(self.all_data_ok)

        # Устанавливаем начальное состояние
        self.buttons.setDisabled(True)
        self.on_checkbox_toggled(self.checkBox.isChecked())

        # ВЫЗЫВАЕМ ПРОВЕРКУ ПОСЛЕ ТОГО, КАК ВСЕ ПОДКЛЮЧЕНО
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
        # Получаем список существующих проектов
        existing_names = [p.name for p in en.load_data()['projects']]

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
        if buttons_enabled:
            self.buttons.setEnabled(True)
        else:
            self.buttons.setEnabled(False)
            self.incorrect_data.setVisible(True)


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
        # Получаем список существующих проектов
        existing_names = [p.name for p in en.load_data()['projects']]

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

if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = QTranslator()
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if translator.load("qt_ru", translations_path):
        app.installTranslator(translator)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())