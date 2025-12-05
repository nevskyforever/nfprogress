"""
РУКОВОДСТВО ПО РАЗВИТИЮ NFProgress НА PYQT6

Этот документ содержит информацию для разработчиков, расширяющих приложение NFProgress.
"""

# ============================================================================
# АРХИТЕКТУРА ПРИЛОЖЕНИЯ
# ============================================================================

"""
NFProgress состоит из 3 основных модулей:

1. nfprogress_main.py - Основное приложение
   - NFProgressApp (QMainWindow) - главное окно
   - ProgressTask - модель данных задачи
   - ProgressWorker (QThread) - рабочий поток
   - AddTaskDialog (QDialog) - диалог добавления задачи

2. nfprogress_advanced.py - Расширенные функции
   - ProgressAnalytics - анализ статистики
   - TaskFilter - фильтрация задач
   - TaskExporter - экспорт в различные форматы
   - TaskValidator - валидация данных

3. nfprogress_extended.py - Расширенный UI
   - NFProgressExtended - приложение с вкладками
   - StatisticsTab - вкладка статистики
   - FilterTab - вкладка фильтрации
"""

# ============================================================================
# МОДЕЛЬ ДАННЫХ
# ============================================================================

"""
Структура класса ProgressTask:

class ProgressTask:
    id: int                 # Уникальный идентификатор (timestamp)
    name: str              # Название задачи
    total: int             # Всего юнитов
    current: int           # Текущий прогресс
    category: str          # Категория (Work, Personal и т.д.)
    created_at: str        # Дата создания (ISO format)
    completed: bool        # Завершена ли задача
    notes: str             # Дополнительные заметки

Методы:
    - get_progress_percent() -> float       # Процент выполнения
    - to_dict() -> dict                     # Сериализация
    - from_dict(data: dict) -> ProgressTask # Десериализация
"""

# ============================================================================
# АРХИТЕКТУРА СИГНАЛОВ И СЛОТОВ
# ============================================================================

"""
PyQt6 использует сигналы и слоты для взаимодействия между компонентами:

Сигналы (signals):
    - pyqtSignal() - объявление сигнала
    - emit() - отправка сигнала

Слоты (slots):
    - Методы, запускаемые при получении сигнала
    - Связываются через .connect()

Пример:
    
    class MyWorker(QThread):
        progress_updated = pyqtSignal(int)  # Объявить сигнал
        
        def run(self):
            for i in range(100):
                self.progress_updated.emit(i)  # Отправить сигнал
    
    # В главном окне:
    worker = MyWorker()
    worker.progress_updated.connect(self.on_progress_updated)  # Связать
    
    def on_progress_updated(self, value):
        self.progress_bar.setValue(value)  # Слот
"""

# ============================================================================
# РАСШИРЕНИЕ ФУНКЦИОНАЛЬНОСТИ
# ============================================================================

# 1. ДОБАВЛЕНИЕ НОВОГО ТИПА ЭКСПОРТА
# ============================================================================

"""
Пример: Добавить экспорт в JSON Lines

# В nfprogress_advanced.py, класс TaskExporter:

@staticmethod
def to_jsonl(tasks: List, file_path: Path) -> bool:
    '''Экспортировать в JSON Lines (одна задача на строку)'''
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for task in tasks:
                f.write(json.dumps(task.to_dict()) + '\n')
        return True
    except Exception as e:
        print(f"JSONL export error: {e}")
        return False

# Использование:
exporter = TaskExporter()
exporter.to_jsonl(tasks, Path('tasks.jsonl'))
"""

# 2. ДОБАВЛЕНИЕ НОВОГО ФИЛЬТРА
# ============================================================================

"""
Пример: Фильтр по дате создания

# В nfprogress_advanced.py, класс TaskFilter:

def by_date_range(self, start_date: datetime, end_date: datetime) -> List:
    '''Фильтровать по диапазону дат'''
    return [
        t for t in self.tasks
        if start_date <= datetime.fromisoformat(t.created_at) <= end_date
    ]

# Использование:
from datetime import datetime, timedelta

task_filter = TaskFilter(tasks)
week_ago = datetime.now() - timedelta(days=7)
recent_tasks = task_filter.by_date_range(week_ago, datetime.now())
"""

