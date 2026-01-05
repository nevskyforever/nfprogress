import pickle
import locale

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

def read_projects(filename='projects.pkl'):
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            return data
    except (FileNotFoundError, EOFError):
        return {}

def save_projects(data, filename='projects.pkl'):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

def new_project():
    import datetime
    from datetime import timedelta

    projects = read_projects()
    print('Создание проекта')
    name = input('Введите название: ')
    goal = input('Введите цель (в символах): ')

    # базовые поля
    projects[name] = {'goal': int(goal),
                      'symbols': 0,
                      'progress': 0,
                      'notes': {}
                      'streak': 0,      # текущий стрик
                      'max_streak': 0,  # максимальный стрик
                      'deadline': 'Нет',
                      'created': f'{datetime.date.today().strftime("%d.%m.%y")}'}

    # предложение задать дедлайн
    date_input = input('Введите дату дедлайна (дд.мм.гг) / количество дней (число)\n'
                       'или нажмите Enter, чтобы пропустить: ')

    if date_input == '':
        # дедлайн остается 'Нет'
        pass
    else:
        if date_input.isdigit():
            deadline = datetime.datetime.now() + timedelta(days=int(date_input))
            deadline = deadline.strftime('%d.%m.%y')
        else:
            given_date = datetime.datetime.strptime(date_input, '%d.%m.%y')
            deadline = given_date.strftime('%d.%m.%y')
        projects[name]['deadline'] = deadline

    save_projects(projects)
    print('\nПроект сохранен\n')
    main_menu()

def upd_projects():
   pass


def view_projects():
    upd_projects()
    projects = read_projects()
    if len(projects) == 0:
        print('\nПроектов пока нет.\n')
        main_menu()
    else:
        print('Список проектов:\n')
        for name, data in projects.items():
            goal = data['goal']
            symbols = data['symbols']
            progress = data['progress']
            streak = data.get('streak', 0)
            print(
                f'Название: {name}, цель: {goal}, прогресс: {symbols}/{goal} ({progress:.1f}%), '
                f'дедлайн: {data["deadline"]}, текущий стрик: {streak} дн.'
            )

        print()
        choice = input('Нажмите Enter для возврата в главное меню: ')
        if choice == '':
            main_menu()

def choice_project():
    projects = read_projects()
    if len(projects) == 0:
        print('Проектов пока нет\n')
        main_menu()
    project_list = list(projects.keys())
    print('Ваши проекты:\n')
    for i, project_name in enumerate(project_list, 1):
        display_name = project_name.replace('_', ' ')
        print(f"{i} - {display_name}")
    print()
    choice = input('Введите номер проекта или нажмите Enter для выхода: ')
    if choice == '':
        main_menu()
    selected_project = project_list[int(choice) - 1]
    return selected_project


def more_about_projects():
    pass

def new_note():
    pass

