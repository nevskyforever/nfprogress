import pickle
import random
from datetime import datetime, timedelta, date
import game

version = '2.1'
last_update = '11.02.26'


def today_for_test():
    """Возвращает сегодняшнюю дату."""
    dt = date(2026, 2, 4)
    # dt = None
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

        self.name = name
        self.goal = goal
        self.create_date = create_date if create_date else today_for_test()
        self.total_symbols = total_symbols
        self.progress = progress
        self.deadline = deadline
        self.status = status
        self.notes = notes if notes else []
        self.streaks = streaks if streaks else []
        self.max_streak = max_streak if max_streak else 0
        self.streak_status = streak_status

    def set_name(self, name):
        if name != '':
            self.name = name
            return 'Имя проекта изменено'
        raise ValueError('Некорректное имя проекта!')

    def get_name(self):
        return self.name

    def set_goal(self, goal):
        try:
            self.goal = int(goal)
            return f'Установлена цель в {self.goal} символов'
        except ValueError:
            raise ValueError('Цель должна быть числом!')

    def get_goal(self):
        return self.goal

    def set_deadline(self, deadline):
        if deadline == '':
            self.deadline = 'Нет'
            return None
        try:
            self.deadline = datetime.strptime(deadline, '%d.%m.%y')
            return 'Дедлайн проекта установлен.'
        except ValueError:
            return 'Ошибка: Неверный формат даты (нужно дд.мм.гг).'

    def get_deadline(self):
        if self.deadline != 'Нет':
            return self.deadline.date()
        return 'Нет'

    def get_deadline_str(self):
        if self.deadline != 'Нет':
            return datetime.strftime(self.deadline, '%d.%m.%y')
        return 'Нет'

    def set_status(self, status):
        self.status = status
        if status == 'активен':
            return '✅ Проект снова активен.'
        elif status == 'в архиве':
            self.deadline = 'Нет'
            return '🗄️ Проект архивирован. Дедлайн сброшен.'
        elif status == 'завершен':
            return '🎉 Проект завершен, поздравляем!'
        return None

    def get_status(self):
        return self.status

    def get_total_symbols(self):
        return self.total_symbols

    def set_total_symbols(self, total_symbols):
        self.total_symbols = total_symbols

    def get_added_symbols_today_value(self):
        today = today_for_test()
        today_added = [i.get_added_symbols() for i in self.notes if i.get_date_create() == today]
        return sum(today_added) if today_added else 0

    def get_added_symbols_today_msg(self):
        return f'📝 Написано сегодня: {self.get_added_symbols_today_value()}'

    def get_today_goal_value(self):
        if self.deadline == 'Нет':
            return 0

        today = today_for_test()
        if not isinstance(self.deadline, datetime):
            return 0

        days_before = (self.deadline.date() - today).days

        if days_before <= 0:
            return self.goal - self.total_symbols

        needed = self.goal - self.total_symbols
        if needed < 0: needed = 0
        return needed // days_before

    def get_today_goal_msg(self):
        value = self.get_today_goal_value()
        return f'🎯 Цель на сегодня: {self.total_symbols + value}'
    def get_need_write_value(self):
        total = self.get_total_symbols()
        goal = self.get_goal()
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

        return 'No'

    def get_streak_msg(self, status, msg_type=None):
        if status == 'Start':
            if msg_type == 'min':
                return '🔥  Начат'
            return f'🔥 Стрик в {self.get_name()} начат! Отличное начало, главное - продолжать!'
        elif status == 'Go':
            streaks = len(self.streaks)
            if msg_type == 'min':
                return '🚀 Продлен'
            return f'🚀 Стрик в {self.get_name()} продлен! Вы движетесь к цели уже {streaks} дней подряд!'
        elif status == 'Done':
            if msg_type == 'min':
                return '✌️ Продлен'
            return f'✌️ Стрик в {self.get_name()} сегодня уже продлен, но символы лишними не будут'
        elif status == 'Complete':
            streaks = len(self.streaks)
            return f'🎉 СТРИК ЗАВЕРШЕН! Вы выполняли цель {streaks} дней подряд, потрясающе!'
        elif status == 'No':
            return f'🙃  Стрик не начат'
        elif status.split()[0] == 'Lose':
            status = status.split()
            if len(status) == 2:
                return f'💔 Стрик потерян! Вы были в цели {status[1]} дней подряд.'
            elif len(status) == 3:
                return (f'💔 Стрик потерян! Вы были в цели {status[1]} дней подряд.'
                      f'\n🔥 Вы начали новый стрик!')
        return 'Вывод статуса не работает'

    def get_progress(self):
        self.progress = self.total_symbols / self.goal * 100
        return self.progress

    def set_new_notes(self, new_note):
        self.notes.append(new_note)
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
            status = 'Done'
        elif streak[-1] == yesterday:
            streak.append(today)
            status = 'Go'
        else:
            # Если почему-то есть разрыв, но до потери не дошли — стартуем заново
            # (обычно сюда не попадешь, т.к. потерю обработали выше)
            streak.clear()
            streak.append(today)
            status = 'Start'

    data['global_streak_status'] = status
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

