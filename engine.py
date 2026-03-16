import os
import math
import pickle
import platform
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from docx import Document

# Определяем систему
SYSTEM = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'

def get_app_data_dir():
    """
    Возвращает путь к директории для хранения данных приложения
    в зависимости от операционной системы.
    """
    if SYSTEM == 'Windows':
        # Windows: C:\Users\<USER>\Documents\MyAppData
        base_dir = Path(os.environ.get('USERPROFILE', '')) / 'Documents'
    elif SYSTEM == 'Darwin':  # macOS
        # macOS: /Users/<USER>/Documents/MyAppData
        base_dir = Path.home() / 'Documents'
    else:  # Linux и другие
        # Linux: /home/<USER>/Documents или ~/.local/share/MyApp
        base_dir = Path.home() / 'Documents'
        # Если папки Documents нет, используем стандартную директорию для данных
        if not base_dir.exists():
            base_dir = Path.home() / '.local' / 'share'

    # Создаем папку для нашего приложения
    app_data_dir = base_dir / 'nfprogress'

    # Создаем директорию, если её нет
    try:
        app_data_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Если нет прав на запись в Documents, используем домашнюю папку
        app_data_dir = Path.home() / '.nfprogress'
        app_data_dir.mkdir(parents=True, exist_ok=True)

    return app_data_dir


def get_data_file_path(name):
    """Возвращает путь к файлу данных"""
    return get_app_data_dir() / f'{name}.pkl'


