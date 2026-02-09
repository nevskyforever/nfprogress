import pickle
from datetime import date, datetime, timedelta
from idlelib.configdialog import changes
from random import randint

import game
version = '1.4'  # Обновили версию
last_update = '09.02.26'


def today_for_test():
    TEST_DATE = None
    if TEST_DATE is None:
        return date.today()
    else:
        return TEST_DATE


# === ФУНКЦИИ ИГРОВОГО РЕЖИМА ===

def is_gamer_mode():
    """Проверяет, активирован ли игровой режим (есть ли файл сохранения)"""
    return game.load_game() is not None


def game_event_add_symbols(symbols):
    """Событие: добавление символов (дает опыт и монеты)"""
    if is_gamer_mode():
        hero = game.load_game()
        # Даем опыт и деньги
        xp = hero.add_exp(symbols)
        coins = hero.add_coins(symbols)
        print(f'\n[RPG] Получено: +{xp} опыта, +{coins} монет')

        # Проверяем уровень (вдруг повысился)
        hero.level_up()


def game_event_streak(status, total_symbols):
    """Событие: обновление стрика"""
    if is_gamer_mode() and status:
        hero = game.load_game()
        msg = hero.give_streak_bonus(status, total_symbols)
        if msg:
            print(f'\n[RPG] {msg}')

        # Если статус Complete, это тоже бонус
        if status == 'Complete':
            # В методе give_streak_bonus вы уже обрабатываете 'Complete',
            # но если нужно отдельно - можно добавить логику
            pass


# ================================

class Note:
    date_create = None
    new_total = 0
    added = 0

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
    name = 'Без имени'
    goal = None
    create_date = None
    total_symbols = 0
    progress = 0
    deadline = 'Нет'
    status = 'active'
    notes = None
    streaks = None

    def __init__(self, name='Без имени', goal=None,
                 create_date=None, total_symbols=0, progress=0,
                 notes=None, streaks=None, deadline='Нет',
                 status='active'):

        self.name = name
        self.goal = goal

        if create_date is None:
            self.create_date = today_for_test()
        else:
            self.create_date = create_date

        self.total_symbols = total_symbols
        self.progress = progress
        self.deadline = deadline
        self.status = status

        if notes is None:
            self.notes = []
        else:
            self.notes = notes

        if streaks is None:
            self.streaks = []
        else:
            self.streaks = streaks

    def set_name(self, name):
        if name != '':
            self.name = name
            return 'Имя проекта изменено'
        else:
            raise ValueError('Некорректное имя проекта!')

    def get_name(self):
        return self.name

    def set_goal(self, goal):
        try:
            goal = int(goal)
            self.goal = goal
            return f'Установлена цель в {self.goal} символов'
        except:
            raise ValueError('Некорректное значение для цели, введите число!')

    def get_goal(self):
        return self.goal

    def set_deadline(self, deadline):
        if deadline == '':
            self.deadline = 'Нет'
            return None
        else:
            deadline = datetime.strptime(deadline, '%d.%m.%y')
            self.deadline = deadline
            return 'Дедлайн проекта установлен.'

    def get_deadline(self):
        return self.deadline

    def set_status(self, status):
        self.status = status
        if status == 'active':
            return 'Проект снова активен.'
        elif status == 'archived':
            return ('Проект архивирован.'
                    '\nВы можете вернуть его из архива, когда он снова понадобится.')
        elif status == 'completed':
            # ИГРОВОЕ СОБЫТИЕ: ЗАВЕРШЕНИЕ ПРОЕКТА
            game_event_streak('Complete', self.total_symbols)
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
        current_notes = self.notes
        if current_notes is None:
            current_notes = []

        today_added = [i.get_added() for i in current_notes if i.get_date_create() == today]
        if today_added:
            return sum(today_added)
        else:
            return 0

    def get_added_symbols_today_msg(self):
        today_added = self.get_added_symbols_today_value()
        return f'Написано сегодня: {today_added}'

    def set_new_notes(self, new_note):
        if self.notes is None:
            self.notes = []
        self.notes.append(new_note)

    def get_today_goal_value(self):
        if self.deadline == 'Нет':
            return None
        else:
            today = today_for_test()
            if not isinstance(self.deadline, datetime):
                return None

            days_before = (self.deadline.date() - today).days

            if days_before <= 0:
                return self.goal - self.total_symbols

            need_write = self.goal - self.total_symbols // days_before
            return need_write

    def get_today_goal_msg(self):
        value = self.get_today_goal_value()
        return f'Цель на сегодня: {value}'

    def get_streak_status(self):
        if self.streaks is None:
            self.streaks = []

        today = today_for_test()
        yesterday = today - timedelta(days=1)
        today_added = self.get_added_symbols_today_value()
        today_goal = self.get_today_goal_value()

        if today_goal is None:
            today_goal = 0

        status = None

        if today_added < today_goal:
            status = 'No'
        elif today_added >= today_goal and len(self.streaks) == 0:
            self.streaks.append(today)
            status = 'Start'
        elif today_added >= today_goal and self.streaks[-1] == yesterday:
            self.streaks.append(today_added)
            status = 'Go'
        elif today in self.streaks:
            status = 'Done'
        elif self.streaks and self.streaks[-1] != yesterday:
            lost_days = len(self.streaks)
            status = f'Lose {lost_days}'
            # Очищаем стрик после проигрыша, чтобы не спамить уроном
            self.streaks = []

            # ИГРОВОЕ СОБЫТИЕ: СТРИК
        # Вызываем только если статус изменился и это не "просто нет"
        if status and status != 'No' and status != 'Done':
            game_event_streak(status, self.total_symbols)

        # Особая обработка для Done (просто показать сообщение, если нужно, но бонусов не давать повторно)

        return status


