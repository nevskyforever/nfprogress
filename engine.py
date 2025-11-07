import json

def read_file(filename='projects.json'):
    with open(filename, 'r') as f:
        content = f.read().strip()
        if not content:  # если файл пустой
            return {}
        f.seek(0)
        data = json.load(f)
        return data

def write_file(data, filename='projects.json'):
    with open(filename, 'w') as f:
        json.dump(data, f)

def new_project():
    projects = read_file()
    print('Создание проекта')
    name = input('Введите название: ').replace(' ', '_')  # пробелы в подчеркивания
    goal = input('Введите цель (в символах): ')
    projects[name] = {'goal': int(goal), 'symbols': 0, 'progress': 0}  # сохраняем как список
    write_file(projects)
    print('\n'
          'Проект сохранен'
          '\n')
    main_menu()

def view_projects():
    projects = read_file()
    if len(projects) == 0:
        print('Проектов пока нет.\n')
    else:
        print('Список проектов:\n')
        for name, data in projects.items():
            display_name = name.replace('_', ' ')
            goal = data['goal']
            symbols = data['symbols']
            progress = (symbols / goal * 100) if goal > 0 else 0
            print(f'Название: {display_name}, цель: {goal}, прогресс: {symbols}/{goal} ({progress:.1f}%)')
        print()
        choice = input('Вернуться в главное меню? (введите 0): ')
        if choice == '0':
            main_menu()

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
    projects = read_file()

    print('\nДобавление записи\n')

    selected_project = choice_project()

    # Добавляем запись в список проекта
    new_symbols = input('Введите кол-во символов или "0" для выхода: ')
    if new_symbols == '0':
        main_menu()

    # Обновляем прогресс
    projects[selected_project]['symbols'] = int(projects[selected_project]['symbols']) + int(new_symbols)

    write_file(projects)
    print('Запись добавлена.')
    main_menu()

def change_project_menu():

    def delete_project():
        print('Удаление проекта\n')
        projects = read_file()
        selected_project = choice_project()
        del projects[selected_project]
        write_file(projects)
        print('Проект удален')
        change_project_menu()

    def change_name():
        projects = read_file()
        print('Переименование проекта\n')
        selected_project = choice_project()
        new_name = input('Введите новое имя проекта: ')
        projects[new_name] = projects[selected_project]
        del projects[selected_project]
        write_file(projects)
        print('Имя проекта успешно изменено')
        change_project_menu()

    def change_goal():
        projects = read_file()
        print('Изменение цели проекта')
        selected_project = choice_project()
        projects[selected_project]['goal'] = int(input('Введите новую цель (в символах): '))
        write_file(projects)
        print(f'Цель {selected_project} успешно изменена!')
        change_project_menu()

    change_menu = {'1': delete_project, '2': change_name, '3': change_goal, '4': main_menu}

    choice_for_change = input('Что вы хотите сделать?\n'
                              '1 - удалить проект\n'
                              '2 - переименовать проект\n'
                              '3 - изменить цель проекта\n'
                              '4 - выйти в главное меню\n'
                              'Выбор: ')

    change_menu[choice_for_change]()

def main_menu():
    ch = False
    while ch == False:
        # Словарь функций
        menu = {'1': view_projects, '2': new_project, '3': new_note, '4': change_project_menu}

        # Вывод меню
        ch = input('nfprogress 0.3.1.3\n'
              '\n'
            'Что вы хотите сделать?\n'
            '1 - просмотреть проекты\n'
            '2 - добавить проект\n'
            '3 - добавить запись\n'
            '4 - изменить проекты'
            '\n'
            'Выбор: ')
        menu[ch]()

main_menu()