def main_menu():
    # Словарь функций
    menu = {'1': view_project, '2': new_note}

    # Вывод меню
    print('nfprogress 0.0.1')
    print('Что вы хотите сделать?')
    print()
    print('1 - просмотреть проекты')
    print('2 - добавить запись')

    # Выбор пункта
    ch = input()
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
    with open('projects.txt', '') as f:
        data = f.readlines()
        if data:
            projects_lines = [line.replace('\n', '') for line in data]
            for project in projects_lines:
                pr_out = project.split(' ')
                written = round(sum([int(i) for i in pr_out[2:]]) / int(pr_out[1]) * 100)
                print(f'Название: {pr_out[0]}, цель: {pr_out[1]}, написано: {written}%')
            choice = input('Что вы хотите сделать?')
            menu = {'1': new_note, '2': main_menu}
            menu[choice]()
        else:
            print('Проектов пока нет')
            menu = {'д': new_project, 'н': view_project}
            ch = input('Создать первый проект? (д/н): ')
            menu[ch]()

def open_project():
    pass

def delete_project():
    pass


def new_note():
    pass