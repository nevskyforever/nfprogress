import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QDialog, QDialogButtonBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QEvent, Qt, QObject
from PySide6.QtWidgets import QLabel, QProgressBar
from PySide6.QtCore import QDate
from engine import load_data, Project, save_data, today_for_test


class CreateProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_ui()
        self.setup_connections()

    def load_ui(self):
        loader = QUiLoader()
        file = QFile("UI/d_create_project.ui")
        file.open(QFile.ReadOnly)
        self.ui = loader.load(file, self)
        file.close()

        # Создаем layout для диалога
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # Находим все необходимые виджеты
        self.le_name = self.ui.findChild(QWidget, 'le_name')
        self.le_goal = self.ui.findChild(QWidget, 'le_goal')
        self.le_total_symbols = self.ui.findChild(QWidget, 'le_total_symbols')
        self.de_deadline = self.ui.findChild(QWidget, 'de_deadline')
        self.checkBox = self.ui.findChild(QWidget, 'checkBox')
        self.buttons = self.ui.findChild(QWidget, 'buttons')

        # Настраиваем начальные значения
        self.le_goal.setText('1000')
        self.le_total_symbols.setText('0')

        # Устанавливаем текущую дату + 1 год по умолчанию
        today = today_for_test()
        default_date = QDate(today.year + 1, today.month, today.day)
        self.de_deadline.setDate(default_date)

    def setup_connections(self):
        # Связываем checkbox с полем выбора даты
        self.checkBox.stateChanged.connect(self.on_deadline_checkbox_changed)

        # Связываем кнопки диалога
        if self.buttons:
            self.buttons.accepted.connect(self.accept)
            self.buttons.rejected.connect(self.reject)

    def on_deadline_checkbox_changed(self, state):
        """Включает/отключает поле выбора даты в зависимости от состояния checkbox"""
        self.de_deadline.setEnabled(not state)  # Если checkbox отмечен (Нет), поле отключается

    def get_project_data(self):
        """Возвращает данные проекта из формы"""
        name = self.le_name.text() or 'Новый проект'

        try:
            goal = int(self.le_goal.text() or 1000)
        except ValueError:
            goal = 1000

        try:
            total_symbols = int(self.le_total_symbols.text() or 0)
        except ValueError:
            total_symbols = 0

        if self.checkBox.isChecked():
            deadline = 'Нет'
        else:
            qdate = self.de_deadline.date()
            deadline = qdate.toString('dd.MM.yy')

        return {
            'name': name,
            'goal': goal,
            'total_symbols': total_symbols,
            'deadline': deadline
        }


