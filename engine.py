import os
import pickle
import platform
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

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


def get_data_file_path():
    """Возвращает путь к файлу данных"""
    return get_app_data_dir() / 'data.pkl'


def resource_path(relative_path):
    """Получить путь к ресурсу, работает и в .py, и в .app, и в .exe"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# Версия приложения
version = '2.2.6'
last_update = '22.02.26'


def today_for_test():
    """Возвращает сегодняшнюю дату."""
    # Для тестирования можно раскомментировать:
    return date(2026, 3, 3)
    return date.today()


class Project:
    max_streak = 0
    streak_status = 'No'

    def __init__(self, name='Без имени', goal=None,
                 create_date=None, total_symbols=0, progress=0,
                 notes=None, streaks=None, max_streak=None, streak_status='No', deadline='Нет',
                 status='активен'):

        self._name = name
        self._goal = goal
        self.create_date = create_date if create_date else today_for_test()
        self.complete_date = None
        self._total_symbols = total_symbols
        self._progress = progress
        self._deadline = deadline
        self._status = status
        self.notes = notes if notes else []
        self.streaks = streaks if streaks else []
        self.max_streak = max_streak if max_streak else 0
        self.streak_status = streak_status

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        # Если имя не изменилось - пропускаем проверку
        if hasattr(self, '_name') and self._name == name:
            self._name = name
            return

        data = load_data()
        projects = data['projects']
        names = [i for i in projects.keys() if i != self]  # Исключаем текущий проект из проверки
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
            self._goal = int(goal)
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

    def get_added_symbols_today_value(self):
        today = today_for_test()
        today_added = [i.get_added_symbols() for i in self.notes if i.get_date_create() == today]
        return sum(today_added) if today_added else 0

    def get_added_symbols_today_msg(self):
        return f'📝 Написано сегодня: {self.get_added_symbols_today_value()}'

    def get_today_goal_value(self):
        """Возвращает общее количество символов, которое должно быть написано к сегодняшнему дню."""
        if self.deadline == 'Нет':
            return 0

        today = today_for_test()
        if not isinstance(self.deadline, date):
            return 0

        create_date = self.create_date
        # Приводим create_date к date, если это datetime или другой тип
        if isinstance(create_date, datetime):
            create_date = create_date.date()
        elif not isinstance(create_date, date):
            # Если create_date не дата (например, None), берём сегодня
            create_date = today

        # Общее количество дней от создания до дедлайна включительно
        total_days = (self.deadline - create_date).days + 1
        if total_days <= 0:
            # Дедлайн уже прошёл или некорректен – цель = весь проект
            return self.goal

        # Сколько дней прошло от создания до сегодня включительно
        days_passed = (today - create_date).days + 1
        if days_passed <= 0:
            days_passed = 1

        # Округление вверх, чтобы в первый день не было 0
        target = (self.goal * days_passed + total_days - 1) // total_days
        return min(target, self.goal)

    def get_today_goal_msg(self):
        value = self.get_today_goal_value()
        return f'🎯 Цель на сегодня: {self.total_symbols + value}'

    def get_need_write_value(self):
        total = self.total_symbols
        goal = self.goal
        need_write = goal - total
        return need_write

    def get_need_write_msg(self):
        value = self.get_need_write_value()
        return f'⚡️ Осталось написать: {value}'

    def get_streak_status(self):
        today = today_for_test()
        yesterday = today - timedelta(days=1)
        today_added = self.get_added_symbols_today_value()
        today_goal = self.get_today_goal_value()

        # Если цель не установлена (нет дедлайна), стрик не работает
        if today_goal == 0:
            return 'No'

        # Проверяем выполнение цели сегодня
        if today_added >= today_goal:
            if len(self.streaks) == 0:
                # Начало нового стрика
                self.streaks.append(today)
                self.streak_status = 'Start'
                return 'Start'
            elif self.streaks[-1] == today:
                # Стрик уже продлен сегодня
                self.streak_status = 'Done'
                return 'Done'
            elif self.streaks[-1] == yesterday:
                # Продление стрика
                self.streaks.append(today)
                if self.max_streak < len(self.streaks):
                    self.max_streak = len(self.streaks)
                self.streak_status = 'Go'
                return 'Go'
            else:
                # Есть разрыв в стрике - начинаем новый
                self.streaks = [today]
                self.streak_status = 'Start'
                return 'Start'
        else:
            # Цель сегодня не выполнена
            if len(self.streaks) == 0:
                # Стрик никогда не начинался, но мог быть потерян ранее
                if self.streak_status and self.streak_status.startswith('Lose'):
                    return self.streak_status  # сохраняем статус потери
                else:
                    return 'No'
            elif self.streaks[-1] == today:
                # Сегодня стрик уже был продлен ранее (редкий случай)
                self.streak_status = 'Done'
                return 'Done'
            elif self.streaks[-1] == yesterday:
                # Стрик был вчера, сегодня ещё не продлён – активен
                self.streak_status = 'Active'
                return 'Active'
            elif self.streaks[-1] < yesterday:
                # Последний стрик был раньше чем вчера – стрик потерян
                lose = len(self.streaks)
                if self.max_streak < lose:
                    self.max_streak = lose
                self.streaks = []
                self.streak_status = f'Lose {lose}'
                return f'Lose {lose}'

        return 'No'  # резервный вариант, но по логике сюда не дойдём

    def get_streak_status_msg(self, msg_type=None):
        status = self.get_streak_status()
        if status == 'Start':
            if msg_type == 'min':
                return '🔥 стрик Начат'
            return f'🔥 Стрик в {self.name} начат! Отличное начало, главное - продолжать!'
        elif status == 'Go':
            streaks = len(self.streaks)
            if msg_type == 'min':
                return '🚀 стрик продлен'
            return f'🚀 Стрик в {self.name} продлен! Вы движетесь к цели уже {streaks} дней подряд!'
        elif status == 'Done':
            if msg_type == 'min':
                return '✌️ Стрик продлен'
            return f'✌️ Стрик в {self.name} сегодня уже продлен, но символы лишними не будут'
        elif status == 'Active':  # <-- НОВЫЙ СТАТУС
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

    @property
    def progress(self):
        if self._goal and self._goal > 0:
            self._progress = self._total_symbols / self._goal * 100
        else:
            self._progress = 0
        return self._progress

    def set_new_notes(self, new_note):
        self.notes.append(new_note)


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
    data_file = get_data_file_path()
    try:
        with open(data_file, 'rb') as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError):
        # Если файл не найден, создаём пустую структуру
        return {'last': None,
                'projects': {},
                'notifications': [],
                'global_streaks': [],
                'global_streak_status': 'No',
                'max_global_streak': 0, }


def save_data(data):
    """Сохраняет данные в кроссплатформенную директорию"""
    data_file = get_data_file_path()

    # Создаём временную копию для безопасного сохранения
    temp_file = data_file.with_suffix('.tmp')
    try:
        with open(temp_file, 'wb') as f:
            pickle.dump(data, f)
        # Заменяем старый файл новым
        temp_file.replace(data_file)
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")
        # Если что-то пошло не так, удаляем временный файл
        if temp_file.exists():
            temp_file.unlink()


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
    data_file = get_data_file_path()

    return {
        'system': SYSTEM,
        'data_dir': str(data_dir),
        'data_file': str(data_file),
        'data_dir_exists': data_dir.exists(),
        'data_file_exists': data_file.exists(),
        'data_file_size': data_file.stat().st_size if data_file.exists() else 0
    }


# === МЕНЮ И ЛОГИКА ===

def find_project_by_name(name):
    """Находит проект по имени и возвращает его индекс и сам проект"""
    data = load_data()
    for i, p in enumerate(data['projects']):
        if p.name == name:
            return i, p
    return None, None


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

# При импорте модуля создаём директорию для данных
try:
    get_app_data_dir()
    print(f"Директория для данных: {get_app_data_dir()}")
    print(f"Файл данных: {get_data_file_path()}")
except Exception as e:
    print(f"Ошибка при создании директории для данных: {e}")