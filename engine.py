import pickle
import locale

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

def read_file(filename='projects.pkl'):
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            return data
    except (FileNotFoundError, EOFError):
        return {}

def write_file(data, filename='projects.pkl'):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

def new_project():
    import datetime
    from datetime import timedelta

    projects = read_file()
    print('Создание проекта')
    name = input('Введите название: ')
    goal = input('Введите цель (в символах): ')

    # базовые поля
    projects[name] = {'goal': int(goal),
                      'symbols': 0,
                      'progress': 0,
                      'notes': {},
                      'streak': 0,      # текущий стрик
                      'max_streak': 0,  # максимальный стрик
                      'deadline': 'Нет',
                      'created': f'{datetime.date.today().strftime("%d.%m.%y")}'}

    # предложение задать дедлайн
    date_input = input('Введите дату дедлайна (дд.мм.гг) / количество дней (число)\n'
                       'или нажмите Enter, чтобы пропустить: ')

    if date_input == '':
        # дедлайн остается 'Нет'
        pass
    else:
        if date_input.isdigit():
            deadline = datetime.datetime.now() + timedelta(days=int(date_input))
            deadline = deadline.strftime('%d.%m.%y')
        else:
            given_date = datetime.datetime.strptime(date_input, '%d.%m.%y')
            deadline = given_date.strftime('%d.%m.%y')
        projects[name]['deadline'] = deadline

    write_file(projects)
    print('\nПроект сохранен\n')
    main_menu()

def upd_projects():
    from datetime import datetime, timedelta   # ← добавлен timedelta
    projects = read_file()

    # Расчет прогресса
    for name, data in projects.items():
        projects[name]['progress'] = (data['symbols'] / data['goal'] * 100) if data['goal'] > 0 else 0

    # Расчет дедлайна и ежедневной цели
    for name, data in projects.items():
        deadline_str = data['deadline']
        if deadline_str == 'Нет':
            continue
        else:
            deadline = datetime.strptime(deadline_str, '%d.%m.%y')
            deadline_days = (deadline - datetime.today()).days
            if deadline_days > 0:
                projects[name]['deadline_days'] = deadline_days
                projects[name]['today_goal'] = int(projects[name]['goal'] / projects[name]['deadline_days'])
            else:
                projects[name]['deadline_days'] = 0
                projects[name]['today_goal'] = 0

    # Расчет стриков
    for name, data in projects.items():
        if not data['notes']:  # нет записей
            projects[name]['streak'] = 0
            continue

        dates = sorted(data['notes'].keys(), key=lambda x: datetime.strptime(x, '%d.%m.%y'))
        today_str = datetime.today().strftime('%d.%m.%y')

        streak = 0
        for i, date_str in enumerate(reversed(dates)):  # идем от сегодня назад
            date = datetime.strptime(date_str, '%d.%m.%y')
            if date_str == today_str or date_str == (datetime.today() - timedelta(days=i)).strftime('%d.%m.%y'):
                streak += 1
            else:
                break

        projects[name]['streak'] = streak
        projects[name]['max_streak'] = max(projects[name].get('max_streak', 0), streak)

    write_file(projects)


def view_projects():
    projects = read_file()
    if len(projects) == 0:
        print('\nПроектов пока нет.\n')
        main_menu()
    else:
        print('Список проектов:\n')
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
        choice = input('Нажмите Enter для возврата в главное меню: ')
        if choice == '':
            main_menu()

def choice_project():
    projects = read_file()
    if len(projects) == 0:
        print('Проектов пока нет\n')
        main_menu()
    project_list = list(projects.keys())
    print('Ваши проекты:\n')
    for i, project_name in enumerate(project_list, 1):
        display_name = project_name.replace('_', ' ')
        print(f"{i} - {display_name}")
    print()
    choice = input('Введите номер проекта или нажмите Enter для выхода: ')
    if choice == '':
        main_menu()
    selected_project = project_list[int(choice) - 1]
    return selected_project


