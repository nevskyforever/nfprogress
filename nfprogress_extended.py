"""
NFProgress Extended UI - Расширенная версия приложения с вкладками и статистикой
"""

from nfprogress_main import NFProgressApp, AddTaskDialog, ProgressTask
from nfprogress_advanced import ProgressAnalytics, TaskFilter, TaskExporter, TaskValidator

from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDateEdit, QComboBox, QLineEdit, QHeaderView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PyQt6.QtGui import QColor
import sys


class StatisticsTab(QWidget):
    """Вкладка со статистикой"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Основные показатели
        stats_layout = QHBoxLayout()
        
        self.total_label = QLabel("Всего задач: 0")
        self.completed_label = QLabel("Завершено: 0")
        self.progress_label = QLabel("Средний прогресс: 0%")
        self.completion_rate_label = QLabel("Завершённость: 0%")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.completed_label)
        stats_layout.addWidget(self.progress_label)
        stats_layout.addWidget(self.completion_rate_label)
        
        layout.addLayout(stats_layout)
        
        # Диаграмма
        layout.addWidget(QLabel("Статистика по категориям"))
        self.chart_view = QChartView()
        layout.addWidget(self.chart_view)
        
        # Таблица статистики
        layout.addWidget(QLabel("Задачи по категориям"))
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(["Категория", "Количество", "Завершено"])
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.stats_table)
        
        self.setLayout(layout)

    def update_statistics(self, tasks):
        """Обновить статистику"""
        analytics = ProgressAnalytics(tasks)
        stats = analytics.get_statistics()
        
        self.total_label.setText(f"Всего задач: {stats.total_tasks}")
        self.completed_label.setText(f"Завершено: {stats.completed_tasks}")
        self.progress_label.setText(f"Средний прогресс: {stats.average_progress:.1f}%")
        self.completion_rate_label.setText(f"Завершённость: {stats.completion_rate:.1f}%")
        
        # Обновить таблицу
        self.stats_table.setRowCount(len(stats.tasks_by_category))
        
        completed_by_cat = {}
        for task in tasks:
            if task.completed:
                cat = task.category
                completed_by_cat[cat] = completed_by_cat.get(cat, 0) + 1
        
        for row, (category, count) in enumerate(stats.tasks_by_category.items()):
            self.stats_table.setItem(row, 0, QTableWidgetItem(category))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(count)))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(completed_by_cat.get(category, 0))))
        
        # Диаграмма
        self.update_chart(stats)

    def update_chart(self, stats):
        """Обновить диаграмму"""
        set0 = QBarSet("Количество")
        set0.setColor(QColor(52, 211, 153))
        
        categories = []
        for category, count in stats.tasks_by_category.items():
            set0.append(count)
            categories.append(category)
        
        series = QBarSeries()
        series.append(set0)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Задачи по категориям")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        axisX = QBarCategoryAxis()
        axisX.append(categories)
        chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axisX)
        
        axisY = QValueAxis()
        chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axisY)
        
        self.chart_view.setChart(chart)


class FilterTab(QWidget):
    """Вкладка с фильтрацией"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Фильтры
        filter_layout = QHBoxLayout()
        
        layout.addWidget(QLabel("Фильтры"))
        
        # По категории
        filter_layout.addWidget(QLabel("Категория:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("Все")
        self.category_filter.addItems(["General", "Work", "Personal", "Study", "Other"])
        self.category_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.category_filter)
        
        # По статусу
        filter_layout.addWidget(QLabel("Статус:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Все", "Завершено", "В процессе"])
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.status_filter)
        
        # Поиск
        filter_layout.addWidget(QLabel("Поиск:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Найти задачу...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_input)
        
        layout.addLayout(filter_layout)
        
        # Таблица результатов
        layout.addWidget(QLabel("Результаты фильтрации"))
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Название", "Прогресс", "Категория", "Статус", "%"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.results_table)
        
        self.setLayout(layout)

    def apply_filters(self):
        """Применить фильтры"""
        category = self.category_filter.currentText()
        status = self.status_filter.currentText()
        search = self.search_input.text()
        
        task_filter = TaskFilter(self.parent_app.tasks)
        
        results = self.parent_app.tasks
        
        # По категории
        if category != "Все":
            results = task_filter.by_category(category)
        
        # По статусу
        if status == "Завершено":
            results = [t for t in results if t.completed]
        elif status == "В процессе":
            results = [t for t in results if not t.completed]
        
        # По поиску
        if search:
            results = [t for t in results if search.lower() in t.name.lower()]
        
        # Показать результаты
        self.results_table.setRowCount(len(results))
        for row, task in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(task.name))
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{task.current}/{task.total}"))
            self.results_table.setItem(row, 2, QTableWidgetItem(task.category))
            
            status_text = "✓ Завершено" if task.completed else "В процессе"
            self.results_table.setItem(row, 3, QTableWidgetItem(status_text))
            self.results_table.setItem(row, 4, QTableWidgetItem(f"{task.get_progress_percent():.1f}%"))


class NFProgressExtended(NFProgressApp):
    """Расширенная версия приложения с вкладками"""
    
    def init_ui(self):
        """Переопределить инициализацию интерфейса"""
        from PyQt6.QtWidgets import QSplitter
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # Левая панель - список задач
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        left_layout.addWidget(QLabel("Задачи"))
        
        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self.on_task_selected)
        left_layout.addWidget(self.task_list)
        
        add_btn = QPushButton("Добавить задачу")
        add_btn.clicked.connect(self.add_task)
        left_layout.addWidget(add_btn)
        
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(250)
        
        # Правая панель - вкладки
        tabs = QTabWidget()
        
        # Вкладка 1: Детали задачи
        details_widget = QWidget()
        details_layout = QVBoxLayout()
        
        self.task_name_label = QLabel("Нет выбранной задачи")
        self.task_name_label.setFont(self.task_name_label.font())
        details_layout.addWidget(self.task_name_label)
        
        self.progress_bar = ProgressBar()
        details_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("0 / 0 (0%)")
        details_layout.addWidget(self.progress_label)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        
        self.increment_spinbox = QSpinBox()
        self.increment_spinbox.setValue(10)
        control_layout.addWidget(QLabel("Шаг:"))
        control_layout.addWidget(self.increment_spinbox)
        
        increment_btn = QPushButton("Увеличить")
        increment_btn.clicked.connect(self.increment_progress)
        control_layout.addWidget(increment_btn)
        
        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self.reset_progress)
        control_layout.addWidget(reset_btn)
        
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.delete_task)
        control_layout.addWidget(delete_btn)
        
        details_layout.addLayout(control_layout)
        
        self.stats_label = QLabel("Статистика: N/A")
        details_layout.addWidget(self.stats_label)
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(6)
        self.tasks_table.setHorizontalHeaderLabels(["Название", "Прогресс", "Текущий/Всего", "Категория", "Статус", "Действия"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        details_layout.addWidget(self.tasks_table)
        
        details_widget.setLayout(details_layout)
        tabs.addTab(details_widget, "📋 Детали")
        
        # Вкладка 2: Статистика
        self.stats_tab = StatisticsTab(self)
        tabs.addTab(self.stats_tab, "📊 Статистика")
        
        # Вкладка 3: Фильтрация
        self.filter_tab = FilterTab(self)
        tabs.addTab(self.filter_tab, "🔍 Фильтры")
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        self.create_menu_bar()
        self.statusBar().showMessage("Готово")

    def on_task_selected(self, item):
        """Обработка выбора задачи"""
        super().on_task_selected(item)
        # Обновить все вкладки
        self.stats_tab.update_statistics(self.tasks)
        self.filter_tab.apply_filters()

    def refresh_table(self):
        """Переопределить для использования progressbar"""
        super().refresh_table()
        self.stats_tab.update_statistics(self.tasks)

    def add_task(self):
        """Переопределить добавление задачи"""
        super().add_task()
        self.stats_tab.update_statistics(self.tasks)


# Импортировать ProgressBar из основного приложения
from PyQt6.QtWidgets import QProgressBar

# Запуск расширенного приложения
def main():
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = NFProgressExtended()
    window.setWindowTitle("NFProgress Extended - Task Progress Tracker")
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
