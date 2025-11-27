import pickle
import locale
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

def read_file(filename='projects.pkl'):
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            return data
    except (FileNotFoundError, EOFError):
        # FileNotFoundError - файла нет
        # EOFError - файл пустой
        return {}

def write_file(data, filename='projects.pkl'):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

def new_project():
    import datetime
    projects = read_file()
    print('Создание проекта')
    name = input('Введите название: ')  # пробелы в подчеркивания
    goal = input('Введите цель (в символах): ')
    projects[name] = {'goal': int(goal),
                      'symbols': 0,
                      'progress': 0,
                      'notes': [],
                      'deadline': 'Нет',
                      'created': f'{datetime.date.today().strftime('%d.%m.%y')}'}  # сохраняем как словарь
    write_file(projects)
    print('\n'
          'Проект сохранен'
          '\n')
    main_menu()

def upd_projects():
    from datetime import datetime
    projects = read_file()

    # Подсчет прогресса
    for name, data in projects.items():
        total = 0
        notes = data['notes']
        for note in notes:
            total += note[0]
        projects[name]['symbols'] = total
    for name, data in projects.items():
        projects[name]['progress'] = (data['symbols'] / data['goal'] * 100) if data['goal'] > 0 else 0

    # Подсчет дней дедлайна
    for name, data in projects.items():
        deadline_str = data['deadline']
        if deadline_str == 'Нет':
            continue
        else:
            deadline = datetime.strptime(deadline_str, '%d.%m.%y')
            deadline_days = (deadline - datetime.today()).days
            if deadline_days > 0:
                projects[name]['deadline_days'] = deadline_days
                projects[name]['deadline_flag'] = 'ВРЕМЯ ЕСТЬ'
            else:
                projects[name]['deadline_days'] = 0
                projects[name]['deadline_flag'] = 'ПРОСРОЧЕН!'

    write_file(projects)

def view_projects():
    projects = read_file()
    if len(projects) == 0:
        print('Проектов пока нет.\n')
        main_menu()
    else:
        print('Список проектов:\n')
        for name, data in projects.items():
            goal = data['goal']
            symbols = data['symbols']
            progress = data['progress']
            last_note = data['notes'][-1]
            last_note = f'{last_note[1]}'
            if data['deadline'] != 'Нет':
                print(f'Название: {name}, цель: {goal}, прогресс: {symbols}/{goal} ({progress:.1f}%),'
                      f' дедлайн: {data["deadline"]} - {data["deadline_flag"]}, '
                      f'дата последней записи: {last_note}')
            else:
                print(f'Название: {name}, цель: {goal}, прогресс: {symbols}/{goal} ({progress:.1f}%),'
                      f' дедлайн: {data["deadline"]}')
        print()
        choice = input('Нажмите Enter для возврата в главное меню: ')
        if choice == '':
            main_menu()

def more_about_projects():
    from datetime import datetime
    print('Детальный просмотр проекта\n')
    projects = read_file()
    project_name = choice_project()

    # Получаем данные выбранного проекта
    project_data = projects[project_name]

    last_note = project_data['notes'][-1]
    last_note = f'{last_note[1]} - {last_note[0]} символов'

    print(f'Название: {project_name}')

    if project_data["deadline"] != 'Нет':
        if project_data['deadline_days'] > 0:
            print(f'Дедлайн: {project_data["deadline"]} - осталось {project_data['deadline_days']} дней')
        else:
            print(f'Дедлайн: {project_data["deadline"]} - {project_data["deadline_flag"]}')
        print(f'Прогресс: {project_data["progress"]:.1f}%')
        print(f'Цель/написано: {project_data["goal"]}/{project_data["symbols"]}')
        print(f'Дата создания: {project_data["created"]}')
        print(f'Последняя запись: {last_note}')
        print(f'Кол-во записей: {len(project_data["notes"])}')
        print(f'Среднее кол-во символов в записи: {int(project_data["symbols"] / len(project_data["notes"]))} символов\n')
    else:
        print(f'Дедлайн: {project_data['deadline']}')
        print(f'Прогресс: {project_data["progress"]:.1f}%')
        print(f'Цель/написано: {project_data["goal"]}/{project_data["symbols"]}')
        print(f'Дата создания: {project_data["created"]}')
        print(f'Последняя запись: {last_note}')
        print(f'Кол-во записей: {len(project_data["notes"])}')
        print(f'Среднее кол-во символов в записи: {int(project_data["symbols"] / len(project_data["notes"]))} символов\n')

    ext = input('Нажмите Enter для выхода в меню выбора проектов\n'
                'Для просмотра записей выбранного проекта введите "1": ')
    if ext == '':
        more_about_projects()
    else:
        print(f'Просмотр записей {project_name}\n')

        # Проверяем записи только выбранного проекта
        if len(project_data['notes']) == 0:
            print('Записей пока нет\n')
            more_about_projects()
        else:
            # Выводим ВСЕ записи сразу
            for i, note in enumerate(project_data['notes'], 1):
                print(f'{i}. {note[1]}: {note[0]} символов')

            # Запрос выхода только после показа всех записей
            cancel = input('\nНажмите Enter для возврата в меню проектов: ')
            if cancel == '':
                more_about_projects()

