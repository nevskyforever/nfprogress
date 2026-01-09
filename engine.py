import pickle
import game
from datetime import date, datetime, timedelta

def load_projects(): # Загрузка проектов
        try:
            with open('projects.pkl', 'rb') as f:
                projects = pickle.load(f)
                return projects
        except FileNotFoundError:
            return {'last': None}

def save_projects(projects): # Сохранение проектов
    with open('projects.pkl', 'wb') as f:
        pickle.dump(projects, f)

def update_project():
    pass

def main_menu():
    print('nfprogress 0.9.1\n')
    print('Что вы хотите сделать?\n')
    print('1 - Новая запись')
    print('2 - Просмотр проектов')
    print('3 - Новый проект')
    print('4 - Изменить проект')
    print('5 - Игровой режим')
    last = load_projects()['last']
    if last is not None:
        print(f'Запись в последний проект ({last}) - Enter')
    do_list = {'1': new_note,
               '2': view_projects,
               '3': new_project,
               '4': change_project,
               '5': game.menu}
    update_project()
    do = input('\nВыберите пункт из меню: ')
    if do != '':
        do_list[do]()
    else:
        new_note(last)

def new_project():
    projects = load_projects()
    print('\nСОЗДАНИЕ ПРОЕКТА\n')
    name = input('Введите имя проекта: ')
    try:
        goal = int(input('Введите цель по проекту в символах: '))
    except ValueError:
        print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
        goal = int(input('Введите цель по проекту в символах: '))
    projects[name] = {'goal': goal,
                      'created': date.today(),
                      'total symbols': 0,
                      'progress': 0,
                      'notes': {},
                      'streaks': [],
                      'deadline': {'date': 'Нет', 'days left': 0}}

    save_projects(projects)
    print(f'\nПроект {name} создан\n')
    main_menu()

def view_projects():
    projects = load_projects()
    if len(projects) == 1:
        print('\nПроектов пока нет.')
        do = input('\nДля выхода нажмите Enter.')
        if do == '':
            main_menu()
    else:
        for name in projects.keys():
            if name != 'last':
                goal = projects[name]['goal']
                progress = projects[name]['progress']
                symbols = projects[name]['total symbols']
                deadline = projects[name]['deadline']['date']
                if deadline == 'Нет':
                    print(f'Название: {name}, '
                          f'прогресс: {progress}%, '
                          f'написано\цель: {symbols}/{goal} символов')
                else:
                    deadline = datetime.strftime(deadline, '%d.%m.%y')
                    days_left = projects[name]['deadline']['days left']
                    streaks = len(projects[name]['streaks'])
                    print(f'Название: {name}, '
                          f'прогресс: {progress}%, '
                          f'написано\цель: {symbols}/{goal} символов, '
                          f'дедлайн: {deadline}, осталось дней: {days_left} '
                          f'стрик: {streaks}')

        do = input('\nДля выхода нажмите Enter.')
        if do == '':
            main_menu()

def choice_project():
    projects = load_projects()
    if len(projects) == 1:
        print('\nПроектов пока нет.')
        do = input('\nДля выхода нажмите Enter.')
        if do == '':
            main_menu()
    else:
        projects_names = list(projects.keys())
        l = projects_names.index('last')
        del projects_names[l]
        print('ВЫБЕРИТЕ ПРОЕКТ:\n')
        for i in range(len(projects_names)):
            print(f'{i + 1} - {projects_names[i]}')
        try:
            choice = int(input('\nВведите номер выбранного проекта '
                           '\nили введите Enter для выхода в главное меню: '))
        except ValueError:
            print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
            change_project()
        else:
            choice = projects_names[choice - 1]
            print(f'\nВыбран проект: {choice}\n')
            return choice

def update_streaks(project):
    pass


