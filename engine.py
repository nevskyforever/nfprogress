import json

def main_menu():
    ch = False
    while ch == False:
        # Словарь функций
        menu = {'1': view_projects, '2': new_project, '3': new_note, '4': delete_project}

        # Вывод меню
        ch = input('nfprogress 0.2.0\n'
              '\n'
            'Что вы хотите сделать?\n'
            '1 - просмотреть проекты\n'
            '2 - добавить проект\n'
            '3 - добавить запись\n'
            '4 - удалить проект\n'
            '\n'
            'Выбор: ')
        menu[ch]()
    pass

def read_file(filename='projects.json'):
    with open(filename, 'r') as f:
        content = f.read().strip()
        if not content:  # если файл пустой
            return {}
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
    projects[name] = [goal, '0']  # сохраняем как список
    write_file(projects)
    print('\n'
          'Проект сохранен'
          '\n')
    main_menu()

def view_projects():
    projects = read_file()
    if len(projects) == 0:
        print('Проектов пока нет.')
        main_menu()
    else:
        print('Список проектов:'
              '\n')
        for project_name, project_data in projects.items():
            goal = int(project_data[0])
            current = int(project_data[1])
            progress = round((current / goal) * 100) if goal > 0 else 0
            print(f'{project_name}: цель {goal}, написано: {progress}%')
            print()
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
    current_progress = int(projects[selected_project][1])
    new_progress = current_progress + int(new_symbols)
    projects[selected_project][1] = str(new_progress)

    write_file(projects)
    print('Запись добавлена.')
    main_menu()

main_menu()