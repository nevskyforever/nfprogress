# NFProgress - PyQt6 Cross-Platform Application

Полнофункциональное приложение для отслеживания прогресса задач на PyQt6 с поддержкой Windows и macOS.

## Системные требования

- **Python:** 3.8+
- **ОС:** Windows 10+, macOS 10.14+
- **RAM:** Минимум 512 MB

## Установка зависимостей

### Способ 1: Использование pip (рекомендуется)

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### Способ 2: Прямая установка

```bash
pip install PyQt6==6.7.0 PyQt6-Charts==6.7.0
```

## Запуск приложения

```bash
python nfprogress_main.py
```

## Файл requirements.txt

Если файла нет, создайте его с содержимым:

```
PyQt6==6.7.0
PyQt6-Charts==6.7.0
```

## Основные функции

### 1. Управление задачами
- ✅ Создание новых задач с произвольным количеством юнитов
- ✅ Категоризация задач (Work, Personal, Study и т.д.)
- ✅ Добавление заметок к каждой задаче
- ✅ Удаление задач

### 2. Отслеживание прогресса
- ✅ Визуальная прогресс-бар
- ✅ Процентное отображение прогресса
- ✅ Автоматическое отслеживание завершённых задач
- ✅ Пошаговое увеличение прогресса

### 3. Сохранение данных
- ✅ Автоматическое сохранение после каждого изменения
- ✅ Сохранение в JSON формате (~/.nfprogress/tasks.json)
- ✅ Восстановление данных при перезапуске
- ✅ Экспорт в CSV

### 4. Интерфейс
- ✅ Тёмная и светлая темы
- ✅ Таблица со всеми задачами
- ✅ Список задач слева
- ✅ Детальная информация о текущей задаче
- ✅ Меню и строка состояния

### 5. Кросс-платформенность
- ✅ Native внешний вид на Windows
- ✅ Native внешний вид на macOS
- ✅ Одинаковая функциональность на всех платформах

## Архитектура кода

### Классы

#### `ProgressTask`
Модель данных для задач отслеживания прогресса.

**Методы:**
- `get_progress_percent()` - получить процент выполнения
- `to_dict()` - сериализация в словарь
- `from_dict()` - десериализация из словаря

#### `ProgressWorker`
Рабочий поток для асинхронных операций (опционально).

**Сигналы:**
- `progress_updated` - обновление прогресса
- `finished` - завершение работы

#### `AddTaskDialog`
Диалоговое окно для добавления новых задач.

#### `NFProgressApp`
Главное окно приложения (QMainWindow).

**Основные методы:**
- `add_task()` - добавить новую задачу
- `increment_progress()` - увеличить прогресс
- `reset_progress()` - сбросить прогресс
- `delete_task()` - удалить задачу
- `save_tasks()` - сохранить в JSON
- `load_tasks()` - загрузить из JSON
- `export_to_csv()` - экспортировать в CSV
- `apply_theme()` - переключение темы

## Структура данных

### JSON формат (tasks.json)

```json
[
  {
    "id": 1701234567000,
    "name": "Проект A",
    "total": 100,
    "current": 45,
    "category": "Work",
    "created_at": "2024-01-15T10:30:45.123456",
    "completed": false,
    "notes": "Основной проект"
  }
]
```

## Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| `Ctrl+N` | Новая задача (через меню) |
| `Ctrl+S` | Сохранить (через меню) |
| `Ctrl+E` | Экспортировать в CSV (через меню) |

## Расширение функциональности

### Добавление нового типа диаграммы

```python
from PyQt6.QtCharts import QPieChart, QPieSeries, QPieSlice

def create_stats_chart(self):
    series = QPieSeries()
    for task in self.tasks:
        slice = QPieSlice(task.name, task.get_progress_percent())
        series.append(slice)
    
    chart = QPieChart()
    chart.addSeries(series)
    return chart
```

### Добавление экспорта в PDF

```python
from PyQt6.QtPrintSupport import QPrinter, QPdfWriter

def export_to_pdf(self):
    file_path, _ = QFileDialog.getSaveFileName(self, "Export to PDF", "", "PDF Files (*.pdf)")
    if file_path:
        # Реализация экспорта
        pass
```

## Возможные проблемы и решения

### Проблема: ImportError: No module named 'PyQt6'
**Решение:** Установите PyQt6:
```bash
pip install PyQt6==6.7.0
```

### Проблема: Data не сохраняется
**Решение:** Проверьте права доступа в папке ~/.nfprogress/

### Проблема: Приложение медленно запускается
**Решение:** Если много задач (>1000), рассмотрите оптимизацию таблицы или использование базы данных.

## Развёртывание

### Windows (создание исполняемого файла)

```bash
pip install pyinstaller

pyinstaller --onefile --windowed --icon=icon.ico nfprogress_main.py
```

Исполняемый файл будет в папке `dist/`.

### macOS (создание приложения)

```bash
pyinstaller --onefile --windowed --osx-bundle-identifier=com.nfprogress nfprogress_main.py
```

## Лицензия

MIT License

## Автор

NFProgress Team
Версия: 1.0.0
Дата: 2024

## Поддержка

Для сообщения об ошибках и предложений используйте GitHub Issues.
