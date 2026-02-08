import pickle
import game
from datetime import date, datetime, timedelta
from random import randint

version = '1.3'
last_update = '03.02.26'

def today_for_test():
    TEST_DATE = None #date(2026, 1, 31)
    if TEST_DATE is None:
        return date.today()
    else:
        return TEST_DATE

class Project:
    def __init__(self, name='Без имени', goal=None,
                 create_date=today_for_test(),
                 total_symbols=0, progress=0,
                 notes=None, streaks=None, deadline='Нет',
                 status='active'):
        self.name = name
        self.goal = goal
        self.create_date = create_date
        self.total_symbols = total_symbols
        self.progress = progress
        self.notes = notes
        self.streaks = streaks
        self.deadline = deadline
        self.status = status
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
            return 'Проект завершен, поздравляем!'
        return None
    def get_status(self):
        return self.status
    def get_total_symbols(self):
        return self.total_symbols
    def get_added_symbols_today_value(self):
        today = today_for_test()
        notes = self.notes
        today_added = [i.new_symbols for i in notes if i.date_create.date() == today]
        if today_added:
            today_added = sum(today_added)
        else:
            today_added = 0
        return today_added
    def get_added_symbols_today_msg(self):
        today_added = self.get_added_symbols_today_value()
        return f'Написано сегодня: {today_added}'
    def set_new_notes(self, new_note):
        notes = self.notes
        if notes is None:
            notes = []
        notes.append(new_note)
        self.notes = notes
    def get_today_goal_value(self):
        if self.deadline == 'Нет':
            return None
        else:
            today = today_for_test()
            days_before = (self.deadline - today).days
            need_write = self.goal - self.total_symbols // days_before
            return need_write
    def get_today_goal_msg(self):
        value = self.get_today_goal_value()
        return f'Цель на сегодня: {value}'
    def get_streak_status(self):
        streaks = self.streaks
        if streaks is None:
            streaks = []
        today = today_for_test()
        yesterday = today - timedelta(days=1)
        today_added = self.get_added_symbols_today_value()
        today_goal = self.get_today_goal_value()
        if today_added < today_goal:
            return 'No'
        elif today_added >= today_goal and len(streaks) == 0:
            streaks.append(today)
            return 'Start'
        elif today_added >= today_goal and streaks[-1] == yesterday:
            streaks.append(today_added)
            self.streaks = streaks
            return 'Go'
        elif today in streaks:
            return 'Done'
        elif streaks[-1] != yesterday:
            lost_days = len(streaks)
            return f'Lose {lost_days}'
        return None

class Note:
    def __init__(self, new_total,
                 date_create=datetime(day=today_for_test().day,
                                      month=today_for_test().month,
                                      year=today_for_test().year,
                                      hour=datetime.now().hour,
                                      minute=datetime.now().minute,)):
        self.date_create = date_create
        self.new_total = new_total


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
    print('СОЗДКАНИЕ ПРОЕКТА')
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
        choice = int(input('Введите номер проекта или Enter для выхода: '))
        if type(choice) == str:
            main_menu()
        elif choice < 0 or choice > len(projects):
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

    new_note = Note(int(input(f'ВВедите новое кол-во символов в {choice.get_name()}: ')))

    # Сначала обновляем объект в памяти
    choice.set_new_notes(new_note)
    print(choice.get_added_symbols_today_msg())

    # И только потом сохраняем изменения в файл
    save_data(data)

def view_project():
    projects = load_data()['projects']
    if len(projects) == 0:
        print('Проектов пока нет')
    else:
        for project in projects:
            print(f'Название: {project.get_name()}, напиcано/цель: {project.get_total_symbols()}/{project.get_goal()}')
    do = input('Для выхода в главное меню введите Enter: ')
    if do == '':
        main_menu()
def main_menu():
    actions = {'1': create_note, '2': create_project, '3': view_project,}
    print('nfprogress')
    print('1 - Сделать запись')
    print('2 - Создать проект')
    print('3 - Просмотреть проекты')
    do = input('Выбор: ')
    actions[do]()

main_menu()