def change_project_menu():

    def delete_project():
        print('Удаление проекта\n')
        projects = read_projects()
        selected_project = choice_project()
        done = input('Подтвердите удаление (нажмите Enter для отмены или введите "1" для удаления): ')
        if done == '1':
            del projects[selected_project]
            save_projects(projects)
            print('\nПроект удален\n')
        else:
            print('\nУдаление отменено\n')
        change_project_menu()

    def change_name():
        projects = read_projects()
        print('Переименование проекта\n')
        selected_project = choice_project()
        new_name = input('Введите новое имя проекта: ')
        projects[new_name] = projects[selected_project]
        del projects[selected_project]
        save_projects(projects)
        print('\nИмя проекта успешно изменено\n')
        change_project_menu()

    def change_goal():
        projects = read_projects()
        print('Изменение цели проекта')
        selected_project = choice_project()
        projects[selected_project]['goal'] = int(input('Введите новую цель (в символах): '))
        upd_projects()
        save_projects(projects)
        print(f'\nЦель {selected_project} успешно изменена!\n')
        change_project_menu()

    def project_deadline():
        from datetime import datetime, timedelta
        print('Установка/изменение дедлайна\n')
        projects = read_projects()
        selected_project = choice_project()
        date_input = input('Введите дату (дд.мм.гг) / количество дней (число) или нажмите Enter для ее удаления: ')
        if date_input == '':
            projects[selected_project]['deadline'] = 'Нет'
            save_projects(projects)
            print('\nДедлайн удален\n')
        else:
            if date_input.isdigit():
                deadline = datetime.now() + timedelta(days=int(date_input))
                deadline = deadline.strftime('%d.%m.%y')
            else:
                given_date = datetime.strptime(date_input, '%d.%m.%y')
                deadline = given_date.strftime('%d.%m.%y')
            projects[selected_project]['deadline'] = deadline
            save_projects(projects)
            print('Дата дедлайна сохранена!')
        change_project_menu()

    def edit_notes():
        from datetime import datetime
        projects = read_projects()
        print('Изменение/удаление записей\n')
        selected_project = choice_project()
        notes = projects[selected_project].get('notes', {})

        if not notes:
            print('У проекта пока нет записей.\n')
            change_project_menu()
            return

        # показываем все записи с индексами
        sorted_notes = sorted(
            notes.items(),
            key=lambda x: datetime.strptime(x[0], '%d.%m.%y')
        )
        for i, (date, value) in enumerate(sorted_notes, 1):
            symbols = value[0] if isinstance(value, (list, tuple)) else int(value)
            print(f'{i}. {date} - {symbols} символов')

        idx = input('\nВведите номер записи для изменения/удаления или нажмите Enter для выхода: ')
        if idx == '':
            change_project_menu()
            return

        try:
            idx = int(idx)
            date, value = sorted_notes[idx - 1]
        except (ValueError, IndexError):
            print('Неверный номер записи.\n')
            change_project_menu()
            return

        action = input('Введите "1" для изменения, "2" для удаления, Enter для отмены: ')
        if action == '1':
            # выбор, что менять
            what = input('Что изменить?\n'
                         '1 - только дату\n'
                         '2 - только кол-во символов\n'
                         '3 - и дату, и кол-во символов\n'
                         'Нажмите Enter для отмены\n'
                         'Выбор: ')
            if what == '':
                print('\nИзменение отменено.\n')
                change_project_menu()
                return

            old_symbols = value[0] if isinstance(value, (list, tuple)) else int(value)
            today_goal = value[1] if isinstance(value, (list, tuple)) and len(value) > 1 else projects[
                selected_project].get('today_goal', 0)

            new_date = date
            new_symbols = old_symbols

            if what in ('1', '3'):
                new_date_input = input('Введите новую дату (дд.мм.гг): ')
                try:
                    _ = datetime.strptime(new_date_input, '%d.%m.%y')
                    new_date = new_date_input
                except ValueError:
                    print('Неверный формат даты. Дата не изменена.')
                    new_date = date

            if what in ('2', '3'):
                new_symbols_input = input('Введите новое кол-во символов: ')
                try:
                    new_symbols = int(new_symbols_input)
                except ValueError:
                    print('Неверное число символов. Кол-во символов не изменено.')
                    new_symbols = old_symbols

            # применяем изменения
            if new_date != date:
                del notes[date]
            notes[new_date] = [new_symbols, today_goal]

            projects[selected_project]['notes'] = notes
            projects[selected_project]['symbols'] = max(
                v[0] if isinstance(v, (list, tuple)) else int(v)
                for v in notes.values()
            )

            save_projects(projects)
            upd_projects()
            print('\nЗапись изменена.\n')
            change_project_menu()

        elif action == '2':
            del notes[date]
            projects[selected_project]['notes'] = notes
            if notes:
                projects[selected_project]['symbols'] = max(
                    v[0] if isinstance(v, (list, tuple)) else int(v)
                    for v in notes.values()
                )
            else:
                projects[selected_project]['symbols'] = 0
            save_projects(projects)
            upd_projects()
            print('\nЗапись удалена.\n')
            change_project_menu()
        else:
            print('\nДействие отменено.\n')
            change_project_menu()

    change_menu = {
        '1': delete_project,
        '2': change_name,
        '3': change_goal,
        '4': project_deadline,
        '5': edit_notes,
        '': main_menu
    }

    choice_for_change = input('Что вы хотите сделать?\n'
                              '1 - удалить проект\n'
                              '2 - переименовать проект\n'
                              '3 - изменить цель проекта\n'
                              '4 - изменить дедлайн проекта\n'
                              '5 - изменить/удалить запись проекта\n'
                              'Нажмите Enter для выхода в главное меню\n'
                              'Выбор: ')
    change_menu.get(choice_for_change, main_menu)()

