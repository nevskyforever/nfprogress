import pickle
import locale

# Устанавливаем русскую локаль для корректного отображения дат и чисел
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛОМ
# ============================================================================

def read_file(filename='projects.pkl'):
    """
    Загружает данные проектов из pickle-файла.
    Если файл не найден или пустой, возвращает пустой словарь.
    """
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            return data
    except (FileNotFoundError, EOFError):
        # Если файла нет или он повреждён, начинаем с нуля
        return {}


def write_file(data, filename='projects.pkl'):
    """
    Сохраняет данные проектов в pickle-файл.
    Перезаписывает файл полностью каждый раз.
    """
    with open(filename, 'wb') as f:
        pickle.dump(data, f)


# ============================================================================
# ФУНКЦИИ СОЗДАНИЯ И РЕДАКТИРОВАНИЯ ПРОЕКТОВ
# ============================================================================

def new_project():
    """
    Создаёт новый проект.
    Запрашивает:
    - название проекта
    - цель в символах
    - опциональный дедлайн (дата или количество дней вперёд)
    """
    import datetime
    from datetime import timedelta

    projects = read_file()
    print('Создание проекта')

    # Получаем название и цель от пользователя
    name = input('Введите название: ')
    goal = input('Введите цель (в символах): ')

    # Создаём базовую структуру проекта
    projects[name] = {
        'goal': int(goal),  # Целевое количество символов
        'symbols': 0,  # Текущее количество (макс из записей)
        'progress': 0,  # Процент выполнения (0-100%)
        'notes': {},  # Записи в формате {дата: [символы, daily_goal]}
        'streak': 0,  # Текущая серия дней активности
        'max_streak': 0,  # Максимальная серия активности
        'deadline': 'Нет',  # Дедлайн проекта (дд.мм.гг или 'Нет')
        'created': f'{datetime.date.today().strftime("%d.%m.%y")}'  # Дата создания
    }

    # Предложение установить дедлайн
    date_input = input('Введите дату дедлайна (дд.мм.гг) / количество дней (число)\n'
                       'или нажмите Enter, чтобы пропустить: ')

    if date_input == '':
        # Если Enter - дедлайн остаётся 'Нет'
        pass
    else:
        # Проверяем, что введено: число дней или конкретная дата
        if date_input.isdigit():
            # Если число - добавляем количество дней к сегодняшней дате
            deadline = datetime.datetime.now() + timedelta(days=int(date_input))
            deadline = deadline.strftime('%d.%m.%y')
        else:
            # Если дата - парсим и форматируем
            given_date = datetime.datetime.strptime(date_input, '%d.%m.%y')
            deadline = given_date.strftime('%d.%m.%y')

        projects[name]['deadline'] = deadline

    # Сохраняем проект в файл
    write_file(projects)
    print('\nПроект сохранен\n')
    main_menu()


def upd_projects():
    """
    Пересчитывает статистику всех проектов.
    Функция вызывается при каждом входе в главное меню.

    Делает три вещи:
    1. Пересчитывает процент прогресса (symbols / goal * 100)
    2. Вычисляет дни до дедлайна и ежедневную цель (goal / days_left)
    3. Пересчитывает стрик (последовательные дни с записями от сегодня назад)
    """
    from datetime import datetime, timedelta

    projects = read_file()

    # ========== ЧАСТЬ 1: Расчет прогресса ==========
    for name, data in projects.items():
        # Процент = (символы / цель) * 100, но не больше 100% если цель = 0
        projects[name]['progress'] = (data['symbols'] / data['goal'] * 100) if data['goal'] > 0 else 0

    # ========== ЧАСТЬ 2: Расчет дедлайна и ежедневной цели ==========
    for name, data in projects.items():
        deadline_str = data['deadline']

        # Пропускаем проекты без дедлайна
        if deadline_str == 'Нет':
            continue
        else:
            # Парсим дедлайн и вычисляем дни до него
            deadline = datetime.strptime(deadline_str, '%d.%m.%y')
            deadline_days = (deadline - datetime.today()).days

            if deadline_days > 0:
                # Сохраняем количество дней и вычисляем, сколько нужно писать в день
                projects[name]['deadline_days'] = deadline_days
                projects[name]['today_goal'] = int(projects[name]['goal'] / projects[name]['deadline_days'])
            else:
                # Если дедлайн прошел
                projects[name]['deadline_days'] = 0
                projects[name]['today_goal'] = 0

    # ========== ЧАСТЬ 3: Расчет стрика ==========
    for name, data in projects.items():
        # Если записей нет - стрик = 0
        if not data['notes']:
            projects[name]['streak'] = 0
            continue

        # Сортируем даты записей в хронологическом порядке
        dates = sorted(data['notes'].keys(), key=lambda x: datetime.strptime(x, '%d.%m.%y'))
        today_str = datetime.today().strftime('%d.%m.%y')

        # Считаем стрик: идём от последней даты (сегодня) назад
        streak = 0
        for i, date_str in enumerate(reversed(dates)):
            # Вычисляем ожидаемую дату (сегодня - i дней)
            expected_date = (datetime.today() - timedelta(days=i)).strftime('%d.%m.%y')

            # Если дата записи совпадает с ожидаемой - продолжаем стрик
            if date_str == expected_date:
                streak += 1
            else:
                # Если нет - стрик прерывается
                break

        # Обновляем текущий стрик и максимальный (если новый стрик больше)
        projects[name]['streak'] = streak
        projects[name]['max_streak'] = max(projects[name].get('max_streak', 0), streak)

    # Сохраняем обновлённые данные
    write_file(projects)


