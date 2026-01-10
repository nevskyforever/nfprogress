import pickle
import game
from datetime import date, datetime, timedelta

def load_data():
    try:
        with open('data.pkl', 'rb') as f:
            data = pickle.load(f)
            return data
    except FileNotFoundError:
        return {'last': None, 'projects': {}}

def save_data(data):
    with open('data.pkl', 'wb') as f:
        pickle.dump(data, f)

def main_menu():
    print('nfprogress 0.11.2\n')
    print('Что вы хотите сделать?\n')
    print('1 - Новая запись')
    print('2 - Просмотр проектов')
    print('3 - Новый проект')
    print('4 - Изменить проект')
    print('5 - Игровой режим')
    print('6 - Подробности о проекте')
    last = load_data()['last']
    if last is not None:
        print(f'\nЗапись в последний проект ({last}) - Enter')
    do_list = {'1': new_note,
    '2': view_projects,
    '3': new_project,
    '4': change_project,
    '5': game.menu,
    '6': more_details}
    do = input('\nВыберите пункт из меню: ')
    if do != '':
        try:
            do_list[do]()
        except KeyError:
            print('НЕПРАВИЛЬНЫЙ ВЫБОР')
            main_menu()
    else:
        new_note(last)

def new_project():
    data = load_data()
    print('\nСОЗДАНИЕ ПРОЕКТА\n')
    name = input('Введите имя проекта или Enter для выхода: ')
    if name == '':
        print('\n СОЗДАНИЕ ПРОЕКТА ОТМЕНЕНО \n')
        main_menu()
    try:
        goal = input('Введите цель по проекту в символах или Enter для выхода: ')
        if goal == '':
            print('\n СОЗДАНИЕ ПРОЕКТА ОТМЕНЕНО \n')
            main_menu()
        goal = int(goal)
    except ValueError:
        print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
        goal = int(input('Введите цель по проекту в символах: '))
    try:
        deadline = datetime.strptime(input('Введите дедлайн проекта в формате дд.мм.гг '
                                           '\n или Enter, чтобы пропустить: '), '%d.%m.%y')
        if deadline == '':
            deadline = 'Нет'
    except ValueError:
        print('\n ЗНАЧЕНИЕ НЕКОРРЕКТНО \n')
        deadline = datetime.strptime(input('Введите дедлайн проекта в формате дд.мм.гг '
                                           '\n или Enter, чтобы пропустить: '), '%d.%m.%y')
        if deadline == '':
            deadline = 'Нет'
    data['projects'][name] = {'goal': goal,
    'created': date.today(),
    'total symbols': 0,
    'progress': 0,
    'notes': {},
    'streaks': [],
    'deadline': {'date': deadline, 'days left': 0}}
    data['last'] = name
    save_data(data)
    print(f'\nПроект {name} создан\n')
    main_menu()

def view_projects():
    data = load_data()
    if len(data['projects']) == 0:
        print('\nПроектов пока нет.')
        do = input('\nДля выхода нажмите Enter.')
        if do == '':
            main_menu()
    else:
        for name in data['projects'].keys():
            if name != 'last':
                goal = data['projects'][name]['goal']
                progress = data['projects'][name]['progress']
                symbols = data['projects'][name]['total symbols']
                deadline = data['projects'][name]['deadline']['date']
                if deadline == 'Нет':
                    print(f'Название: {name}, '
                    f'прогресс: {progress}%, '
                    f'написано/цель: {symbols}/{goal} символов')
                else:
                    deadline = datetime.strftime(deadline, '%d.%m.%y')
                    days_left = data['projects'][name]['deadline']['days left']
                    streaks = len(data['projects'][name]['streaks'])
                    print(f'Название: {name}, '
                    f'прогресс: {progress}%, '
                    f'написано/цель: {symbols}/{goal} символов, '
                    f'дедлайн: {deadline}, осталось дней: {days_left} '
                    f'стрик: {streaks}')
        do = input('\nДля выхода нажмите Enter.')
        if do == '':
            main_menu()