# 3. ДОБАВЛЕНИЕ НОВОЙ ВКЛАДКИ
# ============================================================================

"""
Пример: Вкладка с экспортом

# Создать класс ExportTab:

class ExportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Экспорт задач"))
        
        # Кнопки экспорта
        csv_btn = QPushButton("Экспортировать в CSV")
        csv_btn.clicked.connect(lambda: self.export('csv'))
        layout.addWidget(csv_btn)
        
        json_btn = QPushButton("Экспортировать в JSON")
        json_btn.clicked.connect(lambda: self.export('json'))
        layout.addWidget(json_btn)
        
        markdown_btn = QPushButton("Экспортировать в Markdown")
        markdown_btn.clicked.connect(lambda: self.export('markdown'))
        layout.addWidget(markdown_btn)
        
        self.setLayout(layout)
    
    def export(self, format_type: str):
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            f"Export as {format_type.upper()}", 
            "", 
            f"{format_type.upper()} Files (*.{format_type})"
        )
        
        if not file_path:
            return
        
        exporter = TaskExporter()
        
        if format_type == 'csv':
            success = exporter.to_csv(self.parent_app.tasks, Path(file_path))
        elif format_type == 'json':
            success = exporter.to_json(self.parent_app.tasks, Path(file_path))
        elif format_type == 'markdown':
            success = exporter.to_markdown(self.parent_app.tasks, Path(file_path))
        
        if success:
            QMessageBox.information(self, "Success", f"Exported to {file_path}")
        else:
            QMessageBox.warning(self, "Error", "Export failed")

# В NFProgressExtended.init_ui(), добавить:
self.export_tab = ExportTab(self)
tabs.addTab(self.export_tab, "💾 Экспорт")
"""

# 4. ИНТЕГРАЦИЯ С БАЗОЙ ДАННЫХ
# ============================================================================

"""
Пример: Использование SQLite вместо JSON

import sqlite3
from pathlib import Path

class TaskDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                total INTEGER NOT NULL,
                current INTEGER NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed BOOLEAN NOT NULL,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_task(self, task: ProgressTask):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tasks 
            (id, name, total, current, category, created_at, completed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.id, task.name, task.total, task.current,
            task.category, task.created_at, task.completed, task.notes
        ))
        
        conn.commit()
        conn.close()
    
    def load_all_tasks(self) -> List[ProgressTask]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks')
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            task = ProgressTask(row[1], row[2], row[3], row[4])
            task.id = row[0]
            task.created_at = row[5]
            task.completed = row[6]
            task.notes = row[7]
            tasks.append(task)
        
        return tasks

# Использование в NFProgressApp:
self.db = TaskDatabase(Path.home() / '.nfprogress' / 'tasks.db')

def load_tasks(self):
    self.tasks = self.db.load_all_tasks()

def save_tasks(self):
    for task in self.tasks:
        self.db.save_task(task)
"""

# 5. МНОГОЯЗЫЧНАЯ ПОДДЕРЖКА
# ============================================================================

"""
Пример: Добавить поддержку английского и русского языков

# Создать файл translations.py:

TRANSLATIONS = {
    'en': {
        'tasks': 'Tasks',
        'add_task': 'Add Task',
        'statistics': 'Statistics',
        'all_tasks': 'Total tasks',
        'completed': 'Completed',
        'in_progress': 'In Progress',
    },
    'ru': {
        'tasks': 'Задачи',
        'add_task': 'Добавить задачу',
        'statistics': 'Статистика',
        'all_tasks': 'Всего задач',
        'completed': 'Завершено',
        'in_progress': 'В процессе',
    }
}

class Translator:
    def __init__(self, language: str = 'ru'):
        self.language = language
    
    def translate(self, key: str) -> str:
        return TRANSLATIONS.get(self.language, {}).get(key, key)

# Использование:
translator = Translator('ru')
print(translator.translate('tasks'))  # Выведет: Задачи
"""

# 6. АСИНХРОННЫЕ ОПЕРАЦИИ
# ============================================================================

