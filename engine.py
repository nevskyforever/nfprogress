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
    def __init__(self, name, goal,
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
        try:
            deadline = datetime.strptime(input('Введите дату в формате дд.мм.гг'), '%d.%m.%y')
            self.deadline = deadline
            return 'Дедлайн проекта установлен.'
        except:
            raise ValueError('Неправильный формат даты для дедлайна!')
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
    def added_today(self):
        today = today_for_test()
        notes = self.notes
        today_added = [i.new_symbols for i in notes if i.create_date.date() == today]
        if today_added:
            today_added = sum(today_added)
        else:
            today_added = 0
        return f'Написано сегодня: {today_added}'

def load_data():
    try:
        with open('data.pkl', 'rb') as f:
            data = pickle.load(f)
            return data
    except FileNotFoundError:
        return {'last': None, 'projects': {'active': {}}}


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


def main_menu():
    pass