# ============================================================================
# ФУНКЦИИ ПРОСМОТРА ПРОЕКТОВ
# ============================================================================

def view_projects():
    """
    Показывает краткий список всех проектов с основной информацией:
    - название
    - цель и текущий прогресс
    - дедлайн
    - текущий стрик
    """
    projects = read_file()

    # Если проектов нет
    if len(projects) == 0:
        print('\nПроектов пока нет.\n')
        main_menu()
    else:
        print('Список проектов:\n')

        # Выводим каждый проект в одной строке
        for name, data in projects.items():
            goal = data['goal']
            symbols = data['symbols']
            progress = data['progress']
            streak = data.get('streak', 0)

            print(
                f'Название: {name}, цель: {goal}, прогресс: {symbols}/{goal} ({progress:.1f}%), '
                f'дедлайн: {data["deadline"]}, текущий стрик: {streak} дн.'
            )

        print()
        # Ждём нажатия Enter и возвращаемся в меню
        choice = input('Нажмите Enter для возврата в главное меню: ')
        if choice == '':
            main_menu()


def choice_project():
    """
    Показывает список проектов и просит выбрать один по номеру.
    Возвращает имя выбранного проекта.
    Если пользователь нажмёт Enter - возвращает в главное меню.
    """
    projects = read_file()

    # Если проектов нет
    if len(projects) == 0:
        print('Проектов пока нет\n')
        main_menu()

    # Создаём список имён проектов в порядке их добавления
    project_list = list(projects.keys())
    print('Ваши проекты:\n')

    # Выводим проекты с номерами для выбора
    for i, project_name in enumerate(project_list, 1):
        # Заменяем подчёркивания на пробелы для красивого вывода
        display_name = project_name.replace('_', ' ')
        print(f"{i} - {display_name}")

    print()
    # Просим выбрать проект или выход
    choice = input('Введите номер проекта или нажмите Enter для выхода: ')

    if choice == '':
        main_menu()

    # Возвращаем имя выбранного проекта
    selected_project = project_list[int(choice) - 1]
    return selected_project


