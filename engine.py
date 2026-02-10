import pickle
from datetime import datetime, timedelta, date
import game

version = '2.0'
last_update = '09.02.26'


def today_for_test():
    """Возвращает сегодняшнюю дату."""
    dt = date(2026, 2, 12)
    if dt is None:
        return datetime.today()
    else:
        return dt

class Note:
    new_total = 0
    added = 0
    date_create = None
    def __init__(self, new_total, added, date_create=None):
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
        self.added = added

    def get_new_total(self):
        return self.new_total

    def get_added(self):
        return self.added

    def get_date_create(self):
        return self.date_create.date()
class Project:
    def __init__(self, name='Без имени', goal=None,
                 create_date=None, total_symbols=0, progress=0,
                 notes=None, streaks=None, deadline='Нет',
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
            return 'Проект снова активен.'
        elif status == 'в архиве':
            self.deadline = 'Нет'
            return 'Проект архивирован. Дедлайн сброшен.'
        elif status == 'завершен':
            return 'Проект завершен, поздравляем!'
        return None

    def get_status(self):
        return self.status

    def get_total_symbols(self):
        return self.total_symbols

    def set_total_symbols(self, total_symbols):
        self.total_symbols = total_symbols

    def get_added_symbols_today_value(self):
        today = today_for_test()
        today_added = [i.get_added() for i in self.notes if i.get_date_create() == today]
        return sum(today_added) if today_added else 0

    def get_added_symbols_today_msg(self):
        return f'Написано сегодня: {self.get_added_symbols_today_value()}'

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
        return f'Цель на сегодня: {value}'

    def get_streak_status(self):
        today = today_for_test()
        yesterday = today - timedelta(days=1)
        today_added = self.get_added_symbols_today_value()
        today_goal = self.get_today_goal_value()

        status = 'No'  # Статус по умолчанию

        # Проверяем, выполнена ли цель (используем >=, чтобы точное совпадение тоже считалось)
        if today_added >= today_goal:
            # Если цель выполнена, смотрим на стрик
            if len(self.streaks) == 0:
                self.streaks.append(today)
                status = 'Start'
            elif self.streaks[-1] == today:
                status = 'Done'
            elif self.streaks[-1] == yesterday:
                self.streaks.append(today)
                status = 'Go'
        elif len(self.streaks) > 0 and self.streaks[-1] != yesterday:
            # Если последний день стрика был не вчера и не сегодня — стрик потерян
            lose = len(self.streaks)
            self.streaks = []  # Сбрасываем старый
            status = f'Lose {lose}'
            if today_added >= today_goal:
                status = f'Lose {lose} Start'
                self.streaks.append(today)  # Начинаем новый, так как цель выполнена

        return status  # Возвращаем строку, а не список!

    def get_streak_msg(self, status):
        if status == 'Start':
            return 'Стрик начат! Отличное начало, главное - продолжать!'
        elif status == 'Go':
            streaks = len(self.streaks)
            return f'Стрик продлен! Вы движетесь к цели уже {streaks} дней подряд!'
        elif status == 'Done':
            return f'Стрик сегодня уже продлен, но символы лишними не будут'
        elif status == 'Complete':
            pass
        elif status[0] == 'Lose':
            if len(status) == 2:
                print(f'Стрик потерян! Вы были в цели {status[1]} дней подряд.')
            elif len(status) == 3:
                print(f'Стрик потерян! Вы были в цели {status[1]} дней подряд.'
                      f'\nВы начали новый стрик!')

    def set_new_notes(self, new_note):
        print(self.get_today_goal_msg())
        self.notes.append(new_note)
# === ЗАГРУЗКА И СОХРАНЕНИЕ ===

def load_data():
    try:
        with open('data.pkl', 'rb') as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError):
        return {'last': None, 'projects': []}


def save_data(data):
    with open('data.pkl', 'wb') as f:
        pickle.dump(data, f)


# === МЕНЮ И ЛОГИКА ===

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
    projects = data.get('projects', [])
    print('\n--- СОЗДАНИЕ ПРОЕКТА ---')
    new_project = Project()

    try:
        print(new_project.set_name(input('Имя проекта: ')))
        print(new_project.set_goal(input('Цель (символы): ')))
        print(new_project.set_deadline(input('Дедлайн (дд.мм.гг) или Enter: ')))

        projects.append(new_project)
        data['projects'] = projects
        save_data(data)
        print('Проект создан.')
    except ValueError as e:
        print(f'Ошибка: {e}')