def choice_project():
    """Выбор проекта из списка. Возвращает индекс или None."""
    data = load_data()
    projects = data.get('projects', [])

    print('\n--- ВЫБОР ПРОЕКТА ---')
    if not projects:
        print('Проектов пока нет.')
        return None

    for i, p in enumerate(projects):
        print(f'{i + 1}. {p.get_name()} - {p.get_status()}')

    while True:
        choice = input('Введите номер (или Enter для выхода): ')
        if choice == '':
            return None

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                return idx
            print('Такого номера нет.')
        else:
            print('Введите число.')


def create_project():
    data = load_data()
    notifications = data.get('notifications', [])
    projects = data.get('projects', [])
    print('\n--- СОЗДАНИЕ ПРОЕКТА ---')
    new_project = Project()

    try:
        print(new_project.set_name(input('Имя проекта: ')))
        print(new_project.set_goal(input('Цель (символы): ')))
        print(new_project.set_deadline(input('Дедлайн (дд.мм.гг) или Enter: ')))

        projects.append(new_project)
        data['projects'] = projects
        notifications.append(Notification(f'📓СОЗДАН НОВЫЙ ПРОЕКТ - "{new_project.get_name()}"', tag='Изменения'))
        save_data(data)
        print('Проект создан.')
    except ValueError as e:
        print(f'Ошибка: {e}')


def create_note(last=None):
    """Создание записи. Если передан last, выбор проекта пропускается."""
    data = load_data()
    notifications = data.get('notifications', [])
    projects = data.get('projects', [])

    # ИСПРАВЛЕНИЕ: Сначала проверяем быструю запись!
    if last is not None and last < len(projects):
        print('\n--- ⚡️ БЫСТРАЯ ЗАПИСЬ ⚡️ ---')
        choice_idx = last
    else:
        choice_idx = choice_project()

    # Если пользователь ничего не выбрал или нажал отмену
    if choice_idx is None:
        return

    project = projects[choice_idx]
    project_name = project.get_name()
    if len(project_name.split()) >= 4:
        project_name = [i[0].upper() for i in project_name.split()]
        project_name = ''.join(project_name)
    old_total = project.get_total_symbols()
    old_progress = project.get_progress()
    gamer = game.load_game()

    print(f'📓 Проект: {project.get_name()}')
    print(f'✏️ Написано в проекте: {old_total}')
    print(project.get_added_symbols_today_msg())
    print(project.get_need_write_msg())
    if project.get_deadline() != 'Нет':
        streaks = project.streaks
        today = today_for_test()
        if today not in streaks:
            print(project.get_today_goal_msg())

    raw_val = input(f'Введите НОВОЕ ОБЩЕЕ число символов: ')
    if not raw_val:
        return

    try:
        new_total = int(raw_val)
    except ValueError:
        print("🙃 Ошибка: введите число.")
        return

    added_symbols = new_total - old_total
    if added_symbols < 0: added_symbols = 0
    project.set_total_symbols(new_total)
    new_progress = project.get_progress()
    added_progress = new_progress - old_progress
    new_note = Note(new_total, added_symbols, added_progress)
    project.set_new_notes(new_note)
    note_msg = (f'✅ В проект {project_name} добавлено {added_symbols} символов и {added_progress}%.'
            f'\nОсталось написать: {project.get_need_write_value()}')
    note_msg = f'{project_name} - {note_msg}'
    notifications.append(Notification(note_msg, tag='Изменения'))
    print(note_msg)
    save_data(data)

    print(project.get_added_symbols_today_msg())

    streak_status = project.get_streak_status()
    if project.get_deadline() != 'Нет':
        print(project.get_streak_msg(streak_status))

    if gamer is not None:
        msg = gamer.give_symbol_bonus(added_symbols)
        msg = f'{project_name} - {msg}'
        print(msg)
        notifications.append(Notification(msg, tag='Игра'))
        if streak_status:
            msg = gamer.give_streak_bonus(streak_status, new_total, 'Local')
            msg = f'{project_name} - {msg}'
            print(msg)
            notifications.append(Notification(msg, tag='Стрики'))
    data['last'] = choice_idx
    gs_status = global_streak_status(data, local_streak_status=streak_status)
    gs_msg = global_streak_status_msg(data, gs_status)
    if gs_msg:
        print(gs_msg)
        notifications.append(Notification(gs_msg, tag='Стрики'))
        if gamer is not None:
            print(gamer.give_streak_bonus(gs_status, 0, 'Global'))

    save_data(data)