def more_about_projects():
    """
    Детальный просмотр одного проекта.
    Показывает подробную информацию:
    - название, дедлайн, прогресс
    - дата создания, количество записей
    - среднее количество символов в записи
    - текущий и максимальный стрик

    Опционально выводит последние 10 записей с датами.
    """
    from datetime import datetime

    print('Детальный просмотр проекта\n')
    projects = read_file()
    project_name = choice_project()
    project_data = projects[project_name]

    # Выводим основную информацию
    print(f'Название: {project_name}')

    # Информация о дедлайне отличается в зависимости от его наличия
    if project_data["deadline"] != 'Нет':
        # Если дедлайн установлен
        if project_data.get('deadline_days', 0) > 0:
            print(f'Дедлайн: {project_data["deadline"]} - осталось {project_data["deadline_days"]} дней')
        else:
            print(f'Дедлайн: {project_data["deadline"]}')
    else:
        # Если дедлайна нет
        print(f'Дедлайн: {project_data["deadline"]}')

    # Прогресс проекта
    print(f'Прогресс: {project_data["progress"]:.1f}%')
    # Текущее количество символов
    print(f'Цель/написано: {project_data["goal"]}/{project_data["symbols"]}')
    # Дата создания
    print(f'Дата создания: {project_data["created"]}')
    # Количество записей (дней активности)
    print(f'Кол-во записей: {len(project_data["notes"])}')

    # Среднее количество символов в одной записи (если записи есть)
    if len(project_data["notes"]) > 0:
        avg_symbols = int(project_data["symbols"] / len(project_data["notes"]))
        print(f'Среднее кол-во символов в записи: {avg_symbols} символов')

    # Информация о стриках
    print(f'Текущий стрик: {project_data.get("streak", 0)} дней')
    print(f'Максимальный стрик: {project_data.get("max_streak", 0)} дней\n')

    # Предложение просмотреть записи
    ext = input('Нажмите Enter для выхода в меню выбора проектов\n'
                'Для просмотра записей выбранного проекта введите "1": ')

    if ext == '':
        # Просто возвращаемся в главное меню
        main_menu()
    else:
        # Показываем записи проекта
        print(f'Последние записи проекта {project_name}\n')
        notes = project_data['notes']

        # Если записей нет
        if len(notes) == 0:
            print('Записей пока нет\n')
            input('\nНажмите Enter для возврата в главное меню: ')
            main_menu()
        else:
            # Сортируем записи по дате в хронологическом порядке
            sorted_notes = sorted(
                notes.items(),
                key=lambda x: datetime.strptime(x[0], '%d.%m.%y')
            )

            # Берём последние 10 записей
            last_10 = sorted_notes[-10:]

            # Выводим каждую запись с датой и количеством символов
            for i, (date, value) in enumerate(last_10, 1):
                # Проверяем формат хранения (может быть список [символы, goal] или просто число)
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    symbols = value[0]
                else:
                    symbols = int(value)

                print(f'{i}. {date} - {symbols} символов')

            # Ждём нажатия Enter и возвращаемся в меню
            cancel = input('\nНажмите Enter для возврата в главное меню: ')
            if cancel == '':
                main_menu()


# ============================================================================
# ФУНКЦИИ ДЛЯ ДОБАВЛЕНИЯ И РЕДАКТИРОВАНИЯ ЗАПИСЕЙ
# ============================================================================

def new_note():
    """
    Добавляет новую запись (запись о написании) в проект.

    Возможны три режима:
    1. Просто число → запись на сегодня с этим количеством символов
    2. Enter → дополнительные вопросы о дате и количестве символов
    3. 0 → отмена и возврат в меню

    Запись хранится в формате [символы, today_goal].
    Поле 'symbols' проекта обновляется как максимум из всех записей.
    """
    from datetime import datetime

    projects = read_file()
    print('\nДобавление записи\n')
    selected_project = choice_project()

    # Первый ввод: число, 0 или Enter
    raw = input('Введите текущее кол-во символов.\n'
                '0 — выход в меню.\n'
                'Enter — добавить запись с датой: ')

    # 0 → выход
    if raw == '0':
        main_menu()
        return

    note_date = None  # Дата записи (дд.мм.гг)
    new_symbols_int = None  # Количество символов

    if raw == '':
        # Enter → сначала спрашиваем дату, потом число.
        date_input = input('Введите дату (дд.мм.гг): ')
        try:
            # Проверяем формат даты
            given_date = datetime.strptime(date_input, '%d.%m.%y')
            note_date = given_date.strftime('%d.%m.%y')
        except ValueError:
            print('Неверный формат даты. Запись не добавлена.\n')
            main_menu()
            return

        # Спрашиваем количество символов
        symbols_input = input('Введите текущее кол-во символов или 0 для отмены: ')
        if symbols_input == '0' or symbols_input == '':
            main_menu()
            return

        try:
            new_symbols_int = int(symbols_input)
        except ValueError:
            print('Неверное число символов. Запись не добавлена.\n')
            main_menu()
            return
    else:
        # Введено число → считаем датой сегодня
        try:
            new_symbols_int = int(raw)
        except ValueError:
            print('Неверное число символов. Запись не добавлена.\n')
            main_menu()
            return

        # Берём сегодняшнюю дату
        note_date = datetime.now().strftime('%d.%m.%y')

    # Создаём запись в формате [символы, today_goal]
    projects[selected_project]['notes'][note_date] = [
        new_symbols_int,
        projects[selected_project].get('today_goal', 0)
    ]

    # Пересчёт общего количества символов по максимуму из всех записей
    notes = projects[selected_project]['notes']
    if notes:
        # Берём максимум, так как это общий прогресс проекта
        projects[selected_project]['symbols'] = max(
            v[0] if isinstance(v, (list, tuple)) else int(v)
            for v in notes.values()
        )
    else:
        projects[selected_project]['symbols'] = 0

    # Сохраняем и обновляем проект
    write_file(projects)
    upd_projects()  # Пересчитываем статистику (стрик, дедлайн и т.д.)
    print('Запись добавлена.')
    main_menu()