def create_note(last=None):
    """Создание записи. Если передан last, выбор проекта пропускается."""
    data = load_data()
    projects = data.get('projects', [])

    # ИСПРАВЛЕНИЕ: Сначала проверяем быструю запись!
    if last is not None and last < len(projects):
        print('\n--- БЫСТРАЯ ЗАПИСЬ ---')
        choice_idx = last
    else:
        choice_idx = choice_project()

    # Если пользователь ничего не выбрал или нажал отмену
    if choice_idx is None:
        return

    project = projects[choice_idx]
    old_total = project.get_total_symbols()
    gamer = game.load_game()

    print(f'Проект: {project.get_name()}')
    print(f'Написано в проекте: {old_total}')
    print(project.get_added_symbols_today_msg())
    print(project.get_today_goal_msg())

    raw_val = input(f'Введите НОВОЕ ОБЩЕЕ число символов: ')
    if not raw_val:
        return

    try:
        new_total = int(raw_val)
    except ValueError:
        print("Ошибка: введите число.")
        return

    added = new_total - old_total
    if added < 0: added = 0

    new_note = Note(new_total, added)
    project.set_new_notes(new_note)
    project.set_total_symbols(new_total)
    save_data(data)

    print(project.get_added_symbols_today_msg())

    streak_status = project.get_streak_status()

    if gamer is not None:
        print(gamer.give_symbol_bonus(added))
        if streak_status:
            print(gamer.give_streak_bonus(streak_status, new_total))
    data['last'] = choice_idx
    save_data(data)

def change_project():
    idx = choice_project()
    if idx is None:
        return

    data = load_data()
    project = data['projects'][idx]
    status = project.get_status()

    print(f'\nРЕДАКТИРОВАНИЕ: {project.get_name()}')
    print('1 - Изменить имя')
    print('2 - Изменить цель')
    print('3 - Изменить счетчик символов (без опыта)')
    print('4 - Изменить дедлайн')
    print('7 - Удалить проект')

    if status == 'активен':
        print('5 - В архив')
    elif status == 'в архиве':
        print('6 - Вернуть из архива')

    cmd = input('Выбор (Enter - назад): ')

    try:
        if cmd == '1':
            print(project.set_name(input('Новое имя: ')))
        elif cmd == '2':
            print(project.set_goal(input('Новая цель: ')))
        elif cmd == '3':
            val = int(input('Введите точное число символов: '))
            project.set_total_symbols(val)
            print('Сохранено.')
        elif cmd == '4':
            print(project.set_deadline(input('Новый дедлайн (дд.мм.гг): ')))
        elif cmd == '5' and status == 'активен':
            print(project.set_status('в архиве'))
        elif cmd == '6' and status == 'в архиве':
            print(project.set_status('активен'))
        elif cmd == '7':
            data['projects'].remove(project)
    except ValueError as e:
        print(f"Ошибка: {e}")

    save_data(data)


def view_project():
    data = load_data()
    projects = data.get('projects', [])

    active = [p for p in projects if p.get_status() == 'активен']
    archived = [p for p in projects if p.get_status() == 'в архиве']

    print('\n--- ПРОСМОТР ПРОЕКТОВ ---')
    if not active:
        print('Активных проектов нет.')
    else:
        for p in active:
            dl = p.get_deadline_str()
            print(f"{p.get_name()}: Цель/написано - {p.get_total_symbols()}/{p.get_goal()} | Дедлайн: {dl}")

    if archived:
        if input('\nПоказать архив? (введите "a"): ') == 'a':
            print('\n--- АРХИВ ---')
            for p in archived:
                print(f"{p.get_name()}: {p.get_total_symbols()}/{p.get_goal()}")

    input('\nНажмите Enter, чтобы вернуться в меню...')


def main_menu():
    """Отображение меню. Возвращает управление в бесконечный цикл."""
    data = load_data()
    projects = data.get('projects', [])
    last_idx = data.get('last')

    active_count = len([p for p in projects if p.get_status() == 'активен'])

    print('\nnfprogress')
    print(f'Сегодня {today_for_test().strftime("%d.%m.%y")}')
    print('1 - Сделать запись')
    print('2 - Создать проект')
    print(f'3 - Проекты (активных: {active_count})')
    print('4 - Настройки проекта')

    if game.load_game():
        hero = game.load_game()
        print(f'0 - 🦸 Герой (Lvl {hero.level})')
    else:
        print('0 - 🎮 Включить RPG режим')

    # Подсказка для быстрой записи
    if last_idx is not None and last_idx < len(projects):
        last_name = projects[last_idx].get_name()
        print(f'Enter - Быстрая запись в "{last_name}"')

    choice = input('Ваш выбор: ')

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