def today_goals():
    pass

def load_game():
    try:
        with open('game_data.pkl', 'rb') as f:
            game_data = pickle.load(f)
            return game_data
    except FileNotFoundError:
        return None

def save_game(data):
    with open('game_data.pkl', 'wb') as f:
        pickle.dump(data, f)

def game_menu():
    about = ('\nИгровой режим это возможность повысить свою мотивацию'
             '\nДобавляя записи, вы зарабатываете 1 монету за каждые 100 символов'
             '\nЗа монеты можно купить Заморозки'
             '\nЗаморозки позволяют восстановить стрик и применяются автоматически,'
             '\nесли в какой-то день вы не выполнили цель.')
    print('\nИГРОВОЙ РЕЖИМ\n')
    if load_game() is None:
        print('Игровой режим не активирован\n'
              'Для активации игрового режима введите "1"\n'
              'Для выхода в основное меню нажмите Enter\n'
              'Для просмотра подробностей о режиме введите "?"\n')
        choice = input()
        if choice == '1':
            data = {'coins': 0,
                    'freeze': 0}
            save_game(data)
            print('\nИГРОВОЙ РЕЖИМ АКТИВИРОВАН!\n')
            game_menu()
        if choice == '':
            main_menu()
        if choice == '?':
            print(about)
    else:
        data = load_game()
        print(f'Монеты: {data['coins']}'
              f'\nЗаморозки: {data["freeze"]}')
        print('\nКупить заморозку (10 монет) - введите "*+"')
        if data['freeze'] > 0:
            print('Использовать заморозку - введите "*!"\n')
        print('Для просмотра подробностей о режиме введите "?"')
        print('Для редактирования параметров введите "*"')
        choice = input('Выбор: ')
        if choice == '*+':
            if data['coins'] < 10:
                print('\nНЕДОСТАТОЧНО МОНЕТ!\n')
                game_menu()
            else:
                data['coins'] -= 10
                data['freeze'] += 1
                save_game(data)
                print('\nЗАМОРОЗКА КУПЛЕНА\n')
                game_menu()
        if choice == '?':
            print(about)
            game_menu()
        if choice == '*':
            key = ''
            if input('Введите пароль:') == key:
                print('Выберите параметр для редактирования:')
                parameters = list(data.keys())
                for i in range(len(parameters)):
                    print(f'{i + 1} - {parameters[i]}')
                choice = int(input('Введите номер параметра: ')) - 1
                data[parameters[choice]] = int(input(f'Введите значение параметра {parameters[choice]}: '))
                save_game(data)
                print('/nПАРАМЕТР ИЗМЕНЕН/n')
                game_menu()
            else:
                print('\nПАРОЛЬ НЕВЕРНЫЙ! РЕДЖКТИРОВАНИЕ ПАРАМЕТРОВ НЕДОСТУПНО.\n')
                game_menu()


def main_menu():
    ch = False
    while ch == False:
        # Словарь функций: 1 — добавить запись
        menu = {
            '1': new_note,
            '2': view_projects,
            '3': new_project,
            '4': change_project_menu,
            '5': more_about_projects,
            '6': today_goals,
            '7': game_menu,
        }
        ch = input('nfprogress 0.8\n'
              '\n'
            'Что вы хотите сделать?\n'
            '1 - добавить запись\n'
            '2 - просмотреть список проектов\n'
            '3 - добавить проект\n'
            '4 - изменить проекты\n'
            '5 - посмотреть подробности проектов\n'
            '6 - посмотреть ежедневные цели\n'
            '7 - игровой режим'
            '\n'
            'Выбор: ')
        try:
            menu[ch]()
        except KeyError:
            print('\nНЕКОРРЕКТНЫЙ ВЫБОР\n')
            main_menu()


main_menu()
