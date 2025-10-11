import math

projects = []

def project_progress(data):
    if len(data) == 0:
        print("Нет проектов для добавления записей!")
        projects_view(data)
        return

    print("Доступные проекты:")
    for i in range(len(data)):
        print(f'№{i} Название: {data[i][1]} Цель: {data[i][2]} Написано: {data[i][3]}')

    try:
        fp = int(input('Введите номер проекта из списка: '))
        if fp < 0 or fp >= len(data):
            print("Неверный номер проекта!")
            project_progress(data)
            return
    except ValueError:
        print("Введите корректный номер!")
        project_progress(data)
        return

    while True:
        # Добавляем новую запись
        new_entry = int(input("Введите количество написанных символов: "))
        data[fp].append(new_entry)

        # Пересчитываем прогресс
        total_written = sum(data[fp][3:])
        result = math.ceil(total_written / data[fp][2] * 100)  # Процент выполнения
        data[fp][3] = result  # Обновляем прогресс

        flag = input('Хотите добавить еще одну запись? (y/n): ')
        if flag.lower() != 'y':
            break

    projects_view(data)


def projects_view(data):
    print('\nВаши проекты: ')
    if len(data) == 0:
        print("Проектов пока нет")

    for i in range(len(data)):
        print(f'№{i} Название: {data[i][1]} Цель: {data[i][2]} символов Прогресс: {data[i][3]}%')

    flag_new = input('\nДобавить проект? (y/n): ')
    if flag_new.lower() == 'y':
        project_add(data)
    else:
        flag_add = input('Добавить запись в проект? (y/n): ')
        if flag_add.lower() == 'y':
            project_progress(data)


def project_add(data):
    while True:
        # Создаем новый проект
        name = input('Введите название проекта: ')

        try:
            goal = int(input('Введите цель (количество символов): '))
        except ValueError:
            print("Введите корректное число!")
            continue

        # Структура проекта: [индекс, название, цель, прогресс%]
        new_project = [len(data), name, goal, 0]
        data.append(new_project)

        print('Проект сохранен!')

        another = input('Добавить еще проект? (y/n): ')
        if another.lower() != 'y':
            break

    projects_view(data)

# Запуск программы
projects_view(projects)