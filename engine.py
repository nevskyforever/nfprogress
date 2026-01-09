import pickle
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
    print('nfprogress 0.10\n')
    print('Что вы хотите сделать?\n')
    print('Новая запись - 1')
    print('Просмотр проектов - 2')
    print('Новый проект - 3')
    print('Изменить проект - 4')
    last = load_projects()['last']
    if last is not None:
        print(f'Запись в последний проект ({last}) - Enter')
    do_list = {'1': new_note,
               '2': view_projects,
               '3': new_project,
               '4': change_project}
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
    created = date.today()
    projects[name] = {'goal': goal,
                      'created': created,
                      'total symbols': 0,
                      'progress': 0,
                      'notes': {},
                      'deadline': 'Нет'}

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
                deadline = projects[name]['deadline']
                if deadline != 'Нет':
                    deadline = datetime.strftime(deadline, '%d.%m.%y')
                print(f'Название: {name}, '
                      f'прогресс: {progress}%, '
                      f'написано\цель: {symbols}/{goal} символов, '
                      f'дедлайн: {deadline}')
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

def new_note(choice = None):
    # Добавление записи
    print('\nСОЗДАНИЕ ЗАПИСИ\n')
    projects = load_projects()
    if choice is None:
        choice = choice_project()
    today = date.today()
    last_total = projects[choice]['total symbols']
    try:
        new_symbols = int(input(f'Введите текущее кол-во символов в {choice}: '))
    except ValueError:
        print('НЕКОРРЕКТНОЕ ЗНАЧЕНЕ.'
              '\n Введите число.')
        new_symbols = int(input('Введите текущее кол-во символов: '))
    symbol_progress = new_symbols - last_total
    projects[choice]['notes'][today] = new_symbols
    projects[choice]['total symbols'] = new_symbols

    # Расчет прогресса
    symbols = projects[choice].get('total symbols', 0)
    goal = projects[choice]['goal']
    if symbols != 0 and 'progress' in projects[choice].keys():
        progress = symbols / goal * 100
        progress = round(progress)
        projects[choice]['progress'] = progress
        projects['last'] = choice
        save_projects(projects)

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
        try:
            new_deadline = datetime.strptime(input('Введите дату дедлайна в формате "дд.мм.гг" или Enter для выхода: '),'%d.%m.%y')
            if new_deadline != '':
                projects[choice]['deadline'] = new_deadline
                save_projects(projects)
                print(f'\nДедлайн проекта {choice} изменен.\n')
                main_menu()
            else:
                main_menu()
        except ValueError:
            print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите дату в формате "дд.мм.гг".')
            change_deadline()

    change_list = {'1': change_name,
                   '2': change_goal,
                   '3': change_deadline}

    do = input(f'1 - изменить имя проекта {choice}\n'
          f'2 - изменить цель проекта {choice}\n'
          f'3 - изменить дедлайн проекта {choice}\n'
          f'\nВыйти в главное меню - Enter\n'
          f'Выберите пункт из меню: ')
    if do == '':
        main_menu()
    else:
        change_list[do]()

main_menu()