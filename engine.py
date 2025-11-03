def read_file(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        data = f.readlines()
        if data:
            projects_lines = [line.replace('\n', '') for line in data]
            return projects_lines
    return []  # обязательно возвращаем пустой список

def write_file(filename, pr_out):
    with open(filename, 'w', encoding='UTF-8') as f:
        f.write(pr_out)

def main_menu():
    ch = False
    while ch == False:
        # Словарь функций
        menu = {'1': view_projects, '2': new_project}

        # Вывод меню
        ch = input('nfprogress 0.0.2\n'
              '\n'
            'Что вы хотите сделать?\n'
            '1 - просмотреть проекты\n'
            '2 - добавить проект\n'
            '\n'
            'Выбор: ')
        if ch in menu:
            menu[ch]()
        else:
            print('Неверный выбор')
            main_menu()

def new_project():
    print('Новый проект')
    name = input('Название: ')
    goal = input('Цель (в символах): ')

    with open('projects.txt', 'a', encoding='utf-8') as f:
        f.write(f"{name} {goal}\n")

    print('Проект сохранен.')

    main_menu()

def view_projects():
    projects = read_file('projects.txt')
    if projects:
        for project in projects:
            pr_out = project.split(' ')
            if len(pr_out) >= 2:  # проверяем что есть хотя бы название и цель
                if len(pr_out) > 2:  # если есть написанные символы
                    written = round(sum([int(i) for i in pr_out[2:]]) / int(pr_out[1]) * 100)
                else:  # если нет написанных символов
                    written = 0
                print(f'Название: {pr_out[0]}, цель: {pr_out[1]}, написано: {written}%')
        choice = input('Что вы хотите сделать?\n'
                       '1 - новая запись\n'
                       '2 - выйти в меню\n'
                       '\n'
                       'Выбор: ')
        menu = {'1': new_note, '2': main_menu}
        if choice in menu:
            menu[choice]()
    else:
        print('Проектов пока нет')
        menu = {'д': new_project, 'н': main_menu}
        ch = input('Создать первый проект? (д/н): ')
        if ch in menu:
            menu[ch]()

def open_project():
    pass

def delete_project():
    pass

def new_note():
    pass

main_menu()