def change_project_menu():
    """
    Подменю для изменения параметров проектов.
    Позволяет:
    - удалить проект
    - переименовать проект
    - изменить цель проекта
    - установить/изменить/удалить дедлайн
    - редактировать/удалить отдельные записи
    """

    def delete_project():
        """Удаляет выбранный проект после подтверждения."""
        print('Удаление проекта\n')
        projects = read_file()
        selected_project = choice_project()

        # Просим подтверждение
        done = input('Подтвердите удаление (нажмите Enter для отмены или введите "1" для удаления): ')
        if done == '1':
            del projects[selected_project]
            write_file(projects)
            print('\nПроект удален\n')
        else:
            print('\nУдаление отменено\n')

        # Возвращаемся в подменю изменений
        change_project_menu()

    def change_name():
        """Меняет имя проекта."""
        projects = read_file()
        print('Переименование проекта\n')
        selected_project = choice_project()

        # Получаем новое имя
        new_name = input('Введите новое имя проекта: ')

        # Копируем данные на новое имя и удаляем старое
        projects[new_name] = projects[selected_project]
        del projects[selected_project]

        write_file(projects)
        print('\nИмя проекта успешно изменено\n')
        change_project_menu()

    def change_goal():
        """Меняет целевое количество символов для проекта."""
        projects = read_file()
        print('Изменение цели проекта')
        selected_project = choice_project()

        # Получаем новую цель
        projects[selected_project]['goal'] = int(input('Введите новую цель (в символах): '))

        # Обновляем статистику (в том числе ежедневные цели)
        upd_projects()
        write_file(projects)
        print(f'\nЦель {selected_project} успешно изменена!\n')
        change_project_menu()

    def project_deadline():
        """Устанавливает, изменяет или удаляет дедлайн проекта."""
        from datetime import datetime, timedelta

        print('Установка/изменение дедлайна\n')
        projects = read_file()
        selected_project = choice_project()

        # Спрашиваем дату, количество дней или Enter для удаления
        date_input = input('Введите дату (дд.мм.гг) / количество дней (число) или нажмите Enter для её удаления: ')

        if date_input == '':
            # Удаляем дедлайн
            projects[selected_project]['deadline'] = 'Нет'
            write_file(projects)
            print('\nДедлайн удален\n')
        else:
            # Проверяем, введено ли число дней или конкретная дата
            if date_input.isdigit():
                # Добавляем количество дней к текущей дате
                deadline = datetime.now() + timedelta(days=int(date_input))
                deadline = deadline.strftime('%d.%m.%y')
            else:
                # Парсим введённую дату
                given_date = datetime.strptime(date_input, '%d.%m.%y')
                deadline = given_date.strftime('%d.%m.%y')

            # Сохраняем дедлайн
            projects[selected_project]['deadline'] = deadline
            write_file(projects)
            print('Дата дедлайна сохранена!')

        change_project_menu()

    def edit_notes():
        """
        Позволяет редактировать или удалять отдельные записи проекта.

        Пользователь может:
        - изменить дату записи
        - изменить количество символов
        - изменить оба параметра сразу
        - удалить запись полностью
        """
        from datetime import datetime

        projects = read_file()
        print('Изменение/удаление записей\n')
        selected_project = choice_project()
        notes = projects[selected_project].get('notes', {})

        # Если записей нет
        if not notes:
            print('У проекта пока нет записей.\n')
            change_project_menu()
            return

        # Показываем все записи с индексами
        sorted_notes = sorted(
            notes.items(),
            key=lambda x: datetime.strptime(x[0], '%d.%m.%y')
        )
        for i, (date, value) in enumerate(sorted_notes, 1):
            # Извлекаем количество символов (может быть список или число)
            symbols = value[0] if isinstance(value, (list, tuple)) else int(value)
            print(f'{i}. {date} - {symbols} символов')

        # Просим выбрать запись для редактирования
        idx = input('\nВведите номер записи для изменения/удаления или нажмите Enter для выхода: ')
        if idx == '':
            change_project_menu()
            return

        try:
            # Получаем выбранную запись
            idx = int(idx)
            date, value = sorted_notes[idx - 1]
        except (ValueError, IndexError):
            print('Неверный номер записи.\n')
            change_project_menu()
            return

        # Спрашиваем, что делать с записью
        action = input('Введите "1" для изменения, "2" для удаления, Enter для отмены: ')

        if action == '1':
            # ========== РЕДАКТИРОВАНИЕ ЗАПИСИ ==========

            # Спрашиваем, что именно изменить
            what = input('Что изменить?\n'
                         '1 - только дату\n'
                         '2 - только кол-во символов\n'
                         '3 - и дату, и кол-во символов\n'
                         'Нажмите Enter для отмены\n'
                         'Выбор: ')

            if what == '':
                print('\nИзменение отменено.\n')
                change_project_menu()
                return

            # Извлекаем старые значения
            old_symbols = value[0] if isinstance(value, (list, tuple)) else int(value)
            today_goal = value[1] if isinstance(value, (list, tuple)) and len(value) > 1 else projects[
                selected_project].get('today_goal', 0)

            # Инициализируем новые значения старыми
            new_date = date
            new_symbols = old_symbols

            # Изменяем дату, если нужно
            if what in ('1', '3'):
                new_date_input = input('Введите новую дату (дд.мм.гг): ')
                try:
                    # Проверяем формат
                    _ = datetime.strptime(new_date_input, '%d.%m.%y')
                    new_date = new_date_input
                except ValueError:
                    print('Неверный формат даты. Дата не изменена.')
                    new_date = date

            # Изменяем количество символов, если нужно
            if what in ('2', '3'):
                new_symbols_input = input('Введите новое кол-во символов: ')
                try:
                    new_symbols = int(new_symbols_input)
                except ValueError:
                    print('Неверное число символов. Кол-во символов не изменено.')
                    new_symbols = old_symbols

            # Применяем изменения к словарю записей
            if new_date != date:
                # Если дата изменилась, удаляем старую запись
                del notes[date]

            # Добавляем запись с новыми (или старыми, если не изменили) значениями
            notes[new_date] = [new_symbols, today_goal]

            # Обновляем данные проекта
            projects[selected_project]['notes'] = notes
            # Пересчитываем общее количество символов (берём максимум)
            projects[selected_project]['symbols'] = max(
                v[0] if isinstance(v, (list, tuple)) else int(v)
                for v in notes.values()
            )

            # Сохраняем и обновляем
            write_file(projects)
            upd_projects()
            print('\nЗапись изменена.\n')
            change_project_menu()

        elif action == '2':
            # ========== УДАЛЕНИЕ ЗАПИСИ ==========

            del notes[date]
            projects[selected_project]['notes'] = notes

            # Пересчитываем общее количество символов
            if notes:
                projects[selected_project]['symbols'] = max(
                    v[0] if isinstance(v, (list, tuple)) else int(v)
                    for v in notes.values()
                )
            else:
                # Если записей больше нет
                projects[selected_project]['symbols'] = 0

            # Сохраняем и обновляем
            write_file(projects)
            upd_projects()
            print('\nЗапись удалена.\n')
            change_project_menu()
        else:
            print('\nДействие отменено.\n')
            change_project_menu()

    # ===== ГЛАВНОЕ МЕНЮ РЕДАКТИРОВАНИЯ =====

    # Словарь функций редактирования
    change_menu = {
        '1': delete_project,
        '2': change_name,
        '3': change_goal,
        '4': project_deadline,
        '5': edit_notes,
        '': main_menu  # Enter = выход в главное меню
    }

    # Выводим меню и получаем выбор
    choice_for_change = input('Что вы хотите сделать?\n'
                              '1 - удалить проект\n'
                              '2 - переименовать проект\n'
                              '3 - изменить цель проекта\n'
                              '4 - изменить дедлайн проекта\n'
                              '5 - изменить/удалить запись проекта\n'
                              'Нажмите Enter для выхода в главное меню\n'
                              'Выбор: ')

    # Выполняем выбранную функцию (или main_menu по умолчанию)
    change_menu.get(choice_for_change, main_menu)()