def new_note(choice=None):
    print('\nСОЗДАНИЕ ЗАПИСИ\n')
    projects = load_projects()
    if choice == None:
        choice = choice_project()
    today = date.today()
    last_total = projects[choice]['total symbols']
    try:
        new_symbols = int(input(f'Введите текущее кол-во символов в {choice}: '))
    except ValueError:
        print('НЕКОРРЕКТНОЕ ЗНАЧЕНЕ.\n Введите число.')
        new_symbols = int(input('Введите текущее кол-во символов: '))
    symbol_progress = new_symbols - last_total
    projects[choice]['notes'][today] = {'symbol_progress': symbol_progress, 'streak_bonus': False}
    projects[choice]['total symbols'] = new_symbols

    symbols = projects[choice].get('total symbols', 0)
    goal = projects[choice]['goal']
    progress = round(symbols / goal * 100) if symbols != 0 else 0
    projects[choice]['progress'] = progress
    projects['last'] = choice

    deadline = projects[choice]['deadline']['date']

    if game.load_game() is not None:
        coins = game.give_coins(symbol_progress)
        exps = game.give_exps(symbol_progress)
        if deadline != 'Нет':
            today_bonus = projects[choice]['notes'][today].get('streak_bonus', False)
            if today_bonus:
                print(f'Получен бонус за продление стрика: {game.give_streak_bonus()} монет')
                projects[choice]['notes'][today]['streak_bonus'] = True
                save_projects(projects)
        print(f'\n Получено {coins} монет и {exps} опыта')

    save_projects(projects)

    do = input(f'\nЗапись добавлена в {choice}, прогресс: {progress}% и {symbol_progress} символов\n'
               f'\nВыйти в главное меню - Enter.')
    if do == '':
        main_menu()

def change_project():
    print('\nИЗМЕНЕНИЕ ПРОЕКТА\n')
    projects = load_projects()
    choice = choice_project()

    # Изменение имени
    def change_name():
        new_name = input(f'Введите новое имя проекта {choice} или Enter для выхода: ')
        if new_name != '':
            projects[new_name] = projects[choice]
            del projects[choice]
            save_projects(projects)
            print(f'\nИмя изменено на {new_name}.\n')
            main_menu()
        else:
            main_menu()

    # Изменение цели
    def change_goal():
        try:
            new_goal = int(input(f'Введите новую цель для {choice} или Enter для выхода: '))
            if new_goal != '':
                projects[choice]['goal'] = new_goal
                save_projects(projects)
                print(f'Цель {choice} изменена')
            else:
                main_menu()
        except ValueError:
            print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
            change_goal()

    # Изменение дедлайна
    def change_deadline():
        deadline_str = input('Введите дату дедлайна в формате "дд.мм.гг" или Enter: ')
        if deadline_str == '':
            main_menu()
        try:
            new_deadline = datetime.strptime(deadline_str, '%d.%m.%y')
            projects[choice]['deadline'] = {
                'date': new_deadline.date(),
                'days left': (new_deadline.date() - date.today()).days
            }
            save_projects(projects)
            print(f'\nДедлайн {choice} изменён.')
            main_menu()
        except ValueError:
            print('Формат: дд.мм.гг')
            change_deadline()

    # Удаление проекта
    def delete_project():
        from random import randint
        key = randint(1000, 9999)
        print(f'Если вы удалите {choice}, все его данные будут стерты без возможности восстановления \n')
        approve = int(input(f'Подтвердите удаление введя {key}: '))
        if approve == key:
            print(f'\n {choice} удален. \n')
            del projects[choice]
            save_projects(projects)
            main_menu()
        else:
            print('\n УДАЛЕНИЕ НЕ ПОДТВЕРЖДЕНО \n')
            main_menu()

    # Изменение кол-ва символов
    def change_total_symbols():
        if game.load_game() is not None:
            print('Это изменение не добавляет запись, а меняет текущий прогресс напрямую.')
            try:
                projects[choice]['total symbols'] = int(input(f'Введите новое кол-во символов в {choice}: '))
                save_projects(projects)
            except ValueError:
                print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
                change_total_symbols()
        else:
            password = input('Введите пароль: ')
            if password == '':

                print('Это изменение не добавляет запись, а меняет текущий прогресс напрямую.')
                try:
                    projects[choice]['total symbols'] = int(input(f'Введите новое кол-во символов в {choice}: '))
                    save_projects(projects)
                except ValueError:
                    print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
                    change_total_symbols()
            else:
                print('\n НЕПРАВИЛЬНЫЙ ПАРОЛЬ. \n')
                main_menu()



    change_list = {'1': change_name,
                   '2': change_goal,
                   '3': change_deadline,
                   '4': delete_project,
                   '5': change_project,}


    print(f'1 - изменить имя проекта {choice}')
    print(f'2 - изменить цель проекта {choice}')
    print(f'3 - изменить дедлайн проекта {choice}')
    print(f'4 - удалить проект {choice}')
    print(f'5 - Изменить общее кол-во символов в {choice}')
    print(f'\nВыйти в главное меню - Enter\n')
    print(f'Выберите пункт из меню: ')
    do = input()
    if do == '':
        main_menu()
    else:
        change_list[do]()

main_menu()