def load_data():
    try:
        with open('data.pkl', 'rb') as f:
            data = pickle.load(f)
            return data
    except FileNotFoundError:
        return {'last': None, 'projects': []}


def save_data(data):
    with open('data.pkl', 'wb') as f:
        pickle.dump(data, f)


def about_program():
    print('Автор: nevskyforever')
    print(f'Версия приложения: {version}')
    print(f'Дата последнего обновления: {last_update}')
    input('\nДля выхода в главное меню нажмите Enter: ')
    main_menu()


def notifications_view():
    print('\nУВЕДОМЛЕНИЯ\n')
    data = load_data()
    notifications = data.get('notifications', {'new': [], 'read': []})
    new = notifications['new']
    read = notifications['read']

    if len(new) == 0 and len(read) == 0:
        print('Уведомлений пока нет.')
    else:
        print('НОВЫЕ УВЕДОМЛЕННИЯ\n')
        if len(new) == 0:
            print('Новых пока нет.')
        for i in new:
            print(i)
    if len(read) != 0:
        print('\nПРОЧИТАННЫЕ УВЕДОМЛЕННИЯ\n')
        for i in read:
            print(i)

    do = input('\nДля очистки прочитанных введите 1'
               '\nДля выхода введите Enter: ')

    if do == '1':
        notifications['read'] = []
        data['notifications'] = notifications
        save_data(data)
        print('\nПрочитанные уведомления очищены.\n')
        main_menu()
    else:
        notifications['read'].extend(notifications['new'])
        notifications['new'] = []
        data['notifications'] = notifications
        save_data(data)
        main_menu()


def create_project():
    data = load_data()
    projects = data.get('projects', [])
    print('СОЗДАНИЕ ПРОЕКТА')
    new_project = Project()
    print(new_project.set_name(input('Введите имя проекта: ')))
    print(new_project.set_goal(input('Введите цель по проекту в символах: ')))
    print(new_project.set_deadline(input('Введите дату в формате дд.мм.гг или Enter для пропуска: ')))
    projects.append(new_project)
    save_data(data)
    print('Проект создан.')
    main_menu()


def choice_project():
    projects = load_data()['projects']
    print('ВЫБОР ПРОЕКТА')
    if len(projects) == 0:
        print('Проектов пока нет')
        main_menu()
    else:
        for project in projects:
            print(f'{projects.index(project) + 1}. {project.get_name()}')
    try:
        choice = input('Введите номер проекта или Enter для выхода: ')
        if choice == '':
            main_menu()
        else:
            choice = int(choice)
        if choice < 0 or choice > len(projects):
            print('Неправильный выбор - такого номера нет в списке проектов')
            choice_project()
        return choice - 1
    except ValueError:
        print('Неправильное значение! Введите число!')
        create_project()


def create_note():
    data = load_data()
    projects = data['projects']
    do_choice = choice_project()
    choice = projects[do_choice]
    old_total = choice.get_total_symbols()

    try:
        new_total_input = input(f'Введите новое кол-во символов в {choice.get_name()}: ')
        if not new_total_input:
            main_menu()
            return
        new_total = int(new_total_input)
    except ValueError:
        print("Ошибка ввода числа")
        main_menu()
        return

    added = new_total - old_total
    if added < 0:
        added = 0

    new_note = Note(new_total, added)
    choice.set_new_notes(new_note)
    choice.set_total_symbols(new_total)
    print(choice.get_added_symbols_today_msg())

    # ИГРОВОЕ СОБЫТИЕ: ДОБАВЛЕНИЕ СИМВОЛОВ
    if added > 0:
        game_event_add_symbols(added)

    # ПРОВЕРКА СТРИКА ПОСЛЕ ДОБАВЛЕНИЯ
    choice.get_streak_status()

    data['last'] = do_choice
    save_data(data)
    main_menu()


