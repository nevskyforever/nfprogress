import math

projects = {}


def project_progress(data):
    if len(data) == 0:
        print("Нет проектов для добавления записей!")
        return

    print("Доступные проекты:")
    for i, (name, details) in enumerate(data.items(), 1):
        goal, current = details
        progress = math.ceil(current / goal * 100) if goal > 0 else 0
        print(f'№{i} Название: {name} Цель: {goal} символов Прогресс: {progress}% ({current}/{goal})')

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

    while True:
        try:
            new_entry = int(input("Введите количество написанных символов: "))
            if new_entry < 0:
                print("Количество символов не может быть отрицательным!")
                continue

            # Обновляем текущий результат
            data[selected_project][1] += new_entry

            # Пересчитываем прогресс
            total_written = data[selected_project][1]
            goal = data[selected_project][0]
            result = math.ceil(total_written / goal * 100) if goal > 0 else 0

            print(f"Текущий прогресс: {result}% ({total_written}/{goal})")

            flag = input('Хотите добавить еще одну запись? (y/n): ')
            if flag.lower() != 'y':
                break
        except ValueError:
            print("Введите корректное число!")


def projects_view(data):
    print('\n' + '=' * 50)
    print('ОБЗОР ПРОЕКТОВ')
    print('=' * 50)

    if len(data) == 0:
        print("Проектов пока нет")
    else:
        for i, (name, details) in enumerate(data.items(), 1):
            goal, current = details
            progress = math.ceil(current / goal * 100) if goal > 0 else 0
            status = "✅ ВЫПОЛНЕН" if progress >= 100 else "📝 В РАБОТЕ"
            print(f'№{i} {status} | {name} | Прогресс: {progress}% ({current}/{goal})')

    print('\n' + '-' * 50)


def main_menu():
    while True:
        projects_view(projects)

        print("\nЧто вы хотите сделать?")
        print("1 - Добавить запись в проект")
        print("2 - Добавить новый проект")
        print("3 - Выйти из программы")

        choice = input("\nВведите номер действия (1-3): ").strip()

        if choice == '1':
            project_progress(projects)
        elif choice == '2':
            project_add(projects)
        elif choice == '3':
            print("До свидания!")
            break
        else:
            print("Неверный выбор! Пожалуйста, введите 1, 2 или 3")


def project_add(data):
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

        # Структура: {название: [цель, текущий_результат]}
        data[name] = [goal, 0]
        print(f'✅ Проект "{name}" успешно создан!')

        another = input('\nДобавить еще один проект? (y/n): ').lower()
        if another != 'y':
            break
    # Убрана рекурсивная функция projects_view(data) - возвращаем управление в main_menu


# Запуск программы
if __name__ == "__main__":
    main_menu()