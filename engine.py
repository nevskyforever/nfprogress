import pickle
import random
from datetime import datetime, timedelta, date
import game

version = '2.2.6'
last_update = '22.02.26'


def today_for_test():
    """Возвращает сегодняшнюю дату."""
    dt = date(2026, 2, 3)
    dt = None
    if dt is None:
        return date.today()
    else:
        return dt

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
        data = load_data()
        projects = data['projects']
        names = [i.name for i in projects]
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
            try:
                self._deadline = datetime.strptime(deadline, '%d.%m.%y').date()
            except ValueError:
                raise ValueError('Ошибка: Неверный формат даты (нужно дд.мм.гг).')

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

        today = today_for_test()  # предполагается, что возвращает date
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
        if self.streak_status == 'Complete':
            return 'Complete'
        else:
            # Проверяем потерю стрика (последний день был давно, не вчера и не сегодня)
            if len(self.streaks) > 0 and self.streaks[-1] != yesterday and self.streaks[-1] != today:
                if self.max_streak < len(self.streaks):
                    self.max_streak = len(self.streaks)
                lose = len(self.streaks)
                self.streaks = []
                # Если цель сегодня выполнена, начинаем новый стрик
                if today_added >= today_goal:
                    self.streaks.append(today)
                    self.streak_status = 'Start'
                    return f'Lose {lose} Start'
                self.streak_status = 'Lose'
                return f'Lose {lose}'

            # Проверяем выполнение цели
            if today_added >= today_goal:
                if len(self.streaks) == 0:
                    # Начало нового стрика
                    self.streaks.append(today)
                    self.streak_status = 'Start'
                    return 'Start'
                elif self.streaks[-1] == today:
                    # Стрик уже продлен сегодня
                    return 'Done'
                elif self.streaks[-1] == yesterday:
                    # Продление стрика
                    self.streaks.append(today)
                    if self.max_streak < len(self.streaks):
                        self.max_streak = len(self.streaks)
                    self.streak_status = 'Go'
                    return 'Go'
                elif self.streaks[-1] == self.deadline:
                    # Продление стрика
                    self.streaks.append(today)
                    if self.max_streak < len(self.streaks):
                        self.max_streak = len(self.streaks)
                    self.streak_status = 'Complete'

        return 'No'

    def get_streak_status_msg(self, msg_type=None):
        status = self.get_streak_status()
        if status == 'Start':
            if msg_type == 'min':
                return '🔥 стрик Начат'
            return f'🔥 Стрик в {self.name} начат! Отличное начало, главное - продолжать!'
        elif status == 'Go':
            streaks = len(self.streaks)
            if msg_type == 'min':
                return '🚀  стрик продлен'
            return f'🚀  Стрик в {self.name} продлен! Вы движетесь к цели уже {streaks} дней подряд!'
        elif status == 'Done':
            if msg_type == 'min':
                return '✌️ Стрик продлен'
            return f'✌️  Стрик в {self.name} сегодня уже продлен, но символы лишними не будут'
        elif status == 'Complete':
            streaks = len(self.streaks)
            if msg_type == 'min':
                return '🎉  СТРИК ЗАВЕРШЕН'
            return f'🎉  СТРИК ЗАВЕРШЕН! Вы выполняли цель {streaks} дней подряд, потрясающе!'
        elif status == 'No':
            return f'🙃  Стрик не начат'
        elif status.split()[0] == 'Lose':
            status = status.split()
            if len(status) == 2:
                if msg_type == 'min':
                    return f'💔  Потеряно {status[1]} д. стрика'
                return f'💔  Стрик потерян! Вы были в цели {status[1]} дней подряд.'
            elif len(status) == 3:
                return (f'💔  Стрик потерян! Вы были в цели {status[1]} дней подряд.'
                      f'\n🔥  Вы начали новый стрик!')
        return 'Вывод статуса не работает'

    @property
    def progress(self):
        self._progress = self._total_symbols / self._goal * 100
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
    try:
        with open('data.pkl', 'rb') as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError):
        return {'last': None, 'projects': [], 'notifications': []}


def save_data(data):
    with open('data.pkl', 'wb') as f:
        pickle.dump(data, f)


# === МЕНЮ И ЛОГИКА ===

def save_project(project):
    data = load_data()
    for i, p in enumerate(data['projects']):
        if p.name == project.name:
            data['projects'][i] = project
            break
    save_data(data)

def global_streak_status(data, local_streak_status=None, today=None):
    """
    Обновляет глобальный стрик и возвращает строковый статус.
    Глобальный стрик стартует/продлевается, если локальный стрик в проекте: Start/Go/Done.
    Потеря — аналогично локальному: если последний день стрика не вчера и не сегодня.
    """
    if today is None:
        today = today_for_test()
    yesterday = today - timedelta(days=1)

    # Инициализация хранилища
    streak = data.get('global_streaks')
    if streak is None:
        streak = []
        data['global_streaks'] = streak

    status = 'No'
    max_streak = data.get('max_global_streak', 0)

    # 1) Проверка потери (аналогично твоему локальному блоку)
    if len(streak) > 0 and streak[-1] != yesterday and streak[-1] != today:
        lose = len(streak)
        data['global_streaks'] = []
        streak = data['global_streaks']
        status = f'Lose {lose}'

    # 2) Продление/старт по факту "локальный стрик продлен/уже продлен/стартовал"
    ok_statuses = {'Start', 'Go', 'Done'}
    if local_streak_status.split()[-1] in ok_statuses:
        if len(streak) == 0:
            streak.append(today)
            status = 'Start'
        elif streak[-1] == today:
            if len(streak) > max_streak:
                max_streak = len(streak)
            status = 'Done'
        elif streak[-1] == yesterday:
            if len(streak) > max_streak:
                max_streak = len(streak)
            streak.append(today)
            status = 'Go'
        else:
            # Если почему-то есть разрыв, но до потери не дошли — стартуем заново
            # (обычно сюда не попадешь, т.к. потерю обработали выше)
            streak.clear()
            streak.append(today)
            status = 'Start'

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
        # status вида "Lose 5"
        parts = status.split()
        if len(parts) == 2 and parts[1].isdigit():
            return f'💔 Глобальный стрик потерян! Было дней подряд: {parts[1]}'
        return '💔 Глобальный стрик потерян!'
    return None