def change_project():
    data = load_data()
    projects = data['projects']
    do_choice = choice_project()
    choice = projects[do_choice]
    print('ИЗМЕНЕНИЕ ПРОЕКТА')
    print('1 - Изменить имя')
    print('2 - Изменить цель')
    print('3 - Изменить кол-во символов в проекте')
    print('4 - Изменить дату дедлайна')
    print('5 - Архивировать проект')
    print('Enter - Выйти в главное меню')

    def change_name(choice):
        data = load_data()
        projects = data['projects']
        project = projects[choice]
        new_name = input(f'Введите новое имя для проекта {project.get_name()}: ')
        print(project.set_name(new_name))
        projects[choice] = project
        save_data(data)
        change_project()
    def change_goal(choice):
        data = load_data()
        projects = data['projects']
        project = projects[choice]
        new_goal = int(input(f'Введите новую цель в символах для {project.get_name()}: '))
        print(project.set_goal(new_goal))
        projects[choice] = project
        save_data(data)
        change_project()
        change_project()
    def change_deadline(choice):
        data = load_data()
        projects = data['projects']
        project = projects[choice]
        new_deadline = input(f'Введите новую дату дедлайна для проекта {project.get_name()}'
                             f'\nДату вводите в формате дд.мм.гг: ')
        print(project.set_new_deadline(new_deadline))
        projects[choice] = project
        save_data(data)
        change_project()
    do = input('Выбор: ')
    change_do = {'1': change_name, '2': change_goal,}
    if do != '':
        try:
            change_do[do](do_choice)
            save_data(data)
        except KeyError:
            print('Неправильное значение для менб изменения, введите число!')
    else:
        main_menu()

def view_project():
    projects = load_data()['projects']
    if len(projects) == 0:
        print('Проектов пока нет')
    else:
        for project in projects:
            print(f'Название: {project.get_name()}, написано/цель: {project.get_total_symbols()}/{project.get_goal()}')

            # Показываем статус стрикa
            streak = project.get_streak_status()
            if streak == 'Go' or streak == 'Done':
                print(f'   🔥 Стрик активен!')
            elif streak == 'No':
                val = project.get_today_goal_value()
                if val and val > 0:
                    print(f'   📅 Нужно сегодня: {val}')

    do = input('Для выхода в главное меню введите Enter: ')
    if do == '':
        main_menu()


def main_menu():
    actions = {
        '1': create_note,
        '2': create_project,
        '3': view_project,
        '4': change_project,
        '0': game.menu  # Добавлен пункт меню
    }

    data = load_data()
    projects = data['projects']
    cnt_active = len([i.get_status() for i in projects if i.get_status() == 'active'])

    print('\n--- nfprogress ---')
    print('1 - Сделать запись')
    print('2 - Создать проект')
    print(f'3 - Просмотреть проекты (активных: {cnt_active})')
    print('4 - Изменить проект')

    # Показываем пункт игрового режима по-разному, в зависимости от того, включен он или нет
    if is_gamer_mode():
        hero = game.load_game()
        print(f'0 - 🦸 Персонаж (Lvl {hero.level} | ❤️ {hero.health})')
    else:
        print('0 - 🎮 Активировать игровой режим')

    last = data['last']
    if last is not None and last < len(projects):
        last_choice = projects[last]
        print(f'Enter - быстрая запись в "{last_choice.get_name()}"')

    do = input('Выбор: ')

    if do == '' and last is not None and last < len(projects):
        # Логика быстрой записи (дублируется, можно вынести в отдельную функцию, но оставил тут)
        last_choice = projects[last]
        old_total = last_choice.get_total_symbols()
        try:
            new_total = int(input(f'Введите новое кол-во символов в {last_choice.get_name()}: '))
            added = new_total - old_total
            if added < 0: added = 0

            new_note = Note(new_total, added)
            last_choice.set_new_notes(new_note)
            last_choice.set_total_symbols(new_total)
            print(last_choice.get_added_symbols_today_msg())

            # ИГРОВЫЕ СОБЫТИЯ
            if added > 0:
                game_event_add_symbols(added)
            last_choice.get_streak_status()

            save_data(data)
        except ValueError:
            print("Ошибка ввода")

        main_menu()
    elif do in actions:
        actions[do]()
    else:
        main_menu()


if __name__ == "__main__":
    # При запуске проверяем "жизнь" персонажа, если он есть
    if is_gamer_mode():
        game.update_gamer()
    main_menu()
