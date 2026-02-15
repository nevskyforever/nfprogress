import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QEvent, Qt, QObject
from PySide6.QtWidgets import QLabel, QProgressBar
from engine import load_data, Project, save_data


class Controller(QObject):  # <- наследуем от QObject
    def __init__(self, window):
        super().__init__()  # <- инициализируем QObject
        self.window = window
        self.ui = window
        self.data = load_data()
        self.projects = self.data.get('projects', [])
        self.selected_project_idx = -1
        self.refresh_projects_list()

        if hasattr(self.ui, 'btn_create_project'):
            self.ui.btn_create_project.clicked.connect(self.create_project_dialog)

    def refresh_projects_list(self):
        scroll_content = self.ui.scroll_projects.widget()
        if scroll_content is None:
            scroll_content = QWidget()
            self.ui.scroll_projects.setWidget(scroll_content)

        if scroll_content.layout() is None:
            main_layout = QVBoxLayout(scroll_content)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
        else:
            main_layout = scroll_content.layout()

        while main_layout.count():
            item = main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, project in enumerate(self.projects):
            w = self.create_project_widget(project, idx)
            main_layout.addWidget(w)

    def create_project_widget(self, project, idx):
        loader = QUiLoader()
        file = QFile("project_widget.ui")
        file.open(QFile.ReadOnly)
        widget = loader.load(file, self.ui)
        file.close()

        widget.label_title.setText(project.get_name())
        progress = min(100, max(0, project.get_progress()))
        widget.progress_bar.setValue(int(progress))
        widget.label_symbols.setText(f"{project.get_total_symbols()}/{project.get_goal()}")

        widget.installEventFilter(self)
        widget.setProperty("project_idx", idx)

        return widget


    def view_project(self, selected_project_idx):
        if selected_project_idx < 0 or selected_project_idx >= len(self.projects):
            return

        project = self.projects[selected_project_idx]
        container = self.ui.project_detail_widget

        # Ищем лейблы внутри контейнера

        change_widget = container.findChild(QWidget, 'change_project_widget')
        if change_widget is not None:
            change_widget.setEnabled(True)

        name_label = container.findChild(QLabel, "name")
        if name_label:
            name_label.setText(project.get_name())

        name_status = container.findChild(QLabel, "status")
        if name_status:
            name_status.setText(project.get_status())

        goal_label = container.findChild(QLabel, "goal")
        if goal_label:
            goal_label.setText(str(project.get_goal()))

        total_label = container.findChild(QLabel, "total")
        if total_label:
            total_label.setText(str(project.get_total_symbols()))

        added_today_label = container.findChild(QLabel, "added_today")
        if added_today_label:
            added_today_label.setText(str(project.get_added_symbols_today_value()))

        need_label = container.findChild(QLabel, "need")
        if need_label:
            need_label.setText(str(project.get_need_write_value()))

        deadline_label = container.findChild(QLabel, "deadline")
        if deadline_label:
            deadline_label.setText(project.get_deadline_str())

        streaks_label = container.findChild(QLabel, "streaks")
        if streaks_label:
            streaks_label.setText(str(len(project.streaks)))

        max_streak_label = container.findChild(QLabel, "max_streak")
        if max_streak_label:
            max_streak_label.setText(str(project.max_streak))

        streak_status_label = container.findChild(QLabel, "streak_status")
        if streak_status_label:
            streak_status_label.setText(project.get_streak_msg('min'))

        last_note_label = container.findChild(QLabel, "last_note_date")
        if last_note_label:
            last_note_label.setText('В разработке')

        progress_bar = container.findChild(QProgressBar, "progress")
        if progress_bar:
            progress_bar.setValue(int(project.get_progress()))

    def create_project_dialog(self):
        loader = QUiLoader()
        file = QFile("create_project.ui")
        file.open(QFile.ReadOnly)
        dialog = loader.load(file, self.ui)
        file.close()

        def on_accepted():
            name = dialog.edit_name.text() or 'Без имени'
            try:
                goal = int(dialog.edit_goal.text() or 100)
            except ValueError:
                goal = 100
            deadline = dialog.edit_deadline.text() or 'Нет'

            new_project = Project(name=name)
            new_project.set_goal(goal)
            new_project.set_deadline(deadline)

            self.projects.append(new_project)
            self.data['projects'] = self.projects
            save_data(self.data)
            self.refresh_projects_list()
            dialog.close()

        dialog.accepted.connect(on_accepted)
        dialog.rejected.connect(dialog.close)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loader = QUiLoader()
    file = QFile("main_window.ui")
    file.open(QFile.ReadOnly)
    window = loader.load(file)
    file.close()

    controller = Controller(window)
    window.show()
    sys.exit(app.exec())