def more_about_projects():
    from datetime import datetime
    print('Детальный просмотр проекта\n')
    projects = read_file()
    project_name = choice_project()
    project_data = projects[project_name]

    print(f'Название: {project_name}')

    if project_data["deadline"] != 'Нет':
        if project_data.get('deadline_days', 0) > 0:
            print(f'Дедлайн: {project_data["deadline"]} - осталось {project_data["deadline_days"]} дней')
        else:
            print(f'Дедлайн: {project_data["deadline"]}')
        print(f'Прогресс: {project_data["progress"]:.1f}%')
        print(f'Цель/написано: {project_data["goal"]}/{project_data["symbols"]}')
        print(f'Дата создания: {project_data["created"]}')
        print(f'Кол-во записей: {len(project_data["notes"])}')
        if len(project_data["notes"]) > 0:
            print(f'Среднее кол-во символов в записи: {int(project_data["symbols"] / len(project_data["notes"]))} символов')
        print(f'Текущий стрик: {project_data.get("streak", 0)} дней')
        print(f'Максимальный стрик: {project_data.get("max_streak", 0)} дней\n')
    else:
        print(f'Дедлайн: {project_data["deadline"]}')
        print(f'Прогресс: {project_data["progress"]:.1f}%')
        print(f'Цель/написано: {project_data["goal"]}/{project_data["symbols"]}')
        print(f'Дата создания: {project_data["created"]}')
        print(f'Кол-во записей: {len(project_data["notes"])}')
        if len(project_data["notes"]) > 0:
            print(f'Среднее кол-во символов в записи: {int(project_data["symbols"] / len(project_data["notes"]))} символов')
        print(f'Текущий стрик: {project_data.get("streak", 0)} дней')
        print(f'Максимальный стрик: {project_data.get("max_streak", 0)} дней\n')

    ext = input('Нажмите Enter для выхода в меню выбора проектов\n'
                'Для просмотра записей выбранного проекта введите "1": ')
    if ext == '':
        # просто возвращаемся в меню выбора проектов
        main_menu()
    else:
        print(f'Последние записи проекта {project_name}\n')
        notes = project_data['notes']

        if len(notes) == 0:
            print('Записей пока нет\n')
            input('\nНажмите Enter для возврата в главное меню: ')
            main_menu()
        else:
            sorted_notes = sorted(
                notes.items(),
                key=lambda x: datetime.strptime(x[0], '%d.%m.%y')
            )
            last_10 = sorted_notes[-10:]

            for i, (date, value) in enumerate(last_10, 1):
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    symbols = value[0]
                else:
                    symbols = int(value)
                print(f'{i}. {date} - {symbols} символов')

            cancel = input('\nНажмите Enter для возврата в главное меню: ')
            if cancel == '':
                main_menu()

def new_note():
    from datetime import datetime
    projects = read_file()
    print('\nДобавление записи\n')
    selected_project = choice_project()

    # Первый ввод: число, 0 или Enter
    raw = input('Введите текущее кол-во символов.\n'
                '0 — выход в меню.\n'
                'Enter — добавить запись с датой: ')

    # 0 — выход
    if raw == '0':
        main_menu()
        return

    note_date = None
    new_symbols_int = None

    if raw == '':  # Enter → сначала спрашиваем дату, потом число
        date_input = input('Введите дату (дд.мм.гг): ')
        try:
            given_date = datetime.strptime(date_input, '%d.%m.%y')
            note_date = given_date.strftime('%d.%m.%y')
        except ValueError:
            print('Неверный формат даты. Запись не добавлена.\n')
            main_menu()
            return

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
        # Введено число — считаем датой сегодня
        try:
            new_symbols_int = int(raw)
        except ValueError:
            print('Неверное число символов. Запись не добавлена.\n')
            main_menu()
            return
        note_date = datetime.now().strftime('%d.%m.%y')

    # Обновляем/создаем запись
    projects[selected_project]['notes'][note_date] = [
        new_symbols_int,
        projects[selected_project].get('today_goal', 0)
    ]

    # Пересчёт общего количества символов по максимуму
    notes = projects[selected_project]['notes']
    if notes:
        projects[selected_project]['symbols'] = max(
            v[0] if isinstance(v, (list, tuple)) else int(v)
            for v in notes.values()
        )
    else:
        projects[selected_project]['symbols'] = 0

    write_file(projects)
    upd_projects()
    print('Запись добавлена.')
    main_menu()