def choice_project():
    # Создаем нумерованный список проектов (с правильными названиями)
    projects = read_file()
    if len(projects) == 0:
        print('Проектов пока нет\n')
        main_menu()
    project_list = list(projects.keys())
    print('Ваши проекты:\n')
    for i, project_name in enumerate(project_list, 1):
        # Показываем названия с пробелами для пользователя
        display_name = project_name.replace('_', ' ')
        print(f"{i} - {display_name}")

    print()
    choice = input('Введите номер проекта или нажмите Enter для выхода: ')
    if choice == '':
        main_menu()
    # Получаем выбранный проект (оригинальный ключ с _)
    selected_project = project_list[int(choice) - 1]
    return selected_project

def new_note():
    from datetime import datetime

    projects = read_file()

    print('\nДобавление записи\n')

    selected_project = choice_project()

    # Добавляем запись в список проекта
    new_symbols = input('Введите кол-во символов или нажмите Enter для выхода: ')
    if new_symbols == '':
        main_menu()

    # Обновляем прогресс

    notes = projects[selected_project]['notes']
    notes.append([int(new_symbols), datetime.now().strftime('%d.%m.%y %H:%M')])
    projects[selected_project]['notes'] = notes

    write_file(projects)
    upd_projects()

    print('Запись добавлена.')
    main_menu()

def change_project_menu():

    def delete_project():
        print('Удаление проекта\n')
        projects = read_file()
        selected_project = choice_project()
        done = input('Подтвердите удаление (нажмите Enter для отмены или введите "1" для удаления): ')
        if done == '1':
            del projects[selected_project]
            write_file(projects)
            print('\nПроект удален\n')
            change_project_menu()
        else:
            print('\nУдаление отменено\n')
        change_project_menu()

    def change_name():
        projects = read_file()
        print('Переименование проекта\n')
        selected_project = choice_project()
        new_name = input('Введите новое имя проекта: ')
        projects[new_name] = projects[selected_project]
        del projects[selected_project]
        write_file(projects)
        print('\nИмя проекта успешно изменено\n')
        change_project_menu()

    def change_goal():
        projects = read_file()
        print('Изменение цели проекта')
        selected_project = choice_project()
        projects[selected_project]['goal'] = int(input('Введите новую цель (в символах): '))
        upd_projects()
        write_file(projects)
        print(f'\nЦель {selected_project} успешно изменена!\n')
        change_project_menu()

    def project_deadline():
        from datetime import datetime
        from datetime import timedelta
        print('Установка/изменение дедлайна\n')
        projects = read_file()
        selected_project = choice_project()
        date_input = input('Введите дату (дд.мм.гг) / количество дней (число) или нажмите Enter для ее удаления: ')
        if date_input == '':
            projects[selected_project]['deadline'] = 'Нет'
            write_file(projects)
            print('\nДедлайн удален\n')
            change_project_menu()
        else:
            if date_input.isdigit():
                deadline = datetime.now() + timedelta(days=int(date_input))
                deadline = deadline.strftime('%d.%m.%y')
                projects[selected_project]['deadline'] = deadline
                write_file(projects)
                print('Дата дедлайна сохранена!')
                change_project_menu()
            else:
                given_date = datetime.strptime(date_input, '%d.%m.%y')
                deadline = given_date.strftime('%d.%m.%y')
                projects[selected_project]['deadline'] = deadline
                write_file(projects)
                print('Дата дедлайна сохранена!')
                change_project_menu()

    change_menu = {'1': delete_project, '2': change_name, '3': change_goal, '4': project_deadline, '': main_menu}

    choice_for_change = input('Что вы хотите сделать?\n'
                              '1 - удалить проект\n'
                              '2 - переименовать проект\n'
                              '3 - изменить цель проекта\n'
                              '4 - изменить дедлайн проекта\n'
                              'Нажмите Enter для выхода в главное меню\n'
                              'Выбор: ')

    change_menu[choice_for_change]()

def main_menu():
    upd_projects()
    ch = False
    while ch == False:
        # Словарь функций
        menu = {'1': view_projects, '2': new_project, '3': new_note, '4': change_project_menu, '5': more_about_projects}

        # Вывод меню
        ch = input('nfprogress 0.6.7\n'
              '\n'
            'Что вы хотите сделать?\n'
            '1 - просмотреть список проектов\n'
            '2 - добавить проект\n'
            '3 - добавить запись\n'
            '4 - изменить проекты\n'
            '5 - посмотреть подробности проектов\n'
            '\n'
            'Выбор: ')
        menu[ch]()

main_menu()