# ============================================================================
# ФУНКЦИИ ПРОСМОТРА ЕЖЕДНЕВНЫХ ЦЕЛЕЙ
# ============================================================================

def today_goals():
    """
    Показывает статус ежедневных целей для всех проектов с активным дедлайном.

    Для каждого проекта выводит:
    - сколько нужно написать сегодня
    - сколько уже написано
    - сколько осталось
    - статус (выполнена ли цель)

    Ежедневная цель = goal / days_left (пересчитывается в upd_projects)
    """
    from datetime import datetime

    projects = read_file()

    if len(projects) == 0:
        print('Проектов пока нет.\n')
        main_menu()
    else:
        print('Список проектов:\n')
        cnt = 0  # Счётчик активных целей
        today_str = datetime.today().strftime('%d.%m.%y')  # Сегодняшняя дата

        # Проходим по каждому проекту
        for name, data in projects.items():
            today_goal = data.get('today_goal', 0)

            # Пропускаем проекты без дедлайна или без ежедневной цели
            if data.get('deadline', 'Нет') == 'Нет' or today_goal <= 0:
                continue

            # Получаем количество символов, написанных сегодня
            today_symbols = 0
            notes = data.get('notes', {})
            if isinstance(notes, dict) and today_str in notes:
                # Извлекаем символы из записи (может быть список [символы, goal] или число)
                val = notes[today_str]
                if isinstance(val, (list, tuple)) and len(val) > 0:
                    today_symbols = int(val[0])
                else:
                    today_symbols = int(val)

            # Вычисляем, сколько осталось написать
            remaining = max(today_goal - today_symbols, 0)

            # Определяем статус
            done = today_symbols >= today_goal
            status = 'цель ВЫПОЛНЕНА' if done else 'цель НЕ выполнена'

            # Выводим информацию
            print(
                f"{name}: цель на сегодня {today_goal} сим., "
                f"написано сегодня {today_symbols} сим., "
                f"осталось {remaining} сим., {status}."
            )
            cnt += 1

        # Если активных целей нет
        if cnt == 0:
            print('Проектов с активными дедлайнами и ежедневными целями нет.\n')
            main_menu()
        else:
            # Ждём нажатия Enter
            choice = input('\nНажмите Enter для возврата в главное меню: ')
            if choice == '':
                main_menu()


