import pickle

import game
from datetime import date, datetime
from random import randint

version = '1.3'
last_update = '03.02.26'

def today_for_test():
    TEST_DATE = None #date(2026, 1, 31)
    if TEST_DATE is None:
        return date.today()
    else:
        return TEST_DATE

class Note:
    def __init__(self, new_symbols,
                 date_create=datetime(day=today_for_test().day,
                                      month=today_for_test().month,
                                      year=today_for_test().year,
                                      hour=datetime.now().hour,
                                      minute=datetime.now().minute,)):
        self.date_create = date_create
        self.new_symbols = new_symbols

class Project:
    def __init__(self, name=None, goal=None,
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
    def set_name(self):
        name = input('Введите имя проекта: ')
        if name != '':
            self.name = name
            return 'Имя проекта изменено'
        else:
            raise ValueError('Некорректное имя проекта!')
    def set_goal(self):
        try:
            goal = int(input('Введите цель по проекту в символах: '))
            self.goal = goal
            return f'Установлена цель в {self.goal} символов'
        except:
            raise ValueError('Некорректное значение для цели, введите число!')
    def set_deadline(self):
        deadline = input('Введите дату в формате дд.мм.гг или Enter для пропуска: ')
        if deadline == '':
            self.deadline = None
            return None
        else:
            deadline = datetime.strptime(deadline, '%d.%m.%y')
            self.deadline = deadline
            return 'Дедлайн проекта установлен.'

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
    def update_total_symbols(self):
        # Создаем переменные
        old_total_symbols = self.total_symbols
        new_total_symbols = 0
        # Считаем символы в проекте
        for note in self.notes: new_total_symbols += note.new_symbols
        symbol_added = new_total_symbols - old_total_symbols
        # Сохраняем результаты
        self.total_symbols = new_total_symbols
        return (f'Добавлено символов: {symbol_added}'
                f'\nТекущее кол-во символов: {self.total_symbols}.')
    def get_added_today_msg(self):
        today = today_for_test()
        notes = self.notes
        today_added = [i.new_symbols for i in notes if i.create_date.date() == today]
        if today_added:
            today_added = sum(today_added)
        else:
            today_added = 0
        return f'Написано сегодня: {today_added}'
    def get_added_notes_value(self):
        today = today_for_test()
        notes = self.notes
        today_added = [i.new_symbols for i in notes if i.create_date.date() == today]
        if today_added:
            today_added = sum(today_added)
        else:
            today_added = 0
        return today_added
    def set_new_notes(self, new_note):
        notes = self.notes
        notes.append(new_note)

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
    print('СОЗДКАНИЕ ПРОЕКТА')
    new_project = Project()
    new_project.set_name()
    new_project.set_goal()
    new_project.set_deadline()
    data['projects'].append(new_project)
    save_data(data)
    print('Проект создан')
    main_menu()

def view_project():
    projects = load_data()['projects']
    if len(projects) == 0:
        print('Проектов пока нет')
    else:
        for project in projects:
            print(f'Название: {project.name}, напиcано/цель: {project.total_symbols}/{project.goal}')
    do = input('Для выхода в главное меню введите Enter: ')
    if do == '':
        main_menu()

def main_menu():
    actions = {'1': create_project, '2': view_project,}
    print('nfprogress')
    print('1 - Создать проект')
    print('2 - Просмотреть проекты')
    do = input('Выбор: ')
    actions[do]()

main_menu()