def choice_project():
    data = load_data()
    projects = data['projects']
    if len(projects) == 0:
        print('\nПроектов пока нет.')
        do = input('\nДля выхода нажмите Enter.')
        if do == '':
            main_menu()
    else:
        projects_names = list(data['projects'].keys())
        print('ВЫБЕРИТЕ ПРОЕКТ:\n')
        for i in range(len(projects_names)):
            print(f'{i + 1} - {projects_names[i]}')
        try:
            choice = int(input('\nВведите номер выбранного проекта '
            '\nили введите Enter для выхода в главное меню: '))
            choice = projects_names[choice - 1]
            print(f'\nВыбран проект: {choice}\n')
            return choice
        except (ValueError, IndexError):
            print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
            main_menu()

def chek_streak(project):
    data = load_data()
    streaks = data['projects'][project]['streaks']
    today = date.today()
    if len(streaks) == 0:
        streaks.append(today)
        streak_status = 'Start'
    else:
        yesterday = today - timedelta(days=1)
        if streaks[-1] == yesterday:
            streaks.append(today)
            streak_status = 'Go'
        if streaks[-1] == today:
            streak_status = 'Done'
        else:
            streak_status = f'Lose {len(streaks)}'
            streaks = [today]
    data['projects'][project]['streaks'] = streaks
    save_data(data)
    return streak_status

def new_note(choice=None):
    print('\nСОЗДАНИЕ ЗАПИСИ\n')
    # Проверяем выбор
    if choice is None:
        choice = choice_project()
    # Загружаем данные
    data = load_data()
    data['last'] = choice
    project = data['projects'][choice]
    goal = project['goal']
    last_symbols = project['total symbols']
    today = date.today()
    today_goal = 0
    game_status = game.load_game()
    deadline = project['deadline']['date']
    if deadline != 'Нет':
        # Считаем дни до дедлайна и цель на сегодня
        days_left = (deadline - today).days
        today_goal = (goal - last_symbols) // days_left
        print(f'Цель на сегодня: {today_goal} символов')
    # Запрашиваем символы
    try:
        new_symbols = input('Введите кол-во текущих символов или Enter для выхода:  ')
        if new_symbols == '':
            main_menu()
        else:
            new_symbols = int(new_symbols)
    except ValueError:
        print('\n ЗНАЧЕНИЕ НЕКОРРЕКТНО \n')
        main_menu()
    # Считаем прогресс в процентах
    progress = round(new_symbols / goal * 100)
    # Считаем прогресс в символах
    symbol_progress = new_symbols - last_symbols
    # Пишем прогресс в проект
    project['notes'][today] = {'symbol_progress': symbol_progress}
    project['progress'] = progress
    project['total symbols'] = new_symbols
    # Сохраняем все
    save_data(data)
    print(f'Запись добавлена в {choice}\n'
          f'Написано {symbol_progress} символов, прогресс: {progress}%\n')
    # Проверяем выполнение ежедневной цели
    if today_goal <= symbol_progress:
        # Если цель выполнена - проверяем текущий стрик и получаем статус
        last_streak_days = len(project['streaks'])
        streak_status = chek_streak(choice)
        # Обновляем данные, повторно из загружая
        data = load_data()
        project = data['projects'][choice]
        streak_days = len(project['streaks'])
        # Отображаем статус стрика
        if streak_status == 'Go':
            print(f'Вы продлили стрик! Вы в цели уже {streak_days} дней!')
        elif streak_status == 'Lose':
            print(f'Стрик прерван, вы потеряли {last_streak_days} и начали новый стрик')
        elif streak_status == 'Start':
            print('Вы начали путь к цели, стрику дан старт!')

        if game_status is not None:  # ← Отдельное условие для игры
            data = load_data()
            project = data['projects'][choice]
            bonus_status = project['notes'][today].get('streak_bonus', False)
            if bonus_status is False:
                print(game.give_streak_bonus(streak_status))
                project['notes'][today]['streak_bonus'] = True
                data['projects'][choice] = project
                save_data(data)

        main_menu()

    else:
        main_menu()