"""
Пример: Загрузка с сервера асинхронно

class DataFetcher(QThread):
    data_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            import requests
            response = requests.get(self.url)
            data = response.json()
            self.data_fetched.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))

# Использование:
fetcher = DataFetcher('https://api.example.com/tasks')
fetcher.data_fetched.connect(self.on_data_fetched)
fetcher.error_occurred.connect(self.on_error)
fetcher.start()
"""

# 7. ЮНИТ-ТЕСТЫ
# ============================================================================

"""
Пример: Тестирование функций

import unittest
from nfprogress_advanced import ProgressAnalytics, TaskFilter, TaskValidator

class TestProgressAnalytics(unittest.TestCase):
    def setUp(self):
        self.tasks = [
            ProgressTask("Task 1", 100, 50, "Work"),
            ProgressTask("Task 2", 100, 100, "Personal"),
        ]
        self.tasks[1].completed = True
        self.analytics = ProgressAnalytics(self.tasks)
    
    def test_statistics(self):
        stats = self.analytics.get_statistics()
        self.assertEqual(stats.total_tasks, 2)
        self.assertEqual(stats.completed_tasks, 1)
        self.assertEqual(stats.in_progress_tasks, 1)
    
    def test_completion_rate(self):
        stats = self.analytics.get_statistics()
        self.assertEqual(stats.completion_rate, 75.0)  # (50+100)/200 = 75%

class TestTaskFilter(unittest.TestCase):
    def setUp(self):
        self.tasks = [
            ProgressTask("Work Task", 100, 0, "Work"),
            ProgressTask("Personal Task", 100, 0, "Personal"),
        ]
        self.filter = TaskFilter(self.tasks)
    
    def test_filter_by_category(self):
        work_tasks = self.filter.by_category("Work")
        self.assertEqual(len(work_tasks), 1)
        self.assertEqual(work_tasks[0].name, "Work Task")

if __name__ == '__main__':
    unittest.main()

# Запуск тестов:
# python -m unittest tests.py
"""

# ============================================================================
# ЛУЧШИЕ ПРАКТИКИ
# ============================================================================

"""
1. КОДОВЫЙ СТИЛЬ
   - Использовать PEP 8
   - Добавлять type hints для функций
   - Документировать классы и методы docstrings

2. ПРОИЗВОДИТЕЛЬНОСТЬ
   - Использовать QThread для длительных операций
   - Не блокировать главный поток (main thread)
   - Кэшировать результаты где возможно

3. БЕЗОПАСНОСТЬ
   - Валидировать все входные данные
   - Обрабатывать исключения
   - Избегать SQL injection при использовании BD

4. ТЕСТИРОВАНИЕ
   - Писать unit tests для критических функций
   - Тестировать UI интерактивно
   - Проверять на разных ОС (Windows, macOS)

5. ДОКУМЕНТАЦИЯ
   - Комментировать сложный код
   - Обновлять README при изменениях
   - Добавлять примеры использования новых функций

6. ВЕРСИОНИРОВАНИЕ
   - Использовать semantic versioning (1.0.0)
   - Вести CHANGELOG
   - Создавать git tags для релизов
"""

# ============================================================================
# ОТЛАДКА
# ============================================================================

"""
Полезные команды для отладки:

1. Включить verbose вывод:
   python -u nfprogress_main.py

2. Использовать debugger:
   import pdb
   pdb.set_trace()  # точка остановки

3. Логирование:
   import logging
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger(__name__)
   logger.debug("Debug message")

4. Профилирование производительности:
   python -m cProfile -s cumulative nfprogress_main.py

5. Проверка памяти:
   pip install memory-profiler
   python -m memory_profiler nfprogress_main.py
"""

# ============================================================================
# ПОЛЕЗНЫЕ РЕСУРСЫ
# ============================================================================

"""
Документация:
- PyQt6: https://doc.qt.io/qt-6/
- PyQt6 Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- Qt Creator: https://www.qt.io/product/development-tools

Учебные материалы:
- Real Python: PyQt6 tutorials
- Sentdex YouTube channel: PyQt tutorials
- Qt official documentation

Сообщества:
- Stack Overflow: tag [pyqt6]
- PyQt mailing list
- GitHub Issues в этом проекте
"""