def change_project_menu():

    def delete_project():
        print('Удаление проекта\n')
        projects = read_file()
        selected_project = choice_project()
        done = input('Подтвердите удаление (нажмите Enter для отмены или введите "1" для удаления): ')
        if done == '1':
            del projects[selected_project]
            write_file(projects)
            print('\nПроект удален\n')
        else:
            print('\nУдаление отменено\n')
        change_project_menu()

    def change_name():
        projects = read_file()
        print('Переименование проекта\n')
        selected_project = choice_project()
        new_name = input('Введите новое имя проекта: ')
        projects[new_name] = projects[selected_project]
        del projects[selected_project]
        write_file(projects)
        print('\nИмя проекта успешно изменено\n')
        change_project_menu()

    def change_goal():
        projects = read_file()
        print('Изменение цели проекта')
        selected_project = choice_project()
        projects[selected_project]['goal'] = int(input('Введите новую цель (в символах): '))
        upd_projects()
        write_file(projects)
        print(f'\nЦель {selected_project} успешно изменена!\n')
        change_project_menu()

    def project_deadline():
        from datetime import datetime, timedelta
        print('Установка/изменение дедлайна\n')
        projects = read_file()
        selected_project = choice_project()
        date_input = input('Введите дату (дд.мм.гг) / количество дней (число) или нажмите Enter для ее удаления: ')
        if date_input == '':
            projects[selected_project]['deadline'] = 'Нет'
            write_file(projects)
            print('\nДедлайн удален\n')
        else:
            if date_input.isdigit():
                deadline = datetime.now() + timedelta(days=int(date_input))
                deadline = deadline.strftime('%d.%m.%y')
            else:
                given_date = datetime.strptime(date_input, '%d.%m.%y')
                deadline = given_date.strftime('%d.%m.%y')
            projects[selected_project]['deadline'] = deadline
            write_file(projects)
            print('Дата дедлайна сохранена!')
        change_project_menu()

    def edit_notes():
        from datetime import datetime
        projects = read_file()
        print('Изменение/удаление записей\n')
        selected_project = choice_project()
        notes = projects[selected_project].get('notes', {})

        if not notes:
            print('У проекта пока нет записей.\n')
            change_project_menu()
            return

        # показываем все записи с индексами
        sorted_notes = sorted(
            notes.items(),
            key=lambda x: datetime.strptime(x[0], '%d.%m.%y')
        )
        for i, (date, value) in enumerate(sorted_notes, 1):
            symbols = value[0] if isinstance(value, (list, tuple)) else int(value)
            print(f'{i}. {date} - {symbols} символов')

        idx = input('\nВведите номер записи для изменения/удаления или нажмите Enter для выхода: ')
        if idx == '':
            change_project_menu()
            return

        try:
            idx = int(idx)
            date, value = sorted_notes[idx - 1]
        except (ValueError, IndexError):
            print('Неверный номер записи.\n')
            change_project_menu()
            return

        action = input('Введите "1" для изменения, "2" для удаления, Enter для отмены: ')
        if action == '1':
            # выбор, что менять
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

            old_symbols = value[0] if isinstance(value, (list, tuple)) else int(value)
            today_goal = value[1] if isinstance(value, (list, tuple)) and len(value) > 1 else projects[
                selected_project].get('today_goal', 0)

            new_date = date
            new_symbols = old_symbols

            if what in ('1', '3'):
                new_date_input = input('Введите новую дату (дд.мм.гг): ')
                try:
                    _ = datetime.strptime(new_date_input, '%d.%m.%y')
                    new_date = new_date_input
                except ValueError:
                    print('Неверный формат даты. Дата не изменена.')
                    new_date = date

            if what in ('2', '3'):
                new_symbols_input = input('Введите новое кол-во символов: ')
                try:
                    new_symbols = int(new_symbols_input)
                except ValueError:
                    print('Неверное число символов. Кол-во символов не изменено.')
                    new_symbols = old_symbols

            # применяем изменения
            if new_date != date:
                del notes[date]
            notes[new_date] = [new_symbols, today_goal]

            projects[selected_project]['notes'] = notes
            projects[selected_project]['symbols'] = max(
                v[0] if isinstance(v, (list, tuple)) else int(v)
                for v in notes.values()
            )

            write_file(projects)
            upd_projects()
            print('\nЗапись изменена.\n')
            change_project_menu()

        elif action == '2':
            del notes[date]
            projects[selected_project]['notes'] = notes
            if notes:
                projects[selected_project]['symbols'] = max(
                    v[0] if isinstance(v, (list, tuple)) else int(v)
                    for v in notes.values()
                )
            else:
                projects[selected_project]['symbols'] = 0
            write_file(projects)
            upd_projects()
            print('\nЗапись удалена.\n')
            change_project_menu()
        else:
            print('\nДействие отменено.\n')
            change_project_menu()

    change_menu = {
        '1': delete_project,
        '2': change_name,
        '3': change_goal,
        '4': project_deadline,
        '5': edit_notes,
        '': main_menu
    }

    choice_for_change = input('Что вы хотите сделать?\n'
                              '1 - удалить проект\n'
                              '2 - переименовать проект\n'
                              '3 - изменить цель проекта\n'
                              '4 - изменить дедлайн проекта\n'
                              '5 - изменить/удалить запись проекта\n'
                              'Нажмите Enter для выхода в главное меню\n'
                              'Выбор: ')
    change_menu.get(choice_for_change, main_menu)()

