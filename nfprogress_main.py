"""NFProgress - Cross-platform Task Progress Tracker
PyQt6 application for tracking task progress with threading support
Compatible with Windows and macOS
Version 0.7.0
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import threading
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QLabel, QProgressBar, QDialog,
    QDialogButtonBox, QMessageBox, QHeaderView, QTabWidget, QMenuBar,
    QMenu, QStatusBar, QSplitter, QListWidget, QListWidgetItem,
    QStyleFactory, QFileDialog, QCheckBox, QDateEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings, QDate
from PyQt6.QtGui import QColor, QIcon, QFont, QAction
from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis


class ProgressTask:
    """Data model for progress tasks"""
    def __init__(self, name: str, total: int, current: int = 0, category: str = "General"):
        self.id = int(datetime.now().timestamp() * 1000)
        self.name = name
        self.total = total
        self.current = current
        self.category = category
        self.created_at = datetime.now().isoformat()
        self.completed = current >= total
        self.notes = ""
        self.deadline = None  # Новое поле для дедлайна
        self.deadline_days = 0  # Оставшиеся дни
        self.deadline_flag = ""  # Флаг статуса дедлайна
        self.progress_entries = []  # Список записей с датами [(symbols, date), ...]

    def get_progress_percent(self) -> float:
        if self.total == 0:
            return 0
        return (self.current / self.total) * 100

    def update_deadline_status(self):
        """Обновить статус дедлайна"""
        if not self.deadline:
            self.deadline_days = 0
            self.deadline_flag = ""
            return
        
        try:
            deadline_date = datetime.fromisoformat(self.deadline)
            delta = (deadline_date - datetime.now()).days
            
            if delta > 0:
                self.deadline_days = delta
                self.deadline_flag = "ВРЕМЯ ЕСТЬ"
            else:
                self.deadline_days = abs(delta)
                self.deadline_flag = "ПРОСРОЧЕН!"
        except:
            self.deadline_days = 0
            self.deadline_flag = ""

    def get_average_symbols_per_entry(self) -> int:
        """Получить среднее количество символов в записи"""
        if not self.progress_entries:
            return 0
        total = sum(entry[0] for entry in self.progress_entries)
        return int(total / len(self.progress_entries))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'total': self.total,
            'current': self.current,
            'category': self.category,
            'created_at': self.created_at,
            'completed': self.completed,
            'notes': self.notes,
            'deadline': self.deadline,
            'deadline_days': self.deadline_days,
            'deadline_flag': self.deadline_flag,
            'progress_entries': self.progress_entries
        }

    @staticmethod
    def from_dict(data: dict) -> 'ProgressTask':
        task = ProgressTask(data['name'], data['total'], data['current'], data.get('category', 'General'))
        task.id = data['id']
        task.created_at = data['created_at']
        task.completed = data['completed']
        task.notes = data.get('notes', '')
        task.deadline = data.get('deadline')
        task.deadline_days = data.get('deadline_days', 0)
        task.deadline_flag = data.get('deadline_flag', '')
        task.progress_entries = data.get('progress_entries', [])
        task.update_deadline_status()
        return task


class ProgressWorker(QThread):
    """Worker thread for long-running operations"""
    progress_updated = pyqtSignal(int, int)
    finished = pyqtSignal()

    def __init__(self, task_id: int, increment: int, delay: float = 0.5):
        super().__init__()
        self.task_id = task_id
        self.increment = increment
        self.delay = delay
        self.running = True

    def run(self):
        while self.running and self.increment > 0:
            time.sleep(self.delay)
            self.progress_updated.emit(self.task_id, self.increment)

    def stop(self):
        self.running = False


class AddTaskDialog(QDialog):
    """Dialog for adding new tasks"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Task")
        self.setGeometry(100, 100, 400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Task name
        layout.addWidget(QLabel("Task Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter task name")
        layout.addWidget(self.name_input)

        # Total units
        layout.addWidget(QLabel("Total Units:"))
        self.total_input = QSpinBox()
        self.total_input.setMinimum(1)
        self.total_input.setMaximum(10000)
        self.total_input.setValue(100)
        layout.addWidget(self.total_input)

        # Category
        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["General", "Work", "Personal", "Study", "Other"])
        layout.addWidget(self.category_combo)

        # Deadline
        layout.addWidget(QLabel("Deadline (опционально):"))
        deadline_layout = QHBoxLayout()
        
        self.deadline_days_input = QSpinBox()
        self.deadline_days_input.setMinimum(0)
        self.deadline_days_input.setMaximum(365)
        self.deadline_days_input.setSpecialValueText("Нет дедлайна")
        deadline_layout.addWidget(QLabel("Дней:"))
        deadline_layout.addWidget(self.deadline_days_input)
        
        self.deadline_date_input = QDateEdit()
        self.deadline_date_input.setCalendarPopup(True)
        self.deadline_date_input.setDate(QDate.currentDate())
        deadline_layout.addWidget(QLabel("или Дата:"))
        deadline_layout.addWidget(self.deadline_date_input)
        
        layout.addLayout(deadline_layout)

        # Notes
        layout.addWidget(QLabel("Notes:"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes")
        layout.addWidget(self.notes_input)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_task_data(self) -> dict:
        deadline = None
        if self.deadline_days_input.value() > 0:
            deadline_date = datetime.now() + timedelta(days=self.deadline_days_input.value())
            deadline = deadline_date.isoformat()
        elif self.deadline_date_input.date() != QDate.currentDate():
            qdate = self.deadline_date_input.date()
            deadline_date = datetime(qdate.year(), qdate.month(), qdate.day())
            deadline = deadline_date.isoformat()
        
        return {
            'name': self.name_input.text(),
            'total': self.total_input.value(),
            'category': self.category_combo.currentText(),
            'notes': self.notes_input.text(),
            'deadline': deadline
        }


class NFProgressApp(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFProgress - Task Progress Tracker v0.7.0")
        self.setGeometry(100, 100, 1200, 700)
        
        self.tasks: List[ProgressTask] = []
        self.current_task: Optional[ProgressTask] = None
        self.workers = {}
        self.data_file = Path.home() / '.nfprogress' / 'tasks.json'
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.settings = QSettings('NFProgress', 'NFProgress')
        
        self.init_ui()
        self.load_tasks()
        self.apply_theme('dark')
        
        # Таймер для обновления статуса дедлайнов
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_all_deadlines)
        self.update_timer.start(60000)  # Каждую минуту

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Left panel - Task list
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        left_layout.addWidget(QLabel("Tasks"))
        
        # Task list
        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self.on_task_selected)
        left_layout.addWidget(self.task_list)
        
        # Add task button
        add_btn = QPushButton("Add Task")
        add_btn.clicked.connect(self.add_task)
        left_layout.addWidget(add_btn)
        
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(250)
        
        # Right panel - Task details
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Task info
        right_layout.addWidget(QLabel("Task Details"))
        
        self.task_name_label = QLabel("No task selected")
        self.task_name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        right_layout.addWidget(self.task_name_label)
        
        # Deadline info
        self.deadline_label = QLabel("Дедлайн: Нет")
        self.deadline_label.setFont(QFont("Arial", 10))
        right_layout.addWidget(self.deadline_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)
        
        # Progress info
        self.progress_label = QLabel("0 / 0 (0%)")
        right_layout.addWidget(self.progress_label)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.increment_spinbox = QSpinBox()
        self.increment_spinbox.setMinimum(1)
        self.increment_spinbox.setMaximum(1000)
        self.increment_spinbox.setValue(10)
        self.increment_spinbox.setMaximumWidth(80)
        control_layout.addWidget(QLabel("Increment:"))
        control_layout.addWidget(self.increment_spinbox)
        
        increment_btn = QPushButton("Increment")
        increment_btn.clicked.connect(self.increment_progress)
        control_layout.addWidget(increment_btn)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_progress)
        control_layout.addWidget(reset_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_task)
        control_layout.addWidget(delete_btn)
        
        edit_deadline_btn = QPushButton("Edit Deadline")
        edit_deadline_btn.clicked.connect(self.edit_deadline)
        control_layout.addWidget(edit_deadline_btn)
        
        right_layout.addLayout(control_layout)
        
        # Statistics
        right_layout.addWidget(QLabel("Statistics"))
        self.stats_label = QLabel("Created: N/A\nProgress: 0%\nCategory: N/A")
        right_layout.addWidget(self.stats_label)
        
        # Progress entries
        right_layout.addWidget(QLabel("Progress Entries"))
        self.entries_list = QListWidget()
        self.entries_list.setMaximumHeight(150)
        right_layout.addWidget(self.entries_list)
        
        # Tasks table
        right_layout.addWidget(QLabel("All Tasks"))
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(7)
        self.tasks_table.setHorizontalHeaderLabels(["Name", "Progress", "Current/Total", "Category", "Deadline", "Status", "Actions"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.tasks_table)
        
        right_widget.setLayout(right_layout)
        
        # Add splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Menu bar
        self.create_menu_bar()
        
        # Status bar
        self.statusBar().showMessage("Ready")

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Task", self)
        new_action.triggered.connect(self.add_task)
        file_menu.addAction(new_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_tasks)
        file_menu.addAction(save_action)
        
        load_action = QAction("Load", self)
        load_action.triggered.connect(self.load_tasks)
        file_menu.addAction(load_action)
        
        export_action = QAction("Export to CSV", self)
        export_action.triggered.connect(self.export_to_csv)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        dark_theme_action = QAction("Dark Theme", self)
        dark_theme_action.triggered.connect(lambda: self.apply_theme('dark'))
        view_menu.addAction(dark_theme_action)
        
        light_theme_action = QAction("Light Theme", self)
        light_theme_action.triggered.connect(lambda: self.apply_theme('light'))
        view_menu.addAction(light_theme_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def add_task(self):
        """Add new task"""
        dialog = AddTaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_task_data()
            task = ProgressTask(data['name'], data['total'], 0, data['category'])
            task.notes = data['notes']
            task.deadline = data['deadline']
            task.update_deadline_status()
            self.tasks.append(task)
            self.refresh_task_list()
            self.save_tasks()
            self.statusBar().showMessage(f"Task '{data['name']}' created")

    def on_task_selected(self, item):
        """Handle task selection from list"""
        for i, task in enumerate(self.tasks):
            if self.task_list.item(i) == item:
                self.current_task = task
                self.update_task_details()
                break

    def update_task_details(self):
        """Update task details panel"""
        if not self.current_task:
            return
        
        task = self.current_task
        task.update_deadline_status()
        
        self.task_name_label.setText(task.name)
        
        # Deadline info
        if task.deadline:
            deadline_date = datetime.fromisoformat(task.deadline).strftime("%d.%m.%y")
            if task.deadline_flag == "ВРЕМЯ ЕСТЬ":
                self.deadline_label.setText(f"Дедлайн: {deadline_date} - осталось {task.deadline_days} дней")
            else:
                self.deadline_label.setText(f"Дедлайн: {deadline_date} - {task.deadline_flag}")
        else:
            self.deadline_label.setText("Дедлайн: Нет")
        
        self.progress_bar.setValue(int(task.get_progress_percent()))
        self.progress_label.setText(f"{task.current} / {task.total} ({task.get_progress_percent():.1f}%)")
        
        created_date = datetime.fromisoformat(task.created_at).strftime("%d.%m.%y %H:%M")
        status = "Completed" if task.completed else "In Progress"
        
        avg_symbols = task.get_average_symbols_per_entry() if task.progress_entries else 0
        entries_count = len(task.progress_entries)
        
        self.stats_label.setText(
            f"Created: {created_date}\n"
            f"Progress: {task.get_progress_percent():.1f}%\n"
            f"Category: {task.category}\n"
            f"Status: {status}\n"
            f"Entries: {entries_count}\n"
            f"Avg symbols per entry: {avg_symbols}"
        )
        
        # Update entries list
        self.entries_list.clear()
        for i, entry in enumerate(task.progress_entries, 1):
            self.entries_list.addItem(f"{i}. {entry[1]}: {entry[0]} symbols")
        
        self.refresh_table()

    def increment_progress(self):
        """Increment task progress"""
        if not self.current_task:
            QMessageBox.warning(self, "Warning", "Please select a task first")
            return
        
        increment = self.increment_spinbox.value()
        self.current_task.current = min(self.current_task.current + increment, self.current_task.total)
        
        # Add progress entry with timestamp
        timestamp = datetime.now().strftime('%d.%m.%y %H:%M')
        self.current_task.progress_entries.append([increment, timestamp])
        
        if self.current_task.current >= self.current_task.total:
            self.current_task.completed = True
            QMessageBox.information(self, "Completed", f"Task '{self.current_task.name}' completed!")
        
        self.update_task_details()
        self.save_tasks()
        self.statusBar().showMessage(f"Progress updated: {self.current_task.current}/{self.current_task.total}")

    def reset_progress(self):
        """Reset task progress"""
        if not self.current_task:
            return
        
        reply = QMessageBox.question(self, "Confirm", "Reset progress to 0?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.current_task.current = 0
            self.current_task.completed = False
            self.current_task.progress_entries.clear()
            self.update_task_details()
            self.save_tasks()

    def delete_task(self):
        """Delete current task"""
        if not self.current_task:
            return
        
        reply = QMessageBox.question(self, "Confirm", f"Delete task '{self.current_task.name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.tasks.remove(self.current_task)
            self.current_task = None
            self.refresh_task_list()
            self.save_tasks()

    def edit_deadline(self):
        """Edit task deadline"""
        if not self.current_task:
            QMessageBox.warning(self, "Warning", "Please select a task first")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Deadline")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Set new deadline:"))
        
        days_input = QSpinBox()
        days_input.setMinimum(0)
        days_input.setMaximum(365)
        days_input.setSpecialValueText("Удалить дедлайн")
        layout.addWidget(QLabel("Дней от сегодня:"))
        layout.addWidget(days_input)
        
        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(QDate.currentDate())
        layout.addWidget(QLabel("Или выберите дату:"))
        layout.addWidget(date_input)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if days_input.value() == 0:
                self.current_task.deadline = None
            elif days_input.value() > 0:
                deadline_date = datetime.now() + timedelta(days=days_input.value())
                self.current_task.deadline = deadline_date.isoformat()
            else:
                qdate = date_input.date()
                deadline_date = datetime(qdate.year(), qdate.month(), qdate.day())
                self.current_task.deadline = deadline_date.isoformat()
            
            self.current_task.update_deadline_status()
            self.update_task_details()
            self.save_tasks()
            self.statusBar().showMessage("Deadline updated")

    def update_all_deadlines(self):
        """Update deadline status for all tasks"""
        for task in self.tasks:
            task.update_deadline_status()
        if self.current_task:
            self.update_task_details()
        self.refresh_task_list()
        self.refresh_table()

    def refresh_task_list(self):
        """Refresh task list widget"""
        self.task_list.clear()
        for task in self.tasks:
            progress = f"{task.get_progress_percent():.0f}%"
            deadline_info = ""
            if task.deadline:
                if task.deadline_flag == "ПРОСРОЧЕН!":
                    deadline_info = " ⚠️"
                else:
                    deadline_info = f" ({task.deadline_days}d)"
            item = QListWidgetItem(f"{task.name} ({progress}){deadline_info}")
            self.task_list.addItem(item)

    def refresh_table(self):
        """Refresh tasks table"""
        self.tasks_table.setRowCount(len(self.tasks))
        
        for row, task in enumerate(self.tasks):
            # Name
            self.tasks_table.setItem(row, 0, QTableWidgetItem(task.name))
            
            # Progress bar
            progress_item = QTableWidgetItem(f"{task.get_progress_percent():.1f}%")
            self.tasks_table.setItem(row, 1, progress_item)
            
            # Current/Total
            self.tasks_table.setItem(row, 2, QTableWidgetItem(f"{task.current}/{task.total}"))
            
            # Category
            self.tasks_table.setItem(row, 3, QTableWidgetItem(task.category))
            
            # Deadline
            if task.deadline:
                deadline_date = datetime.fromisoformat(task.deadline).strftime("%d.%m.%y")
                deadline_text = f"{deadline_date} - {task.deadline_flag}"
            else:
                deadline_text = "Нет"
            self.tasks_table.setItem(row, 4, QTableWidgetItem(deadline_text))
            
            # Status
            status = "✓ Completed" if task.completed else "In Progress"
            self.tasks_table.setItem(row, 5, QTableWidgetItem(status))
            
            # Actions button
            action_btn = QPushButton("Edit")
            action_btn.clicked.connect(lambda checked, t=task: self.on_task_selected(self.task_list.item(self.tasks.index(t))))
            self.tasks_table.setCellWidget(row, 6, action_btn)

    def save_tasks(self):
        """Save tasks to file"""
        data = [task.to_dict() for task in self.tasks]
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_tasks(self):
        """Load tasks from file"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.tasks = [ProgressTask.from_dict(item) for item in data]
                    self.update_all_deadlines()
                    self.refresh_task_list()
                    self.refresh_table()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load tasks: {e}")

    def export_to_csv(self):
        """Export tasks to CSV"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Export to CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return
        
        try:
            with open(file_path, 'w') as f:
                f.write("Name,Progress (%),Current,Total,Category,Deadline,Status,Entries\n")
                for task in self.tasks:
                    status = "Completed" if task.completed else "In Progress"
                    deadline = datetime.fromisoformat(task.deadline).strftime("%d.%m.%y") if task.deadline else "Нет"
                    entries_count = len(task.progress_entries)
                    f.write(f"{task.name},{task.get_progress_percent():.1f},{task.current},{task.total},{task.category},{deadline},{status},{entries_count}\n")
            QMessageBox.information(self, "Success", f"Tasks exported to {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Export failed: {e}")

    def apply_theme(self, theme: str):
        """Apply dark or light theme"""
        if theme == 'dark':
            self.setStyle(QStyleFactory.create('Fusion'))
            
            palette = self.palette()
            palette.setColor(palette.ColorRole.Window, QColor(30, 30, 30))
            palette.setColor(palette.ColorRole.WindowText, QColor(220, 220, 220))
            palette.setColor(palette.ColorRole.Base, QColor(45, 45, 45))
            palette.setColor(palette.ColorRole.AlternateBase, QColor(53, 53, 53))
            palette.setColor(palette.ColorRole.ToolTipBase, QColor(220, 220, 220))
            palette.setColor(palette.ColorRole.ToolTipText, QColor(30, 30, 30))
            palette.setColor(palette.ColorRole.Text, QColor(220, 220, 220))
            palette.setColor(palette.ColorRole.Button, QColor(53, 53, 53))
            palette.setColor(palette.ColorRole.ButtonText, QColor(220, 220, 220))
            palette.setColor(palette.ColorRole.Highlight, QColor(42, 130, 218))
            palette.setColor(palette.ColorRole.HighlightedText, QColor(30, 30, 30))
            
            self.setPalette(palette)
        else:
            self.setStyle(QStyleFactory.create('Fusion'))
            self.setPalette(self.style().standardPalette())

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About NFProgress",
            "NFProgress v0.7.0\n\n"
            "A cross-platform task progress tracker\n"
            "Built with PyQt6\n\n"
            "New in 0.7.0:\n"
            "- Deadline support with days/date input\n"
            "- Progress entries with timestamps\n"
            "- Average symbols per entry\n"
            "- Automatic deadline status updates\n\n"
            "Compatible with Windows and macOS"
        )

    def closeEvent(self, event):
        """Handle application close"""
        self.save_tasks()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = NFProgressApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