class ProjectWidget(QWidget):
    def __init__(self, project, index, controller, parent=None):
        super().__init__(parent)
        self.project = project
        self.index = index
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        # Создаем простой виджет для отображения проекта в списке
        layout = QVBoxLayout(self)

        name_label = QLabel(self.project.name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        progress_label = QLabel(f"Прогресс: {self.project.progress:.1f}%")

        layout.addWidget(name_label)
        layout.addWidget(progress_label)

        # Делаем виджет кликабельным
        self.setStyleSheet("""
            ProjectWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: #f9f9f9;
            }
            ProjectWidget:hover {
                background-color: #e9e9e9;
                border-color: #999;
            }
        """)

    def mousePressEvent(self, event):
        """Обработчик клика по виджету проекта"""
        if event.button() == Qt.LeftButton:
            self.controller.view_project(self.index)


class Controller(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.ui = window
        self.data = load_data()
        self.projects = self.data.get('projects', [])
        self.selected_project_idx = -1

        # ПОДКЛЮЧАЕМ ВИДЖЕТЫ ИЗ MAIN WINDOW
        self.setup_widgets()

        # Подключаем сигналы
        self.connect_signals()

        # Обновляем список проектов
        self.refresh_projects_list()

    def setup_widgets(self):
        """Метод для подключения всех виджетов из главного окна"""

        # Кнопки
        self.btn_create_project = self.get_widget('btns_create_filter')

        # Области прокрутки
        self.scroll_projects = self.get_widget('scroll_projects')

        # Контейнер с деталями проекта
        self.project_detail_widget = self.get_widget('project_detail_widget')

        # Если есть отдельный виджет для изменения проекта
        self.change_project_widget = self.get_widget('change_project_widget')
        if self.change_project_widget:
            self.change_project_widget.setEnabled(False)  # По умолчанию отключаем

        # Подключаем все QLabel для отображения информации о проекте
        self.name_label = self.find_child_in_detail('name')
        self.status_label = self.find_child_in_detail('status')
        self.goal_label = self.find_child_in_detail('goal')
        self.total_label = self.find_child_in_detail('total')
        self.added_today_label = self.find_child_in_detail('added_today')
        self.need_label = self.find_child_in_detail('need')
        self.deadline_label = self.find_child_in_detail('deadline')
        self.streaks_label = self.find_child_in_detail('streaks')
        self.max_streak_label = self.find_child_in_detail('max_streak')
        self.streak_status_label = self.find_child_in_detail('streak_status')
        self.last_note_label = self.find_child_in_detail('last_note_date')

        # Прогресс бар
        self.progress_bar = self.find_child_in_detail('progress')

    def get_widget(self, object_name):
        """Безопасно получает виджет по objectName"""
        widget = self.window.findChild(QWidget, object_name)
        if widget is None:
            print(f"Предупреждение: Виджет '{object_name}' не найден в главном окне")
        return widget

    def find_child_in_detail(self, object_name):
        """Ищет дочерний виджет в project_detail_widget"""
        if self.project_detail_widget:
            child = self.project_detail_widget.findChild(QLabel, object_name)
            if child is None and 'progress' in object_name:
                # Для прогресс бара используем QProgressBar
                child = self.project_detail_widget.findChild(QProgressBar, object_name)
            return child
        return None

    def connect_signals(self):
        """Подключаем сигналы к слотам"""
        if self.btn_create_project:
            self.btn_create_project.clicked.connect(self.show_create_project_dialog)

    def refresh_projects_list(self):
        """Обновляет список проектов в боковой панели"""
        # Получаем или создаем контейнер для проектов
        scroll_content = self.ui.scroll_projects.widget()
        if scroll_content is None:
            scroll_content = QWidget()
            self.ui.scroll_projects.setWidget(scroll_content)
            self.ui.scroll_projects.setWidgetResizable(True)

        # Создаем или очищаем layout
        if scroll_content.layout() is None:
            main_layout = QVBoxLayout(scroll_content)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            main_layout.addStretch()  # Добавляем растяжку в конец
        else:
            main_layout = scroll_content.layout()
            # Очищаем layout, оставляя только растяжку в конце
            while main_layout.count() > 1:
                item = main_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Добавляем проекты перед растяжкой
        for idx, project in enumerate(self.projects):
            # Создаем виджет проекта
            project_widget = ProjectWidget(project, idx, self)

            # Вставляем перед растяжкой
            main_layout.insertWidget(main_layout.count() - 1, project_widget)

    def show_create_project_dialog(self):
        """Показывает диалог создания проекта"""
        dialog = CreateProjectDialog(self.window)

        if dialog.exec() == QDialog.Accepted:
            # Получаем данные из диалога
            project_data = dialog.get_project_data()

            # Создаем новый проект
            new_project = Project(
                name=project_data['name'],
                goal=project_data['goal'],
                total_symbols=project_data['total_symbols'],
                create_date=today_for_test()
            )

            # Устанавливаем дедлайн
            new_project.deadline = project_data['deadline']

            # Добавляем проект
            self.projects.append(new_project)
            self.data['projects'] = self.projects
            save_data(self.data)

            # Обновляем отображение
            self.refresh_projects_list()

            # Если это первый проект, автоматически открываем его
            if len(self.projects) == 1:
                self.view_project(0)

    def view_project(self, selected_project_idx):
        """Отображает детали выбранного проекта"""
        if selected_project_idx < 0 or selected_project_idx >= len(self.projects):
            return

        self.selected_project_idx = selected_project_idx
        project = self.projects[selected_project_idx]

        # Находим контейнер для деталей проекта
        container = self.ui.project_detail_widget

        # Активируем виджет изменения проекта если есть
        change_widget = container.findChild(QWidget, 'change_project_widget')
        if change_widget is not None:
            change_widget.setEnabled(True)

        # Обновляем все лейблы с информацией о проекте
        name_label = container.findChild(QLabel, "name")
        if name_label:
            name_label.setText(project.name)

        status_label = container.findChild(QLabel, "status")
        if status_label:
            status_label.setText(project.status)

        goal_label = container.findChild(QLabel, "goal")
        if goal_label:
            goal_label.setText(str(project.goal))

        total_label = container.findChild(QLabel, "total")
        if total_label:
            total_label.setText(str(project.total_symbols))

        added_today_label = container.findChild(QLabel, "added_today")
        if added_today_label:
            added_today_label.setText(str(project.get_added_symbols_today_value()))

        need_label = container.findChild(QLabel, "need")
        if need_label:
            need_label.setText(str(project.get_need_write_value()))

        deadline_label = container.findChild(QLabel, "deadline")
        if deadline_label:
            deadline_label.setText(project.deadline_str)

        streaks_label = container.findChild(QLabel, "streaks")
        if streaks_label:
            streaks_label.setText(str(len(project.streaks)))

        max_streak_label = container.findChild(QLabel, "max_streak")
        if max_streak_label:
            max_streak_label.setText(str(project.max_streak))

        # Получаем статус стрика и отображаем сообщение
        streak_status = project.get_streak_status()
        streak_msg = project.get_streak_msg(streak_status, 'min')

        streak_status_label = container.findChild(QLabel, "streak_status")
        if streak_status_label:
            streak_status_label.setText(streak_msg)

        last_note_label = container.findChild(QLabel, "last_note_date")
        if last_note_label:
            if project.notes:
                last_note = project.notes[-1]
                last_note_label.setText(last_note.get_date_create_str())
            else:
                last_note_label.setText('Нет записей')

        progress_bar = container.findChild(QProgressBar, "progress")
        if progress_bar:
            progress_bar.setValue(int(project.progress))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Загружаем главное окно
    loader = QUiLoader()
    file = QFile("UI/main_window.ui")
    file.open(QFile.ReadOnly)
    window = loader.load(file)
    file.close()

    # Создаем контроллер
    controller = Controller(window)

    # Показываем окно
    window.show()

    sys.exit(app.exec())