import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QListWidgetItem
from PySide6.scripts.project_lib import new_project
from PySide6.QtWidgets import QApplication, QSizePolicy
from PySide6.QtCore import QTranslator, QLibraryInfo, QSize
import engine as en
from UI_fiiles.main_window import Ui_main_window as main_window_ui
from UI_fiiles.d_create_project import Ui_d_create_project as d_create_project_ui
from UI_fiiles.project_widget import Ui_Form as project_form_ui


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
                deadline = dialog.de_deadline.date()

            total = int(dialog.le_total_symbols.text())

            new_project = en.Project(name=name, goal=goal, deadline=deadline, total_symbols=total)
            data['projects'].append(new_project)
            en.save_data(data)

            self.refresh_projects()
            dialog.close()

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
        self.deadline.setText(f'Дедлайн: {project.deadline}')
        self.streak.setText(f'стрик: {len(project.streaks)} д.')
        self.streak_status.setText(f'статус стрика: {project.get_streak_status_msg('min')}')

class CreateProject(QDialog, d_create_project_ui):
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

if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = QTranslator()
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if translator.load("qt_ru", translations_path):
        app.installTranslator(translator)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())