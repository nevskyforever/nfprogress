import pickle

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
                      'notes': [],
                      'deadline': 'Нет',
                      'created': f'{datetime.date.today().strftime('%d.%m.%Y')}'}  # сохраняем как словарь
    write_file(projects)
    print('\n'
          'Проект сохранен'
          '\n')
    main_menu()

def calculate_progress():
    projects = read_file()
    for name, data in projects.items():
        total = 0
        notes = data['notes']
        for note in notes:
            total += note[0]
        projects[name]['symbols'] = total
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
            progress = (symbols / goal * 100) if goal > 0 else 0
            print(f'Название: {name}, цель: {goal}, прогресс: {symbols}/{goal} ({progress:.1f}%),'
                  f' дедлайн: {data["deadline"]}')
        print()
        choice = input('Вернуться в главное меню? (введите 0): ')
        if choice == '0':
            main_menu()

def more_about_projects():
    from datetime import datetime
    print('Детальный просмотр проекта\n')
    projects = read_file()
    project_name = choice_project()  # choice_project возвращает имя проекта (строку)

    # Получаем данные проекта по имени
    project_data = projects[project_name]

    # Отображаем название с пробелами вместо подчеркиваний
    display_name = project_name.replace('_', ' ')

    print(f'\nНазвание: {display_name}')
    print(f'Цель/написано: {project_data["goal"]}/{project_data["symbols"]}')

    # Проверяем наличие дедлайна
    if 'deadline' not in project_data or project_data['deadline'] == 'Нет':
        print('Дедлайн: не установлен')
    else:
        # Преобразуем строку с дедлайном в объект datetime
        deadline_date = datetime.strptime(project_data['deadline'], '%d.%m.%Y').date()
        today = datetime.today().date()

        # Считаем разницу в днях
        days_difference = (deadline_date - today).days

        if days_difference > 0:
            print(f'Дедлайн: осталось {days_difference} дней')
        elif days_difference < 0:
            print(f'Дедлайн: просрочен на {days_difference} дней')
        else:
            print('Дедлайн: сегодня!')

    print(f'Дата создания: {project_data["created"]}\n')

    ext = int(input('Для выхода меню выбора проектов введите "0": '))
    if ext == 0:
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
    choice = input('Введите номер проекта или "0" для выхода: ')
    if choice == '0':
        main_menu()
    # Получаем выбранный проект (оригинальный ключ с _)
    selected_project = project_list[int(choice) - 1]
    return selected_project

def new_note():
    import datetime

    projects = read_file()

    print('\nДобавление записи\n')

    selected_project = choice_project()

    # Добавляем запись в список проекта
    new_symbols = input('Введите кол-во символов или "0" для выхода: ')
    if new_symbols == '0':
        main_menu()

    # Обновляем прогресс

    notes = projects[selected_project]['notes']
    notes.append([int(new_symbols), datetime.date.today().strftime('%d.%m.%Y')])
    projects[selected_project]['notes'] = notes

    write_file(projects)
    calculate_progress()

    print('Запись добавлена.')
    main_menu()

def change_project_menu():

    def delete_project():
        print('Удаление проекта\n')
        projects = read_file()
        selected_project = choice_project()
        done = int(input('Подтвердите удаление (введите 0 для отмены или 1 для удаления): '))
        if done == 1:
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
        calculate_progress()
        write_file(projects)
        print(f'\nЦель {selected_project} успешно изменена!\n')
        change_project_menu()

    def project_deadline():
        from datetime import datetime
        print('Установка/изменение дедлайна\n')
        projects = read_file()
        selected_project = choice_project()
        date_input = input('Введите дату (дд.мм.гггг) или "0" для ее удаления: ')
        if date_input == '0':
            projects[selected_project]['deadline'] = 'Нет'
            write_file(projects)
            print('\nДедлайн удален\n')
            change_project_menu()
        else:
            given_date = datetime.strptime(date_input, '%d.%m.%Y')
            deadline = given_date.strftime('%d.%m.%Y')
            projects[selected_project]['deadline'] = deadline
            write_file(projects)
            change_project_menu()

    change_menu = {'1': delete_project, '2': change_name, '3': change_goal, '4': project_deadline, '0': main_menu}

    choice_for_change = input('Что вы хотите сделать?\n'
                              '1 - удалить проект\n'
                              '2 - переименовать проект\n'
                              '3 - изменить цель проекта\n'
                              '4 - изменить дедлайн проекта\n'
                              '0 - выйти в главное меню\n'
                              'Выбор: ')

    change_menu[choice_for_change]()

def main_menu():
    ch = False
    while ch == False:
        # Словарь функций
        menu = {'1': view_projects, '2': new_project, '3': new_note, '4': change_project_menu, '5': more_about_projects}

        # Вывод меню
        ch = input('nfprogress 0.5.1\n'
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