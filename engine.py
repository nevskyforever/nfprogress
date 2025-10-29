import math
from datetime import datetime
import json
import os

PROJECTS_FILE = "projects.txt"
projects = {}


def show_menu(title, options, show_back_option=True):
    """Универсальная функция для отображения меню"""
    print(f'\n{"-" * 30}')
    print(title)
    print('-' * 30)

    for key, description in options.items():
        print(f"{key} - {description}")

    if show_back_option:
        last_key = str(len(options) + 1)
        print(f"{last_key} - Вернуться назад")
        return last_key
    return None


def get_user_choice(max_value, prompt="Выберите действие: "):
    """Получает и проверяет выбор пользователя"""
    try:
        choice = input(prompt).strip()
        if 1 <= int(choice) <= max_value:
            return choice
        print(f"Неверный выбор! Введите число от 1 до {max_value}")
        return None
    except ValueError:
        print("Введите корректное число!")
        return None


def load_projects():
    """Загружает проекты из файла"""
    global projects
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем ключи целей обратно в int (при сохранении в JSON они становятся str)
                converted_data = {}
                for project_name, project_info in data.items():
                    for goal_str, records in project_info.items():
                        converted_data[project_name] = {int(goal_str): records}
                projects = converted_data
            print("✅ Данные проектов загружены!")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"⚠️ Ошибка загрузки файла: {e}. Будет создан новый файл.")
            projects = {}
    else:
        print("📁 Файл projects.txt не найден. Будет создан новый при сохранении.")


def save_projects():
    """Сохраняет проекты в файл"""
    try:
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
        print("✅ Данные проектов сохранены!")
    except Exception as e:
        print(f"❌ Ошибка сохранения файла: {e}")


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

        # Сохраняем изменения
        save_projects()
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

        # Сохраняем изменения
        save_projects()
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

        # Сохраняем изменения
        save_projects()
        return True
    return False


def select_project(data):
    """Выбор проекта из списка"""
    if not data:
        print("Нет проектов для управления!")
        return None

    print("Доступные проекты:")
    for i, (name, info) in enumerate(data.items(), 1):
        goal = list(info.keys())[0]
        records = info[goal]
        progress, total = calc_progress(records, goal)
        print(f'№{i} Название: {name} Цель: {goal} символов Прогресс: {progress}% ({total}/{goal})')

    try:
        project_names = list(data.keys())
        choice = get_user_choice(len(project_names), "Введите номер проекта из списка: ")
        if not choice:
            return None

        selected_project = project_names[int(choice) - 1]
        return selected_project
    except (ValueError, IndexError):
        print("Ошибка выбора проекта!")
        return None


def project_progress(data):
    """Управление прогрессом проекта"""
    selected_project = select_project(data)
    if not selected_project:
        return

    goal = list(data[selected_project].keys())[0]
    project_data = data[selected_project]

    # Словарь функций для управления проектом
    project_actions = {
        '1': add_record,
        '2': view_records,
        '3': delete_record,
        '4': delete_project
    }

    # Опции меню управления проектом
    project_options = {
        '1': 'Добавить запись',
        '2': 'Просмотреть записи',
        '3': 'Удалить запись',
        '4': 'Удалить проект'
    }

    while True:
        back_key = show_menu("УПРАВЛЕНИЕ ПРОЕКТОМ", project_options)

        choice = get_user_choice(len(project_options))
        if not choice:
            continue

        if choice == back_key:
            break

        if choice in project_actions:
            if choice in ['1', '2', '3']:
                # Для действий с записями передаем project_data и goal
                project_actions[choice](project_data, goal)
            elif choice == '4':
                # Для удаления проекта передаем data и selected_project
                if project_actions[choice](data, selected_project):
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
        show_menu("ДОБАВЛЕНИЕ НОВОГО ПРОЕКТА", {}, show_back_option=False)

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

        # Сохраняем изменения
        save_projects()

        another = input('\nДобавить еще один проект? (y/n): ').lower()
        if another != 'y':
            break


def main_menu():
    """Главное меню программы"""
    # Загружаем проекты при запуске
    load_projects()

    # Опции главного меню
    main_options = {
        '1': 'Управление проектом (добавить/просмотреть/удалять)',
        '2': 'Добавить новый проект'
    }

    while True:
        projects_view(projects)

        back_key = show_menu("ГЛАВНОЕ МЕНЮ", main_options, show_back_option=False)

        choice = get_user_choice(len(main_options), "Введите номер действия (1-3): ")
        if not choice:
            continue

        if choice == '1':
            project_progress(projects)
        elif choice == '2':
            project_add(projects)
        elif choice == '3':
            # Сохраняем перед выходом
            save_projects()
            print("✅ Данные сохранены. До свидания!")
            break
        else:
            print("Неверный выбор! Пожалуйста, введите 1, 2 или 3")


if __name__ == "__main__":
    main_menu()