def change_project():
    idx = choice_project()
    if idx is None:
        return

    data = load_data()
    project = data['projects'][idx]
    notifications = data.get('notifications', [])
    status = project.get_status()

    print(f'\n⚙️ РЕДАКТИРОВАНИЕ: {project.get_name()}')
    print('1 - 📇 Изменить имя')
    print('2 - 🎯 Изменить цель')
    print('3 - 📝 Изменить счетчик символов (без опыта)')
    print('4 - 📅 Изменить дедлайн')
    print('7 - 🗑️ Удалить проект')

    if status == 'активен':
        print('5 - 🗄️ В архив')
    elif status == 'в архиве':
        print('6 - 🗃️ Вернуть из архива')

    cmd = input('Выбор (Enter - назад): ')

    try:
        if cmd == '1':
            old_name = project.get_name()
            new_name = input('Новое имя: ')
            print(project.set_name(new_name))
            msg = f'Проект {old_name} переименован в {new_name}.'
            notifications.append(Notification(msg, tag='Изменения'))
        elif cmd == '2':
            print(project.set_goal(input('Новая цель: ')))
        elif cmd == '3':
            val = int(input('Введите точное число символов: '))
            project.set_total_symbols(val)
            msg = f'🎯 В проекте {project.get_name()} новая цель - {val} символов'
            notifications.append(Notification(msg, tag='Изменения'))
            print('✅ Сохранено.')
        elif cmd == '4':
            new_deadline = input('📅 Новый дедлайн (дд.мм.гг): ')
            print(project.set_deadline(new_deadline))
            msg = f'📅 В проекте {project.get_name()} новый дедлайн - {new_deadline}'
            notifications.append(Notification(msg, tag='Изменения'))
        elif cmd == '5' and status == 'активен':
            print(project.set_status('в архиве'))
            msg = f'🗄️ Проект {project.get_name()} направлен в архив.'
            notifications.append(Notification(msg, tag='Изменения'))
        elif cmd == '6' and status == 'в архиве':
            print(project.set_status('активен'))
            msg = f'🗃️ Проекте {project.get_name()} восстановлен из архива.'
            notifications.append(Notification(msg, tag='Изменения'))
        elif cmd == '7':
            code = random.randint(1000, 9999)
            ok = input(f'🗑️ Подтвердите удаление. Введите {code}:')
            while int(ok) != code:
                ok = input(f'⛔️ КОД НЕПРАВИЛЬНЫЙ ⛔️.'
                           f'\nВВедите {code}:')
                if ok == '':
                    main_menu()
            if int(ok) == code:
                msg = f'✅ {project.get_name()} удален.'
                print(msg)
                data['projects'].remove(project)
                notifications.append(Notification(msg, tag='Изменения'))
    except ValueError as e:
        print(f"⛔️ Ошибка: {e}")

    save_data(data)


def view_project():
    data = load_data()
    projects = data.get('projects', [])

    active = [p for p in projects if p.get_status() == 'активен']
    archived = [p for p in projects if p.get_status() == 'в архиве']

    print('\n--- 📚 ПРОСМОТР ПРОЕКТОВ ---')
    if not active:
        print('Активных проектов нет.')
    else:
        for p in active:
            dl = p.get_deadline_str()
            streak = len(p.streaks)
            print(f"{p.get_name()}: {p.get_progress()}%")
            print(f"Цель/написано - {p.get_total_symbols()}/{p.get_goal()} символов")
            print(f"Дедлайн: {dl}, 🔥  текущий стрик: {streak}")
            if p.deadline != 'Нет':
                print(p.get_streak_msg(p.streak_status, 'min'))


    if archived:
        if input('\nПоказать архив? (введите "a"): ') == 'a':
            print('\n--- 🗄️АРХИВ ---')
            for p in archived:
                print(f"{p.get_name()}: прогресс - {p.get_progress()}% цель/написано - {p.get_total_symbols()}/{p.get_goal()} символов | Дедлайн: {dl}")

    input('\nНажмите Enter, чтобы вернуться в меню.')
    save_data(data)


