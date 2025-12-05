"""
NFProgress - Cross-platform Task Progress Tracker
PyQt6 application for tracking task progress with threading support
Compatible with Windows and macOS
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import threading
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QLabel, QProgressBar, QDialog,
    QDialogButtonBox, QMessageBox, QHeaderView, QTabWidget, QMenuBar,
    QMenu, QStatusBar, QSplitter, QListWidget, QListWidgetItem,
    QStyleFactory, QFileDialog, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings
from PyQt6.QtGui import QColor, QIcon, QFont, QAction
from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PyQt6.QtCore import QTimer, Qt


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

    def get_progress_percent(self) -> float:
        if self.total == 0:
            return 0
        return (self.current / self.total) * 100

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'total': self.total,
            'current': self.current,
            'category': self.category,
            'created_at': self.created_at,
            'completed': self.completed,
            'notes': self.notes
        }

    @staticmethod
    def from_dict(data: dict) -> 'ProgressTask':
        task = ProgressTask(data['name'], data['total'], data['current'], data.get('category', 'General'))
        task.id = data['id']
        task.created_at = data['created_at']
        task.completed = data['completed']
        task.notes = data.get('notes', '')
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
        self.setGeometry(100, 100, 400, 250)
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
        return {
            'name': self.name_input.text(),
            'total': self.total_input.value(),
            'category': self.category_combo.currentText(),
            'notes': self.notes_input.text()
        }


class NFProgressApp(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFProgress - Task Progress Tracker")
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
        
        right_layout.addLayout(control_layout)
        
        # Statistics
        right_layout.addWidget(QLabel("Statistics"))
        self.stats_label = QLabel("Created: N/A\nProgress: 0%\nCategory: N/A")
        right_layout.addWidget(self.stats_label)
        
        # Tasks table
        right_layout.addWidget(QLabel("All Tasks"))
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels(["Name", "Progress", "Current/Total", "Category", "Status", "Actions"])
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
        self.task_name_label.setText(task.name)
        self.progress_bar.setValue(int(task.get_progress_percent()))
        self.progress_label.setText(f"{task.current} / {task.total} ({task.get_progress_percent():.1f}%)")
        
        created_date = datetime.fromisoformat(task.created_at).strftime("%Y-%m-%d %H:%M")
        status = "Completed" if task.completed else "In Progress"
        
        self.stats_label.setText(
            f"Created: {created_date}\n"
            f"Progress: {task.get_progress_percent():.1f}%\n"
            f"Category: {task.category}\n"
            f"Status: {status}"
        )
        
        self.refresh_table()

    def increment_progress(self):
        """Increment task progress"""
        if not self.current_task:
            QMessageBox.warning(self, "Warning", "Please select a task first")
            return
        
        increment = self.increment_spinbox.value()
        self.current_task.current = min(self.current_task.current + increment, self.current_task.total)
        
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

    def refresh_task_list(self):
        """Refresh task list widget"""
        self.task_list.clear()
        for task in self.tasks:
            progress = f"{task.get_progress_percent():.0f}%"
            item = QListWidgetItem(f"{task.name} ({progress})")
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
            
            # Status
            status = "✓ Completed" if task.completed else "In Progress"
            self.tasks_table.setItem(row, 4, QTableWidgetItem(status))
            
            # Actions button
            action_btn = QPushButton("Edit")
            action_btn.clicked.connect(lambda checked, t=task: self.on_task_selected(self.task_list.item(self.tasks.index(t))))
            self.tasks_table.setCellWidget(row, 5, action_btn)

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
                f.write("Name,Progress (%),Current,Total,Category,Status\n")
                for task in self.tasks:
                    status = "Completed" if task.completed else "In Progress"
                    f.write(f"{task.name},{task.get_progress_percent():.1f},{task.current},{task.total},{task.category},{status}\n")
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
            "NFProgress v1.0\n\n"
            "A cross-platform task progress tracker\n"
            "Built with PyQt6\n\n"
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