def resource_path(relative_path):
    """Получить путь к ресурсу, работает и в .py, и в .app, и в .exe"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# Версия приложения
version = '3.2'
last_update = '13.03.26'


def today_for_test():
    """Возвращает сегодняшнюю дату."""
    # Для тестирования можно раскомментировать:
    # return date(2026, 3, 4)
    return date.today()


class Project:
    def __init__(self, name='Без имени', goal=None,
                 create_date=None, total_symbols=0, progress=0,
                 notes=None, streaks=None, max_streak=None, streak_status='No', deadline='Нет',
                 status='активен', unit='symbols'):

        self._name = name
        self._goal = goal  # хранится в выбранной единице
        self.create_date = create_date if create_date else today_for_test()
        self.complete_date = None
        self._total_symbols = total_symbols  # хранится в выбранной единице
        self._progress = progress
        self._deadline = deadline
        self._status = status
        self.notes = notes if notes else []
        self.streaks = streaks if streaks else []
        self.max_streak = max_streak if max_streak else 0
        self.streak_status = streak_status
        self.unit = unit
        self.synch = None
        self.last_synch = None

    def migrate(self):
        """Проверяет наличие всех атрибутов и добавляет недостающие"""
        defaults = {
            '_name': 'Без имени',
            '_goal': None,
            'create_date': today_for_test(),
            'complete_date': None,
            '_total_symbols': 0,
            '_progress': 0,
            '_deadline': 'Нет',
            '_status': 'активен',
            'notes': [],
            'streaks': [],
            'max_streak': 0,
            'streak_status': 'No',
            'unit': 'symbols',
            'synch': None,
            'last_synch': None,
        }

        for attr, default_value in defaults.items():
            if not hasattr(self, attr):
                setattr(self, attr, default_value)
            elif attr in ('notes', 'streaks') and not isinstance(getattr(self, attr), list):
                setattr(self, attr, [])
        if self.synch is not None and isinstance(self.synch, str):
            self.synch = {'type': 'word', 'path': self.synch}

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if hasattr(self, '_name') and self._name == name:
            self._name = name
            return

        data = load_data()
        projects = data['projects']
        names = [i for i in projects.keys() if i != self]
        if name != '':
            if name in names:
                raise ValueError('Проект с таким именем уже существует!')
            else:
                self._name = name

    @property
    def goal(self):
        return self._goal

    @goal.setter
    def goal(self, goal):
        try:
            self._goal = float(goal)
        except ValueError:
            raise ValueError('Цель должна быть числом!')

    @property
    def deadline(self):
        if self._deadline != 'Нет':
            return self._deadline
        return 'Нет'

    @deadline.setter
    def deadline(self, deadline):
        if deadline == '':
            self._deadline = 'Нет'
        else:
            self._deadline = deadline

    @property
    def deadline_str(self):
        if self._deadline != 'Нет':
            return datetime.strftime(self.deadline, '%d.%m.%y')
        return 'Нет'

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def total_symbols(self):
        return self._total_symbols

    @total_symbols.setter
    def total_symbols(self, total_symbols):
        self._total_symbols = total_symbols

    def get_goal_symbols(self):
        """Возвращает цель в символах."""
        if self._goal == float('inf'):
            return float('inf')
        return unit_converter(self.unit, self._goal, 'symbols')

    def get_total_symbols(self):
        """Возвращает текущее количество в символах."""
        return unit_converter(self.unit, self._total_symbols, 'symbols')

    @property
    def progress(self):
        goal_sym = self.get_goal_symbols()
        total_sym = self.get_total_symbols()
        if goal_sym and goal_sym > 0 and goal_sym != float('inf'):
            self._progress = total_sym / goal_sym * 100
        else:
            self._progress = 0
        return self._progress

    def get_added_symbols_today_value(self):
        """Возвращает количество добавленных сегодня символов."""
        today = today_for_test()
        today_added = [i.get_added_symbols() for i in self.notes if i.get_date_create() == today]
        return sum(today_added) if today_added else 0

    def get_added_today_in_unit(self):
        """Возвращает количество добавленных сегодня в единице проекта."""
        added_sym = self.get_added_symbols_today_value()
        return unit_converter('symbols', added_sym, self.unit)

    def get_today_goal_value(self):
        """Возвращает цель на сегодня в символах."""
        if self.deadline == 'Нет':
            return 0

        today = today_for_test()
        if not isinstance(self.deadline, date):
            return 0

        create_date = self.create_date
        if isinstance(create_date, datetime):
            create_date = create_date.date()
        elif not isinstance(create_date, date):
            create_date = today

        goal_sym = self.get_goal_symbols()
        if goal_sym == float('inf'):
            return float('inf')

        total_days = (self.deadline - create_date).days + 1
        if total_days <= 0:
            return goal_sym

        days_passed = (today - create_date).days + 1
        if days_passed <= 0:
            days_passed = 1

        target = (goal_sym * days_passed + total_days - 1) // total_days
        return min(target, goal_sym)

    def get_today_goal_in_unit(self):
        """Возвращает цель на сегодня в единице проекта."""
        goal_sym = self.get_today_goal_value()
        if goal_sym == float('inf'):
            return float('inf')
        return unit_converter('symbols', goal_sym, self.unit)

    def get_need_write_value(self):
        """Возвращает остаток написать в символах."""
        goal_sym = self.get_goal_symbols()
        total_sym = self.get_total_symbols()
        if goal_sym == float('inf'):
            return float('inf')
        return goal_sym - total_sym

    def get_need_write_in_unit(self):
        """Возвращает остаток написать в единице проекта."""
        need_sym = self.get_need_write_value()
        if need_sym == float('inf'):
            return float('inf')
        return unit_converter('symbols', need_sym, self.unit)

    def get_streak_status(self):
        """Возвращает статус стрика."""
        today = today_for_test()
        yesterday = today - timedelta(days=1)
        today_added = self.get_added_symbols_today_value()
        today_goal = self.get_today_goal_value()

        if today_goal == 0 or today_goal == float('inf'):
            return 'No'

        if self.streak_status == 'Freeze' and self.streaks and self.streaks[-1] == today:
            return 'Freeze'

        if today_added >= today_goal:
            if len(self.streaks) == 0:
                self.streaks.append(today)
                self.streak_status = 'Start'
                return 'Start'
            elif self.streaks[-1] == today:
                self.streak_status = 'Done'
                return 'Done'
            elif self.streak_status == 'Freeze':
                return 'Freeze'
            elif self.streaks[-1] == yesterday:
                self.streaks.append(today)
                if self.max_streak < len(self.streaks):
                    self.max_streak = len(self.streaks)
                self.streak_status = 'Go'
                return 'Go'
            else:
                self.streaks = [today]
                self.streak_status = 'Start'
                return 'Start'
        else:
            if len(self.streaks) == 0:
                if self.streak_status and self.streak_status.startswith('Lose'):
                    return self.streak_status
                return 'No'
            elif self.streaks[-1] == today:
                self.streak_status = 'Done'
                return 'Done'
            elif self.streaks[-1] == yesterday:
                self.streak_status = 'Active'
                return 'Active'
            elif self.streaks[-1] < yesterday:
                lose = len(self.streaks)
                if self.max_streak < lose:
                    self.max_streak = lose
                self.streaks = []
                self.streak_status = f'Lose {lose}'
                return f'Lose {lose}'

        return 'No'

    def get_streak_status_msg(self, msg_type=None):
        """Возвращает сообщение о статусе стрика."""
        status = self.get_streak_status()
        if status == 'Start':
            if msg_type == 'min':
                return '🔥 стрик Начат'
            return f'🔥 Стрик в {self.name} начат! Отличное начало, главное - продолжать!'
        elif status == 'Freeze':
            if msg_type == 'min':
                return f'❄️ Стрик заморожен'
            return f'❄️ Стрик в {self.name} заморожен'
        elif status == 'Go':
            streaks = len(self.streaks)
            if msg_type == 'min':
                return '🚀 стрик продлен'
            return f'🚀 Стрик в {self.name} продлен! Вы движетесь к цели уже {streaks} дней подряд!'
        elif status == 'Done':
            if msg_type == 'min':
                return '✌️ Стрик продлен'
            return f'✌️ Стрик в {self.name} сегодня уже продлен, но символы лишними не будут'
        elif status == 'Active':
            streaks = len(self.streaks)
            if msg_type == 'min':
                return f'⏳ Стрик в {streaks} дн не продлен'
            return f'⏳ Стрик в {self.name} активен ({streaks} дн.), но ещё не продлён сегодня'
        elif status == 'Complete':
            streaks = len(self.streaks)
            if msg_type == 'min':
                return '🎉 СТРИК ЗАВЕРШЕН'
            return f'🎉 СТРИК ЗАВЕРШЕН! Вы выполняли цель {streaks} дней подряд, потрясающе!'
        elif status == 'No':
            return f'🙃 Стрик не начат'
        elif status.split()[0] == 'Lose':
            status_parts = status.split()
            if len(status_parts) == 2:
                if msg_type == 'min':
                    return f'💔 Потеряно {status_parts[1]} д. стрика'
                return f'💔 Стрик потерян! Вы были в цели {status_parts[1]} дней подряд.'
            elif len(status_parts) == 3:
                return (f'💔 Стрик потерян! Вы были в цели {status_parts[1]} дней подряд.'
                        f'\n🔥 Вы начали новый стрик!')
        return 'Вывод статуса не работает'

    def set_new_notes(self, new_note):
        """Добавляет заметку и обновляет total_symbols в единице проекта."""
        self.notes.append(new_note)
        # new_note.new_total хранится в символах, конвертируем в единицу проекта
        self._total_symbols = unit_converter('symbols', new_note.new_total, self.unit)

class Stage(Project):
    def __init__(self):
        super().__init__()
        self.status = 'в работе'

class Note:
    new_total = 0
    added_symbols = 0
    added_progress = 0
    date_create = None

    def __init__(self, new_total, added_symbols, added_progress, date_create=None):
        if date_create is None:
            now = datetime.now()
            today = today_for_test()
            self.date_create = datetime(
                year=today.year,
                month=today.month,
                day=today.day,
                hour=now.hour,
                minute=now.minute
            )
        else:
            self.date_create = date_create

        self.new_total = new_total
        self.added_symbols = added_symbols
        self.added_progress = added_progress

    def get_new_total(self):
        return self.new_total

    def get_added_symbols(self):
        return self.added_symbols

    def get_added_progress(self):
        return self.added_progress

    def get_date_create(self):
        return self.date_create.date()

    def get_date_create_str(self):
        return self.date_create.strftime('%d.%m.%Y %H:%M')

class Notification:
    def __init__(self, text, tag=None, date_create=None, status='New'):
        self.text = text
        if date_create is None:
            now = datetime.now()
            today = today_for_test()
            self.date_create = datetime(
                year=today.year,
                month=today.month,
                day=today.day,
                hour=now.hour,
                minute=now.minute
            )
        else:
            self.date_create = date_create
        self.status = status
        self.tag = tag

    def get_date_create(self):
        return self.date_create.strftime('%H:%M %d.%m.%y')

    def get_status(self):
        return self.status

    def set_status(self, status):
        self.status = status

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text


# === ЗАГРУЗКА И СОХРАНЕНИЕ ===

def load_data():
    """Загружает данные из кроссплатформенной директории"""
    data_file = get_data_file_path('data')
    try:
        with open(data_file, 'rb') as f:
            data = pickle.load(f)

        # Миграция всех проектов - добавление недостающих атрибутов
        projects = data.get('projects', {})
        for project_name, project in projects.items():
            if isinstance(project, Project):
                # Вызываем метод миграции для каждого проекта
                project.migrate()

        return data

    except (FileNotFoundError, EOFError):
        # Если файл не найден, создаём пустую структуру
        return {
            'last': None,
            'projects': {},
            'notifications': [],
            'global_streaks': [],
            'global_streak_status': 'No',
            'max_global_streak': 0,
        }

def save_data(data):
    """Сохраняет данные в кроссплатформенную директорию"""
    data_file = get_data_file_path('data')

    # Создаём временную копию для безопасного сохранения
    temp_file = data_file.with_suffix('.tmp')
    with open(temp_file, 'wb') as f:
        pickle.dump(data, f)
    # Заменяем старый файл новым
    temp_file.replace(data_file)


def export_data_to_file(file_path):
    """Экспортирует данные в указанный файл"""
    data = load_data()
    try:
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
        return True, "Данные успешно экспортированы"
    except Exception as e:
        return False, f"Ошибка экспорта: {e}"


def import_data_from_file(file_path):
    """Импортирует данные из указанного файла"""
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        save_data(data)
        return True, "Данные успешно импортированы"
    except Exception as e:
        return False, f"Ошибка импорта: {e}"


def get_data_directory_info():
    """Возвращает информацию о директории с данными (для отладки)"""
    data_dir = get_app_data_dir()
    data_file = get_data_file_path('data')

    return {
        'system': SYSTEM,
        'data_dir': str(data_dir),
        'data_file': str(data_file),
        'data_dir_exists': data_dir.exists(),
        'data_file_exists': data_file.exists(),
        'data_file_size': data_file.stat().st_size if data_file.exists() else 0
    }

def load_settings():
    """Загружает данные из кроссплатформенной директории"""
    data_file = get_data_file_path('settings')
    try:
        with open(data_file, 'rb') as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError):
        # Если файл не найден, создаём пустую структуру
        return {
            'game_mode': False,
            'inf_project': False,
            'global_streak': False,
        }

def save_settings(data):
    """Сохраняет данные в кроссплатформенную директорию"""
    data_file = get_data_file_path('settings')

    # Создаём временную копию для безопасного сохранения
    temp_file = data_file.with_suffix('.tmp')
    with open(temp_file, 'wb') as f:
        pickle.dump(data, f)
    # Заменяем старый файл новым
    temp_file.replace(data_file)

# === МЕНЮ И ЛОГИКА ===

# def find_project_by_name(name):
#     """Находит проект по имени и возвращает его индекс и сам проект"""
#     data = load_data()
#     for i, p in enumerate(data['projects']):
#         if p.name == name:
#             return i, p
#     return None, None


def global_streak_status(data, today=None):
    """
    Обновляет глобальный стрик на основе всех активных проектов и возвращает строковый статус.
    Глобальный стрик активен, если хотя бы в одном проекте есть активный стрик.
    """
    if today is None:
        today = today_for_test()
    yesterday = today - timedelta(days=1)

    # Получаем текущие данные
    streak = data.get('global_streaks', [])
    if not isinstance(streak, list):
        streak = []
        data['global_streaks'] = streak

    prev_status = data.get('global_streak_status', 'No')  # запоминаем предыдущий статус
    status = 'No'  # статус по умолчанию для этого вызова
    max_streak = data.get('max_global_streak', 0)

    # Проверяем, есть ли хотя бы один проект с активным стриком сегодня
    has_active_streak_today = False
    projects = data.get('projects', {})

    if data['global_streak_status'] == 'Freeze' and streak and streak[-1] == today:
        return 'Freeze'
    else:
        for project_name, project in projects.items():
            if hasattr(project, 'get_streak_status'):
                project_status = project.get_streak_status()
                # Проверяем, что статус проекта указывает на активный стрик сегодня
                if project_status in ['Start', 'Go', 'Done']:
                    has_active_streak_today = True
                    break

        # 1) Проверка потери глобального стрика
        if len(streak) > 0 and streak[-1] != yesterday and streak[-1] != today:
            lose = len(streak)
            data['global_streaks'] = []   # очищаем стрик
            streak = data['global_streaks']
            status = f'Lose {lose}'        # устанавливаем статус потери

        # 2) Обновление глобального стрика на основе проектов
        if has_active_streak_today:
            if len(streak) == 0:
                streak.append(today)
                status = 'Start'
            elif streak[-1] == today:
                if len(streak) > max_streak:
                    max_streak = len(streak)
                status = 'Done'
            elif streak[-1] == yesterday:
                streak.append(today)
                if len(streak) > max_streak:
                    max_streak = len(streak)
                status = 'Go'
            else:
                # Если есть разрыв, начинаем новый стрик
                streak.clear()
                streak.append(today)
                status = 'Start'
        else:
            # Нет активных проектов сегодня
            if status == 'No' and prev_status.startswith('Lose'):
                # Сохраняем предыдущий статус потери, чтобы сообщение не исчезало сразу
                status = prev_status
            # Иначе status остаётся 'No' (если не был установлен как 'Lose' выше)

        data['max_global_streak'] = max_streak
        data['global_streak_status'] = status
        save_data(data)
        return status

def global_streak_status_msg(data, status=None):
    """Сообщение для глобального стрика по статусу."""
    if status is None:
        status = data.get('global_streak_status', 'No')

    streak = data.get('global_streaks', [])

    if status == 'Start':
        return '🔥 Глобальный стрик начат!'
    elif status == 'Go':
        return f'🚀 Глобальный стрик продлен! Дней подряд: {len(streak)}'
    elif status == 'Done':
        return '✌️ Глобальный стрик сегодня уже продлен.'
    elif status == 'Freeze':
        return '❄️ Глобальный стрик заморожен'
    elif isinstance(status, str) and status.startswith('Lose '):
        parts = status.split()
        if len(parts) == 2 and parts[1].isdigit():
            return f'💔 Глобальный стрик потерян! Было дней подряд: {parts[1]}'
        return '💔 Глобальный стрик потерян!'
    elif status == 'No':
        # Если нет активных стриков, но были раньше
        if streak and len(streak) > 0:
            last_streak_day = streak[-1]
            today = today_for_test()
            days_ago = (today - last_streak_day).days
            if days_ago == 1:
                return f'👀 Глобальный стрик в {len(streak)} д. не продлен.'
            else:
                return f'😴 Глобальный стрик не активен. Последний стрик был {days_ago} дней назад'
        else:
            return '😴 Глобальный стрик не начат'

    return '😴 Глобальный стрик не начат'

def unit_converter(unit, value, convert_to=None):
    """
    Конвертирует количество value из исходной единицы unit в целевую единицу convert_to.
    Если convert_to не указан или равен False, конвертирует в символы.

    Поддерживаемые единицы:
        'symbols'       – символы
        'A4'            – страницы A4 (1 стр. = 1800 символов)
        'author_list'   – авторские листы (1 а.л. = 40 000 символов)
        'ficbook_pages' – страницы Ficbook (1 стр. = 4500 символов)

    Возвращает:
        - для convert_to = 'symbols' – точное значение (float)
        - для остальных единиц – округлённое вверх до целого числа (int)
        - None, если единицы не поддерживаются
    """
    factors = {
        'symbols': 1,
        'A4': 1800,
        'author_list': 40000,
        'ficbook_pages': 4500
    }

    # Если целевая единица не задана – конвертируем в символы
    if convert_to in (None, False):
        convert_to = 'symbols'

    # Проверяем, что обе единицы есть в словаре
    if unit not in factors or convert_to not in factors:
        return None

    # Приводим исходное значение к символам, затем к целевой единице
    symbols_value = value * factors[unit]
    result = symbols_value / factors[convert_to]

    # Для не-символьных единиц округляем вверх до целого
    if convert_to != 'symbols':
        return math.ceil(result)
    else:
        # Для символов возвращаем точное значение (без округления)
        return result

def count_symbols_in_docx(filepath):
    """
    Возвращает общее количество символов (с пробелами) в тексте документа .docx.
    Учитываются абзацы и текст в таблицах.
    """

    doc = Document(filepath)
    total = 0
    for paragraph in doc.paragraphs:
        total += len(paragraph.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    total += len(paragraph.text)
    return total

    # Если целевая единица не задана – конвертируем в символы
    if convert_to in (None, False):
        convert_to = 'symbols'

    # Проверяем, что обе единицы есть в словаре
    if unit not in factors or convert_to not in factors:
        return None

    # Приводим исходное значение к символам, затем к целевой единице
    symbols_value = value * factors[unit]
    result = symbols_value / factors[convert_to]

    # Для не-символьных единиц округляем вверх до целого
    if convert_to != 'symbols':
        return math.ceil(result)
    else:
        # Для символов возвращаем точное значение (без округления)
        return result

# При импорте модуля создаём директорию для данных
get_app_data_dir()