def today_goals():
    from datetime import datetime

    projects = read_file()
    if len(projects) == 0:
        print('Проектов пока нет.\n')
        main_menu()
    else:
        print('Список проектов:\n')
        cnt = 0
        today_str = datetime.today().strftime('%d.%m.%y')

        for name, data in projects.items():
            today_goal = data.get('today_goal', 0)
            if data.get('deadline', 'Нет') == 'Нет' or today_goal <= 0:
                continue

            today_symbols = 0
            notes = data.get('notes', {})
            if isinstance(notes, dict) and today_str in notes:
                val = notes[today_str]
                if isinstance(val, (list, tuple)) and len(val) > 0:
                    today_symbols = int(val[0])
                else:
                    today_symbols = int(val)

            remaining = max(today_goal - today_symbols, 0)
            done = today_symbols >= today_goal
            status = 'цель ВЫПОЛНЕНА' if done else 'цель НЕ выполнена'

            print(
                f"{name}: цель на сегодня {today_goal} сим., "
                f"написано сегодня {today_symbols} сим., "
                f"осталось {remaining} сим., {status}."
            )
            cnt += 1

        if cnt == 0:
            print('Проектов с активными дедлайнами и ежедневными целями нет.\n')
            main_menu()
        else:
            choice = input('\nНажмите Enter для возврата в главное меню: ')
            if choice == '':
                main_menu()

def main_menu():
    upd_projects()
    ch = False
    while ch == False:
        # Словарь функций: 1 — добавить запись
        menu = {
            '1': new_note,
            '2': view_projects,
            '3': new_project,
            '4': change_project_menu,
            '5': more_about_projects,
            '6': today_goals
        }
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
        menu[ch]()


main_menu()