def change_project():
    print('\nИЗМЕНЕНИЕ ПРОЕКТА\n')
    choice = choice_project()
    if choice is None:
        return

    def change_name():
        data = load_data()
        new_name = input(f'Введите новое имя проекта {choice} или Enter для выхода: ')
        if new_name != '':
            data['projects'][new_name] = data['projects'][choice]
            del data['projects'][choice]
            if data['last'] == choice:
                data['last'] = new_name
            save_data(data)
            print(f'\nИмя изменено на {new_name}.\n')
            main_menu()
        else:
            main_menu()

    def change_goal():
        try:
            new_goal = int(input(f'Введите новую цель для {choice} или Enter для выхода: '))
            if new_goal > 0:
                data = load_data()
                data['projects'][choice]['goal'] = new_goal
                save_data(data)
                print(f'Цель {choice} изменена на {new_goal}\n')
                main_menu()
            else:
                print('Цель должна быть больше 0')
                change_goal()
        except ValueError:
            print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
            change_goal()

    def change_deadline():
        deadline_str = input('Введите дату дедлайна в формате "дд.мм.гг" или Enter: ')
        if deadline_str == '':
            main_menu()
            return
        try:
            new_deadline = datetime.strptime(deadline_str, '%d.%m.%y')
            data = load_data()
            data['projects'][choice]['deadline'] = {
                'date': new_deadline.date(),
                'days left': (new_deadline.date() - date.today()).days
            }
            save_data(data)
            print(f'\nДедлайн {choice} изменён на {deadline_str}.\n')
            main_menu()
        except ValueError:
            print('Формат: дд.мм.гг')
            change_deadline()

    def delete_project():
        from random import randint
        key = randint(1000, 9999)
        print(f'Если вы удалите {choice}, все его данные будут стерты без возможности восстановления \n')
        try:
            approve = int(input(f'Подтвердите удаление введя {key}: '))
            if approve == key:
                data = load_data()
                print(f'\n {choice} удален. \n')
                del data['projects'][choice]
                if data['last'] == choice:
                    data['last'] = None
                save_data(data)
                main_menu()
            else:
                print('\n УДАЛЕНИЕ НЕ ПОДТВЕРЖДЕНО \n')
                main_menu()
        except ValueError:
            print('\n НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ \n')
            main_menu()

    print('1 - Изменить имя')
    print('2 - Изменить цель')
    print('3 - Изменить дедлайн')
    print('4 - Удалить проект')

    do = input('\nВыберите действие: ')
    actions = {'1': change_name, '2': change_goal, '3': change_deadline, '4': delete_project}

    try:
        actions[do]()
    except KeyError:
        print('НЕПРАВИЛЬНЫЙ ВЫБОР')
        change_project()

def more_details():
    print('\n ПРОСМОТР ДЕТАЛЕЙ ПРОЕКТА \n')
    # Получаем данные
    choice = choice_project()
    project = load_data()['projects'][choice]
    notes = project['notes']

    # Считаем среднее кол-во символов
    if len(notes) > 0:
        total_symbols = sum(note['symbol_progress'] for note in notes.values())
        avg_symbols = round(total_symbols / len(notes))
    else:
        avg_symbols = 0

    print(f'Название: {choice}\n'
          f'Цель: {project["goal"]}\n'
          f'Написано: {project["total symbols"]} символов\n'
          f'Прогресс: {project["progress"]}%\n'
          f'Среднее символов в записи: {avg_symbols}\n'
          f'Дедлайн: {project["deadline"]["date"]}\n')

    if project["deadline"]["date"] != 'Нет':
        print(f'Стрик: {len(project["streaks"])} дней\n')

    print(f'Кол-во записей: {len(notes)}')

    input('\nДля выхода нажмите Enter.')
    main_menu()


main_menu()