def notifications_view():
    data = load_data()
    notifications = data.get('notifications', [])
    yesterday = today_for_test() - timedelta(days=1)
    new_notifications = [n for n in notifications if n.status == 'New']
    read_notifications = [n for n in notifications if n.status == 'Read' and n.date_create.date() >= yesterday]
    print('\n💡 НОВЫЕ УВЕДОМЛЕНИЯ\n')
    if len(new_notifications) == 0:
        print('Новых нет')
    for n in new_notifications:
        print(f'{n.get_date_create()}: {n.get_text()}')
        n.set_status('Read')
    print('\n⌛️ ПРОЧИТАННЫЕ УВЕДОМЛЕНИЯ\n')
    if len(read_notifications) == 0:
        print('Нет уведомлений')
    for n in read_notifications:
        if n.date_create.date() <= yesterday:
            read_notifications.remove(n)
        print(f'{n.get_date_create()}: {n.get_text()}')
    cmd = input('\nВведите Enter для выхода')
    if cmd == '':
        save_data(data)
        main_menu()

def project_details_view():
    print('Выберите проект для просмотра подробностей:')
    data = load_data()
    projects = data.get('projects', [])
    choice = choice_project()
    project = projects[choice]
    print('ПОДРОБНОСТИ ПРОЕКТА')
    print(f'Название: {project.get_name()}')
    print(f'Прогресс: {round((project.get_progress()), 2)}%')
    print(f'Дедлайн: {project.get_deadline_str()}')
    if project.get_deadline() != 'Нет':
        print(f'Стрик: {len(project.streaks)} д.')
        print(f'Самый длинный стрик - {project.max_streak} д.')
    print(f'Цель/написано: {project.get_goal()}/{project.get_total_symbols()} сим.')
    print(f'Всего записей: {len(project.notes)}')
    if len(project.notes) > 0:
        print(f'Последняя запись: {project.notes[-1].get_date_create_str()}')
    while True:
        input('Введите Enter для выхода: ')
        main_menu()

def main_menu():
    """Отображение меню. Возвращает управление в бесконечный цикл."""
    data = load_data()
    projects = data.get('projects', [])
    notifications = data.get('notifications', [])
    new_notifications = []
    if len(notifications) != 0:
        new_notifications = [n for n in notifications if n.status == 'New']
        new_notifications_cnt = len(new_notifications)
    else:
        new_notifications_cnt = 0
    last_idx = data.get('last')

    active_count = len([p for p in projects if p.get_status() == 'активен'])

    print(f'\nnfprogress {version}\n')
    print(f'☀️Сегодня {today_for_test().strftime("%d.%m.%y")}')
    if data.get('global_streaks', []) != []:
        streaks = len(data['global_streaks'])
        print(f'\n🔥Пишете {streaks} д. подряд')
        if data['global_streak_status'] == 'Freeze':
            print('❄️ Глобальный стрик заморожен')
        elif data['global_streaks'][-1] != today_for_test():
            print('🥺 Глобальный стрик еще не продлен!')
        else:
            print('✅ Глобальный стрик продлен')
    if len(new_notifications) > 0:
        print(f'\n📌{new_notifications[-1].get_text()}\n')
    print('1 - ✏️ Сделать запись')
    print('2 - 📓 Создать проект')
    print(f'3 - 📚 Проекты (активных: {active_count})')
    print('4 - ⚙️ Настройки проекта')
    if new_notifications_cnt > 0:
        print(f'5 - 📌 Уведомления ({new_notifications_cnt} новых)')
    else:
        print('5 - 📌 Уведомления')
    print('6 - 🧐 Подробности о проекте')

    if game.load_game():
        hero = game.load_game()
        print(f'0 - ⚔️ Герой (Lvl {hero.level}|❤️{hero.health})')
    else:
        print('0 - 🎮 Включить RPG режим')

    # Подсказка для быстрой записи
    if last_idx is not None and last_idx < len(projects):
        last_name = projects[last_idx].get_name()
        if len(last_name.split()) >= 4:
            last_name = [i[0].upper() for i in last_name.split()]
            last_name = ''.join(last_name)
        last_name_progress = projects[last_idx].get_progress()
        print(f'Enter - ⚡️Быстрая запись в "{last_name}" ({int(last_name_progress)}%)')

    choice = input('\nВаш выбор: ')

    # Логика меню
    if choice == '' and last_idx is not None:
        create_note(last=last_idx)
    elif choice == '1':
        create_note()
    elif choice == '2':
        create_project()
    elif choice == '3':
        view_project()
    elif choice == '4':
        change_project()
    elif choice == '0':
        game.menu()
    elif choice == '5':
        notifications_view()
    elif choice == '6':
        project_details_view()


# ГЛАВНЫЙ БЛОК ЗАПУСКА
if __name__ == "__main__":
    if game.load_game():
        game.update_gamer()

    # Бесконечный цикл, который держит программу включенной
    while True:
        try:
            main_menu()
        except KeyboardInterrupt:
            print('\nВыход...')
            break
        except Exception as e:
            print(f'\nПроизошла ошибка: {e}')
            input('Нажмите Enter...')
