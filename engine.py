import math
from datetime import datetime

projects = {}


def calc_progress(records, goal):
    """Рассчитывает прогресс проекта"""
    total = sum(r["count"] for r in records)
    progress = math.ceil(total / goal * 100) if goal > 0 else 0
    return progress, total


def add_record(project_data, goal):
    """Добавляет запись о прогрессе"""
    try:
        new_entry = int(input("Введите количество написанных символов: "))
        if new_entry < 0:
            print("Количество символов не может быть отрицательным!")
            return False

        records = project_data[goal]
        records.append({
            "count": new_entry,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        progress, total = calc_progress(records, goal)
        print(f"Текущий прогресс: {progress}% ({total}/{goal})")
        return True
    except ValueError:
        print("Введите корректное число!")
        return False


def view_records(project_data, goal):
    """Просматривает записи проекта"""
    records = project_data[goal]
    print("\nЗаписи проекта:")
    if not records:
        print("Пока нет записей.")
    else:
        for i, r in enumerate(records, 1):
            print(f"  {i}) {r['count']} символов | Дата: {r['datetime']}")


def delete_record(project_data, goal):
    """Удаляет запись проекта"""
    records = project_data[goal]
    if not records:
        print("Нет записей для удаления.")
        return False

    view_records(project_data, goal)

    try:
        del_index = int(input("Введите номер записи для удаления: "))
        if del_index < 1 or del_index > len(records):
            print("Неверный номер записи!")
            return False

        removed = records.pop(del_index - 1)
        print(f"Удалена запись: {removed['count']} символов | {removed['datetime']}")
        return True
    except ValueError:
        print("Введите корректный номер!")
        return False


def delete_project(data, selected_project):
    """Удаляет проект"""
    confirm = input(f"Вы уверены, что хотите удалить проект '{selected_project}'? (y/n): ").lower()
    if confirm == 'y':
        del data[selected_project]
        print(f"Проект '{selected_project}' удалён.")
        return True
    return False


def project_progress(data):
    """Управление прогрессом проекта"""
    if not data:
        print("Нет проектов для управления!")
        return

    # Словарь функций для управления проектом
    project_actions = {
        '1': add_record,
        '2': view_records,
        '3': delete_record,
        '4': delete_project
    }

    print("Доступные проекты:")
    for i, (name, info) in enumerate(data.items(), 1):
        goal = list(info.keys())[0]
        records = info[goal]
        progress, total = calc_progress(records, goal)
        print(f'№{i} Название: {name} Цель: {goal} символов Прогресс: {progress}% ({total}/{goal})')

    try:
        project_names = list(data.keys())
        fp = int(input('Введите номер проекта из списка: '))
        if fp < 1 or fp > len(project_names):
            print("Неверный номер проекта!")
            return
        selected_project = project_names[fp - 1]
    except ValueError:
        print("Введите корректный номер!")
        return

    goal = list(data[selected_project].keys())[0]
    project_data = data[selected_project]

    while True:
        print("\n1 - Добавить запись")
        print("2 - Просмотреть записи")
        print("3 - Удалить запись")
        print("4 - Удалить проект")
        print("5 - Вернуться в меню")
        action = input("Выберите действие (1-5): ").strip()

        if action == '5':
            break

        if action in project_actions:
            if action in ['1', '2', '3']:
                # Для действий с записями передаем project_data и goal
                if action == '1':
                    project_actions[action](project_data, goal)
                elif action == '2':
                    project_actions[action](project_data, goal)
                elif action == '3':
                    project_actions[action](project_data, goal)
            elif action == '4':
                # Для удаления проекта передаем data и selected_project
                if project_actions[action](data, selected_project):
                    break
        else:
            print("Неверный выбор!")


def projects_view(data):
    """Отображает обзор всех проектов"""
    print('\n' + '=' * 50)
    print('ОБЗОР ПРОЕКТОВ')
    print('=' * 50)

    if not data:
        print("Проектов пока нет")
    else:
        for i, (name, info) in enumerate(data.items(), 1):
            goal = list(info.keys())[0]
            records = info[goal]
            progress, total = calc_progress(records, goal)
            status = "✅ ВЫПОЛНЕН" if progress >= 100 else "📝 В РАБОТЕ"
            print(f'№{i} {status} | {name} | Прогресс: {progress}% ({total}/{goal})')

    print('\n' + '-' * 50)


def project_add(data):
    """Добавляет новый проект"""
    while True:
        print('\n' + '-' * 30)
        print('ДОБАВЛЕНИЕ НОВОГО ПРОЕКТА')
        print('-' * 30)

        name = input('Введите название проекта: ').strip()
        if not name:
            print("Название проекта не может быть пустым!")
            continue
        if name in data:
            print("Проект с таким названием уже существует!")
            continue

        try:
            goal = int(input('Введите цель (количество символов): '))
            if goal <= 0:
                print("Цель должна быть положительным числом!")
                continue
        except ValueError:
            print("Введите корректное число!")
            continue

        data[name] = {goal: []}
        print(f'✅ Проект "{name}" успешно создан!')

        another = input('\nДобавить еще один проект? (y/n): ').lower()
        if another != 'y':
            break


def main_menu():
    """Главное меню программы"""
    # Словарь функций главного меню
    menu_actions = {
        '1': project_progress,
        '2': project_add
    }

    while True:
        projects_view(projects)

        print("\nЧто вы хотите сделать?")
        print("1 - Управление проектом (добавить/просмотреть/удалять)")
        print("2 - Добавить новый проект")
        print("3 - Выйти из программы")

        choice = input("\nВведите номер действия (1-3): ").strip()

        if choice == '3':
            print("До свидания!")
            break

        if choice in menu_actions:
            menu_actions[choice](projects)
        else:
            print("Неверный выбор! Пожалуйста, введите 1, 2 или 3")


if __name__ == "__main__":
    main_menu()