# ============================================================================
# ГЛАВНОЕ МЕНЮ ПРОГРАММЫ
# ============================================================================

def main_menu():
    """
    Главное меню приложения.

    При входе в меню:
    1. Автоматически пересчитывается статистика всех проектов (upd_projects)
    2. Выводится меню с 6 опциями
    3. Пользователь выбирает действие

    Опции:
    1 - добавить запись в проект
    2 - просмотреть список всех проектов
    3 - создать новый проект
    4 - изменить существующий проект (удалить, переименовать, цель, дедлайн, записи)
    5 - посмотреть подробную информацию о проекте
    6 - посмотреть ежедневные цели и их статус
    """
    upd_projects()  # Пересчитываем статистику при каждом входе в меню

    ch = False  # Флаг для цикла (хотя используется странно, но оставляем как есть)

    while ch == False:
        # Словарь функций меню: номер опции → функция
        menu = {
            '1': new_note,
            '2': view_projects,
            '3': new_project,
            '4': change_project_menu,
            '5': more_about_projects,
            '6': today_goals
        }

        # Выводим меню и получаем выбор пользователя
        ch = input('nfprogress 0.8\n'
                   '\n'
                   'Что вы хотите сделать?\n'
                   '1 - добавить запись\n'
                   '2 - просмотреть список проектов\n'
                   '3 - добавить проект\n'
                   '4 - изменить проекты\n'
                   '5 - посмотреть подробности проектов\n'
                   '6 - посмотреть ежедневные цели'
                   '\n'
                   'Выбор: ')

        # Выполняем выбранную функцию
        menu[ch]()


# ============================================================================
# ЗАПУСК ПРОГРАММЫ
# ============================================================================

main_menu()
