import math
import os
import pickle
import platform
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict

from docx import Document

# Режим разработчика
dev_mode = False

# Версия приложения
version = '3.3.9'

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


def get_test_data_dir():
    """Возвращает путь к директории тестовых данных и создаёт её при необходимости."""
    test_dir = get_app_data_dir() / 'test_data'
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def cleanup_test_data():
    """Удаляет директорию тестовых данных вместе со всем содержимым."""
    import shutil
    test_dir = get_app_data_dir() / 'test_data'
    if test_dir.exists():
        shutil.rmtree(test_dir)


def get_data_file_path(name):
    """Возвращает путь к файлу данных.

    В режиме разработчика файлы читаются и пишутся из папки test_data.
    При выключении режима разработчика папка test_data удаляется.
    """
    if dev_mode:
        return get_test_data_dir() / f'{name}.pkl'
    return get_app_data_dir() / f'{name}.pkl'


def resource_path(relative_path):
    """Получить путь к ресурсу, работает и в .py, и в .app, и в .exe"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def today_for_test():
    """Возвращает сегодняшнюю дату."""
    # Для тестирования можно раскомментировать:
    if load_settings().get('today_for_test_mode', False):
        return load_settings()['today_for_test_date']
    return date.today()


class Project:
    def __init__(self, name='Без имени', goal=None,
                 create_date=None, total_symbols=0, progress=0,
                 notes=None, streaks=None, max_streak=None, streak_status='No', deadline='Нет',
                 status='активен', unit='symbols'):

        self._name = name
        self._goal = goal  # хранится в выбранной единице
        self.create_date = create_date if create_date else today_for_test()
        self.edit_date = create_date if create_date else today_for_test()
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
        self.last_streak_bonus = None
        self.last_streak_lost_date = None
        self.freezes = 0

    def migrate(self):
        """Проверяет наличие всех атрибутов и добавляет недостающие"""
        defaults = {
            '_name': 'Без имени',
            '_goal': None,
            'create_date': today_for_test(),
            'edit_date': today_for_test(),
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
            'last_streak_bonus': None,
            'last_streak_lost_date': None,
            'freezes': 0
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
        """Возвращает накопленную цель на сегодня в символах.

        Логика: уже написано + одна дневная доля от остатка.
        Это корректно работает при любом дедлайне и не зависит от даты
        создания или редактирования проекта — пересчитывается каждый день
        от текущего состояния.
        """
        if self.deadline == 'Нет':
            return 0

        today = today_for_test()
        if not isinstance(self.deadline, date):
            return 0

        goal_sym = self.get_goal_symbols()
        if goal_sym == float('inf'):
            return float('inf')

        total_sym = self.get_total_symbols()

        # Цель уже достигнута или превышена
        if total_sym >= goal_sym:
            return goal_sym

        remaining = goal_sym - total_sym

        # Количество дней до дедлайна включая сегодня
        days_left = (self.deadline - today).days + 1
        if days_left <= 0:
            # Дедлайн прошёл — весь остаток должен быть написан
            return goal_sym

        # Накопленная цель на сегодня: написано + одна дневная доля от остатка
        daily = math.ceil(remaining / days_left)
        return min(total_sym + daily, goal_sym)

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
        """Возвращает статус локального стрика проекта (статусы потери только в день потери)."""
        today = today_for_test()
        yesterday = today - timedelta(days=1)
        total = self.get_total_symbols()
        planned = self.get_today_goal_value()

        if planned == 0 or planned == float('inf'):
            return 'No'

        # Заморозка
        if self.streak_status == 'Freeze' and self.streaks and self.streaks[-1] == today:
            return 'Freeze'

        # Убедимся, что streaks — список
        if not isinstance(self.streaks, list):
            self.streaks = []

        day_completed = total >= planned

        # === СБРОС УСТАРЕВШЕГО СТАТУСА ПОТЕРИ (чистого) ===
        if (isinstance(self.streak_status, str) and
                self.streak_status.startswith('Lose ') and
                len(self.streak_status.split()) == 2 and
                self.last_streak_lost_date is not None and
                self.last_streak_lost_date < today):
            # Прошёл день потери без активности — сбрасываем
            self.streak_status = 'No'
            self.last_streak_lost_date = None

        # === НОРМАЛИЗАЦИЯ КОМБИНИРОВАННОГО СТАТУСА (только для сегодня) ===
        if (isinstance(self.streak_status, str) and
                self.streak_status.startswith('Lose ') and
                len(self.streak_status.split()) == 3):
            # Если это не сегодняшний стрик, превращаем в обычный Start
            if not (self.streaks and self.streaks[-1] == today):
                self.streak_status = 'Start'
            else:
                parts = self.streak_status.split()
                self.streak_status = parts[2]  # сохраняем базовый статус ('Start')
                return f'Lose {parts[1]} {parts[2]}'  # возвращаем комбо для сообщения

        # === ПЕРСИСТЕНЦИЯ СТАТУСА ПОТЕРИ (только в день потери) ===
        if (isinstance(self.streak_status, str) and
                self.streak_status.startswith('Lose ') and
                len(self.streak_status.split()) == 2 and
                self.last_streak_lost_date == today and
                not day_completed):
            return self.streak_status

        # Случай 1: сегодня уже есть запись в streaks (уже продлили сегодня)
        if self.streaks and self.streaks[-1] == today and day_completed:
            self.streak_status = 'Go' if len(self.streaks) > 1 else 'Start'
            self.last_streak_lost_date = None  # стрик активен, потери нет
            return self.streak_status

        # Случай 2: день выполнен
        if day_completed:
            if not self.streaks:
                # Первый день стрика
                self.streaks = [today]
                self.streak_status = 'Start'
                self.last_streak_lost_date = None
            elif self.streaks[-1] == yesterday:
                # Продолжение стрика
                self.streaks.append(today)
                self.streak_status = 'Go'
                self.last_streak_lost_date = None
            else:
                # Перерыв: потеря предыдущего + начало нового
                lose_len = len(self.streaks)
                if lose_len > self.max_streak:
                    self.max_streak = lose_len
                self.streaks = [today]
                # Комбинированный статус (потеря + старт) — устанавливаем и сразу возвращаем
                self.streak_status = f'Lose {lose_len} Start'
                self.last_streak_lost_date = None  # потеря учтена в комбо, начинаем новый стрик
                return self.streak_status
        else:
            # День не выполнен
            if not self.streaks:
                self.streak_status = 'No'
            elif self.streaks[-1] == today:
                # Уже сегодня была запись, но план не выполнен
                self.streak_status = 'Active'
            elif self.streaks[-1] == yesterday:
                # Вчера был стрик, сегодня ещё не выполнен → активный (риск потери)
                self.streak_status = 'Active'
            else:
                # Потеря стрика (пропуск >1 дня)
                lose_len = len(self.streaks)
                if lose_len > self.max_streak:
                    self.max_streak = lose_len
                self.streaks = []
                self.streak_status = f'Lose {lose_len}'
                self.last_streak_lost_date = today  # фиксируем дату потери

        # Обновляем максимальный стрик, если текущая длина больше
        if len(self.streaks) > self.max_streak:
            self.max_streak = len(self.streaks)

        return self.streak_status

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

    def get_statistic(self):
        """
        Считает и возвращает статистику по проекту в виде словаря.
        Все параметры вычисляются из существующих данных без изменения структуры.
        """

        today = today_for_test()

        # --- Вспомогательные структуры ---
        # Группируем символы по дате
        symbols_by_date = defaultdict(float)
        for note in self.notes:
            symbols_by_date[note.get_date_create()] += note.get_added_symbols()

        active_days = sorted(symbols_by_date.keys())
        total_notes = len(self.notes)
        num_active_days = len(active_days)

        # --- 1. Кол-во записей ---
        stat_notes_count = total_notes

        # --- 2. Всего написано в единице проекта ---
        stat_total_in_unit = self._total_symbols  # уже хранится в единице проекта

        # --- 3. Среднее символов в день (только по активным дням) ---
        if num_active_days > 0:
            total_sym = self.get_total_symbols()  # в символах
            stat_avg_symbols_per_active_day = round(total_sym / num_active_days)
        else:
            stat_avg_symbols_per_active_day = 0

        # --- 4. Среднее кол-во символов в записи ---
        if total_notes > 0:
            total_added = sum(note.get_added_symbols() for note in self.notes)
            stat_avg_symbols_per_note = round(total_added / total_notes)
        else:
            stat_avg_symbols_per_note = 0

        # --- 5. Среднее кол-во записей в день (по активным дням) ---
        if num_active_days > 0:
            stat_avg_notes_per_day = round(total_notes / num_active_days, 1)
        else:
            stat_avg_notes_per_day = 0

        # --- 6. Использовано заморозок ---
        stat_freezes_used = self.freezes

        # --- 7. Лучший день (максимум символов за одну дату) ---
        if symbols_by_date:
            best_date = max(symbols_by_date, key=symbols_by_date.get)
            best_value = round(symbols_by_date[best_date])
            stat_best_day = f'{best_date.strftime("%d.%m.%Y")} — {best_value} симв.'
        else:
            stat_best_day = '—'

        # --- 8. Самый продуктивный день недели ---
        DAYS_RU = {
            0: 'Понедельник', 1: 'Вторник', 2: 'Среда',
            3: 'Четверг', 4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
        }
        if symbols_by_date:
            symbols_by_weekday = defaultdict(float)
            for d, sym in symbols_by_date.items():
                symbols_by_weekday[d.weekday()] += sym
            best_weekday = max(symbols_by_weekday, key=symbols_by_weekday.get)
            stat_best_weekday = DAYS_RU[best_weekday]
        else:
            stat_best_weekday = '—'

        # --- 9. Текущий стрик (дней) ---
        stat_current_streak = len(self.streaks) if isinstance(self.streaks, list) else 0

        # --- 10. Максимальный стрик ---
        # max_streak обновляется в get_streak_status, берём максимум с текущим
        stat_max_streak = max(self.max_streak, stat_current_streak)

        # --- 11. Дней с начала проекта ---
        if self.create_date:
            stat_days_since_start = (today - self.create_date).days + 1
        else:
            stat_days_since_start = 0

        # --- 12. Активных дней (было хоть одна запись) ---
        stat_active_days_count = num_active_days

        # --- 13. Процент активных дней от общего времени проекта ---
        if stat_days_since_start > 0:
            stat_active_days_percent = round(
                stat_active_days_count / stat_days_since_start * 100, 1
            )
        else:
            stat_active_days_percent = 0

        return {
            'Кол-во записей': stat_notes_count,
            'Всего написано в единице проекта': stat_total_in_unit,
            'Среднее символов в день': stat_avg_symbols_per_active_day,
            'Среднее кол-во символов в записи': stat_avg_symbols_per_note,
            'Среднее кол-во записей в день': stat_avg_notes_per_day,
            'Использовано заморозок': stat_freezes_used,
            'Лучший день': stat_best_day,
            'Самый продуктивный день недели': stat_best_weekday,
            'Текущий стрик (дней)': stat_current_streak,
            'Максимальный стрик': stat_max_streak,
            'Дней с начала проекта': stat_days_since_start,
            'Активных дней': stat_active_days_count,
            'Процент активных дней': f'{stat_active_days_percent}%',
        }
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
            'last_global_streak_bonus': None,
            'last_global_streak_lost_date': None,
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

def global_streak_status(data, today=None):
    """Возвращает статус глобального стрика. Статусы потери возвращаются только в день потери."""
    if today is None:
        today = today_for_test()
    yesterday = today - timedelta(days=1)

    streaks = data.get('global_streaks', [])
    if not isinstance(streaks, list):
        streaks = []
        data['global_streaks'] = streaks

    max_streak = data.get('max_global_streak', 0)
    prev_status = data.get('global_streak_status', 'No')
    last_lost_date = data.get('last_global_streak_lost_date')
    last_lost_len = data.get('last_global_streak_lose_len', 0)

    # Заморозка (оставляем как есть)
    if prev_status == 'Freeze' and streaks and streaks[-1] == today:
        return 'Freeze'

    # Определяем, есть ли сегодня проекты, выполнившие план
    has_active_today = False
    projects = data.get('projects', {})
    for project in projects.values():
        if isinstance(project, Project):
            if project.get_total_symbols() >= project.get_today_goal_value() and project.get_today_goal_value() > 0:
                has_active_today = True
                break

    # === ОБРАБОТКА СОХРАНЁННОГО СТАТУСА ПОТЕРИ (только в день потери) ===
    if (isinstance(prev_status, str) and
            prev_status.startswith('Lose ') and
            len(prev_status.split()) == 2 and
            last_lost_date == today):
        # Если сегодня нет активности — оставляем статус потери
        if not has_active_today:
            return prev_status
        else:
            # Появилась активность в день потери — переходим к комбинированному статусу
            streaks = [today]
            status = f'Lose {last_lost_len} Start'
            data['global_streaks'] = streaks
            data['global_streak_status'] = status
            data['last_global_streak_lost_date'] = None
            data['last_global_streak_lose_len'] = 0
            data['max_global_streak'] = max(1, max_streak)
            save_data(data)
            return status

    # === ОБРАБОТКА КОМБИНИРОВАННОГО СТАТУСА (только в день его установки) ===
    if (isinstance(prev_status, str) and
            prev_status.startswith('Lose ') and
            len(prev_status.split()) == 3 and
            streaks and streaks[-1] == today):
        # Это комбинированный статус, установленный сегодня — возвращаем его
        return prev_status

    # Если сохранённый статус потери относится к прошлому дню, сбрасываем его в 'No'
    if (isinstance(prev_status, str) and
            prev_status.startswith('Lose ') and
            len(prev_status.split()) == 2 and
            last_lost_date is not None and
            last_lost_date < today):
        # Прошёл день потери без активности — сбрасываем в No
        data['global_streak_status'] = 'No'
        data['last_global_streak_lost_date'] = None
        data['last_global_streak_lose_len'] = 0
        save_data(data)
        prev_status = 'No'

    # === ОСНОВНАЯ ЛОГИКА РАСЧЁТА СТАТУСА ===
    if has_active_today:
        if not streaks:
            # Новый стрик
            streaks.append(today)
            if last_lost_date is not None:
                # Если была зафиксирована потеря (например, вчера), но сегодня активность — комбо
                status = f'Lose {last_lost_len} Start'
                data['last_global_streak_lost_date'] = None
                data['last_global_streak_lose_len'] = 0
            else:
                status = 'Start'
        elif streaks[-1] == yesterday:
            # Продолжение стрика
            streaks.append(today)
            status = 'Go'
            data['last_global_streak_lost_date'] = None
            data['last_global_streak_lose_len'] = 0
        elif streaks[-1] == today:
            # Уже сегодня обновляли — возвращаем текущий статус
            data['global_streaks'] = streaks
            data['max_global_streak'] = max_streak
            save_data(data)
            return prev_status
        else:
            # Пропуск дней: потеря старого стрика и начало нового
            lose_len = len(streaks)
            if lose_len > max_streak:
                max_streak = lose_len
            streaks = [today]
            status = f'Lose {lose_len} Start'
            data['last_global_streak_lost_date'] = None
            data['last_global_streak_lose_len'] = 0
    else:
        # Нет активности сегодня
        if not streaks:
            status = 'No'
        elif streaks[-1] == yesterday:
            status = 'Active'
        elif streaks[-1] == today:
            # Странная ситуация: запись в streaks сегодня есть, но активности нет — очищаем
            streaks.clear()
            status = 'No'
        else:
            # Потеря стрика из-за пропуска более одного дня
            lose_len = len(streaks)
            if lose_len > max_streak:
                max_streak = lose_len
            streaks.clear()
            status = f'Lose {lose_len}'
            data['last_global_streak_lost_date'] = today
            data['last_global_streak_lose_len'] = lose_len

    # Обновление максимальной длины стрика
    current_len = len(streaks)
    if current_len > max_streak:
        max_streak = current_len

    data['global_streaks'] = streaks
    data['max_global_streak'] = max_streak
    data['global_streak_status'] = status
    save_data(data)
    return status

def global_streak_status_msg(data, status=None):
    """Сообщение для глобального стрика по статусу."""
    if status is None:
        status = data.get('global_streak_status', 'No')

    streaks = data.get('global_streaks', [])

    if status == 'Start':
        return '🔥 Глобальный стрик начат!'
    elif status == 'Go':
        return f'🚀 Глобальный стрик продлен! Дней подряд: {len(streaks)}'
    elif status == 'Freeze':
        return f'❄️ Глобальный стрик в {len(streaks)} д. заморожен'
    elif status == 'Active':
        # Активный глобальный стрик (вчера продлен, сегодня не продлен)
        return f'👀 Глобальный стрик в {len(streaks)} д. не продлен сегодня.'
    elif isinstance(status, str) and status.startswith('Lose '):
        parts = status.split()
        if len(parts) == 2 and parts[1].isdigit():
            return f'💔 Глобальный стрик потерян! Было дней подряд: {parts[1]}'
        elif len(parts) == 3:
            # Комбинированное сообщение: потеря + новый старт
            return (f'💔 Глобальный стрик потерян! Было дней подряд: {parts[1]}'
                    f'\n🔥 Вы начали новый стрик!')
        return '💔 Глобальный стрик потерян!'
    elif status == 'No':
        # Если нет активных стриков, но были раньше
        if streaks and len(streaks) > 0:
            last_streak_day = streaks[-1]
            today = today_for_test()
            days_ago = (today - last_streak_day).days
            if days_ago == 1:
                return f'👀 Глобальный стрик в {len(streaks)} д. не продлен.'
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

# При импорте модуля: создаём нужные директории или удаляем тестовые данные
if dev_mode:
    get_test_data_dir()
else:
    get_app_data_dir()
    cleanup_test_data()