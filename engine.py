import json

def main_menu():
    ch = False
    while ch == False:
        # Словарь функций
        menu = {'1': view_projects, '2': new_project, '3': new_note}

        # Вывод меню
        ch = input('nfprogress 0.3.0\n'
              '\n'
            'Что вы хотите сделать?\n'
            '1 - просмотреть проекты\n'
            '2 - добавить проект\n'
            '3 - добавить запись\n'
            '\n'
            'Выбор: ')
        menu[ch]()
    pass

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

def delete_project():
    projects = read_file()

    print('Удаление проекта\n')

    selected_project = choice_project()

    del projects[selected_project]

    write_file(projects)

    print('Проект удален')

    main_menu()

def new_note():
    projects = read_file()

    print('\nДобавление записи\n')

    selected_project = choice_project()

    # Добавляем запись в список проекта
    new_symbols = input('Введите кол-во символов: ')

    # Обновляем прогресс
    projects[selected_project]['symbols'] = int(projects[selected_project]['symbols']) + int(new_symbols)

    write_file(projects)
    print('Запись добавлена.')
    main_menu()

main_menu()