import pickle
import game
from datetime import date, datetime, timedelta
from random import randint

TEST_DATE = None

def today_for_test():
    if TEST_DATE is None or TEST_DATE < date.today():
        return date.today()
    else:
        return TEST_DATE

def load_data():
    try:
        with open('data.pkl', 'rb') as f:
            data = pickle.load(f)
            return data
    except FileNotFoundError:
        return {'last': None, 'projects': {'active': {}}}


def save_data(data):
    with open('data.pkl', 'wb') as f:
        pickle.dump(data, f)


def main_menu():
    print('nfprogress 1.1.4\n')
    print(f'Сегодня: {today_for_test().strftime("%d.%m.%y")}')
    print('Что вы хотите сделать?\n')
    print('1 - Новая запись')
    print('2 - Просмотр проектов')
    print('3 - Новый проект')
    print('4 - Изменить проект')
    print('5 - Игровой режим')
    print('6 - Подробности о проекте')

    data = load_data()
    last = data['last']

    if last is not None:
        print(f'\nЗапись в последний проект ({last}) - Enter')

    do_list = {
        '1': new_note,
        '2': view_projects,
        '3': new_project,
        '4': change_project,
        '5': game.menu,
        '6': more_details
    }

    do = input('\nВыберите пункт из меню: ')
    if do != '':
        try:
            do_list[do]()
        except KeyError:
            print('НЕПРАВИЛЬНЫЙ ВЫБОР')
            main_menu()
    else:
        new_note(last)


def new_project():
    data = load_data()
    print('\nСОЗДАНИЕ ПРОЕКТА\n')
    name = input('Введите имя проекта или Enter для выхода: ')
    if name == '':
        print('\n СОЗДАНИЕ ПРОЕКТА ОТМЕНЕНО \n')
        main_menu()
        return

    try:
        goal_input = input('Введите цель по проекту в символах или Enter для выхода: ')
        if goal_input == '':
            print('\n СОЗДАНИЕ ПРОЕКТА ОТМЕНЕНО \n')
            main_menu()
            return
        goal = int(goal_input)
    except ValueError:
        print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
        # Для краткости просто перезапускаем, если ошибка
        main_menu()
        return

    deadline_input = input('Введите дедлайн проекта в формате дд.мм.гг \n или Enter, чтобы пропустить: ')
    try:
        if deadline_input == '':
            deadline = 'Нет'
        else:
            deadline = datetime.strptime(deadline_input, '%d.%m.%y')
    except ValueError:
        print('\n ЗНАЧЕНИЕ НЕКОРРЕКТНО (Дедлайн установлен как "Нет") \n')
        deadline = 'Нет'

    data['projects']['active'][name] = {
        'goal': goal,
        'created': today_for_test(),
        'total symbols': 0,
        'progress': 0,
        'notes': {},
        'streaks': [],
        'deadline': {'date': deadline, 'days left': 0}
    }
    data['last'] = name
    save_data(data)
    print(f'\nПроект {name} создан\n')
    main_menu()


def view_projects():
    data = load_data()
    projects = data['projects']['active']

    if len(projects) == 0:
        print('\nАктивных проектов пока нет.')
    else:
        for name in projects.keys():
            if not isinstance(projects[name], dict):
                continue

            proj = projects[name]
            goal = proj['goal']
            progress = proj['progress']
            symbols = proj['total symbols']
            deadline = proj['deadline']['date']

            if deadline == 'Нет':
                print(f'Название: {name}, прогресс: {progress}%, написано/цель: {symbols}/{goal}')
            else:
                deadline_str = datetime.strftime(deadline, '%d.%m.%y')
                days_left = proj['deadline']['days left']
                streaks = len(proj['streaks'])
                print(f'Название: {name}, прогресс: {progress}%, написано: {symbols}/{goal}, '
                      f'дедлайн: {deadline_str}, дней: {days_left}, стрик: {streaks}')

    archived = data['projects'].get('archive', {})
    completed = data['projects'].get('complete', {})

    print('\nДля выхода нажмите Enter\n')

    if len(archived) > 0:
        print('Для просмотра проектов в архиве введите 1')
    if len(completed) > 0:
        print('Для просмотра завершенных проектов введите 2')

    if len(archived) > 0 or len(completed) > 0:
        print()  # Пустая строка для отступа

    do = input('Выбор: ')

    # === ПРОСМОТР АРХИВА ===
    if do == '1' and len(archived) > 0:
        print('\n ПРОЕКТЫ В АРХИВЕ \n')
        for name in archived.keys():
            proj = archived[name]
            goal = proj['goal']
            progress = proj['progress']
            symbols = proj['total symbols']
            archived_date = proj.get('archived_date', 'Неизвестно')

            print(
                f'Название: {name}, прогресс: {progress}%, написано/цель: {symbols}/{goal}, архивирован: {archived_date}')

        print('\nДля выхода нажмите Enter')
        print('Или введите номер проекта для восстановления: ')

        projects_names = list(archived.keys())
        for i in range(len(projects_names)):
            print(f'{i + 1} - {projects_names[i]}')

        do_restore = input('Выбор: ')

        if do_restore == '':
            main_menu()
        else:
            try:
                choice = int(do_restore)
                choice_name = projects_names[choice - 1]
                print(f'\nВыбран проект: {choice_name}\n')

                data['projects']['active'][choice_name] = data['projects']['archive'][choice_name]
                del data['projects']['archive'][choice_name]
                save_data(data)

                print('\n ПРОЕКТ ВОЗВРАЩЕН ИЗ АРХИВА \n')
                main_menu()
            except (ValueError, IndexError):
                print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!')
                main_menu()

    # === ПРОСМОТР ЗАВЕРШЕННЫХ (НОВОЕ) ===
    elif do == '2' and len(completed) > 0:
        print('\n ЗАВЕРШЕННЫЕ ПРОЕКТЫ \n')
        for name in completed.keys():
            proj = completed[name]
            goal = proj['goal']
            progress = proj['progress']
            symbols = proj['total symbols']
            streaks = len(proj.get('streaks', []))

            print(
                f'Название: {name}, прогресс: {progress}%, написано/цель: {symbols}/{goal}, итоговый стрик: {streaks}')

        print('\nДля выхода нажмите Enter')
        print('Или введите номер проекта для удаления из завершенных: ')

        projects_names = list(completed.keys())
        for i in range(len(projects_names)):
            print(f'{i + 1} - {projects_names[i]}')

        delete = input('Выбор: ')
        if delete == '':
            main_menu()
        else:
            try:
                choice = int(delete)
                choice_name = projects_names[choice - 1]
                print(f'\nВыбран проект: {choice_name}\n')

                from random import randint
                key = randint(1000, 9999)
                print(f'Удаление "{choice_name}" необратимо!')

                try:
                    approve = int(input(f'Для подтверждения введите {key}: '))
                    if approve == key:
                        data = load_data()
                        del data['projects']['complete'][choice_name]  # Удаляем из complete, не active
                        save_data(data)
                        print(f'\nПроект удален из завершенных.\n')
                    else:
                        print('\nНеверный код.\n')
                except ValueError:
                    print('\nОшибка.\n')

                main_menu()
            except (ValueError, IndexError):
                print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ')
                main_menu()

    else:
        main_menu()

def choice_project():
    data = load_data()
    projects = data['projects']['active']
    if len(projects) == 0:
        print('\nПроектов пока нет.')
        do = input('\nДля выхода нажмите Enter.')
        if do == '':
            main_menu()
    else:
        projects_names = list(data['projects']['active'].keys())
        print('ВЫБЕРИТЕ ПРОЕКТ:\n')
        for i in range(len(projects_names)):
            print(f'{i + 1} - {projects_names[i]}')
        try:
            choice = int(input('\nВведите номер выбранного проекта '
            '\nили введите Enter для выхода в главное меню: '))
            choice = projects_names[choice - 1]
            print(f'\nВыбран проект: {choice}\n')
            return choice
        except (ValueError, IndexError):
            print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!\nВведите число.')
            main_menu()


def chek_streak(project_name, symbol_progress, today_goal=0):
    data = load_data()
    today = today_for_test()
    project = data['projects']['active'][project_name]
    streaks = project['streaks']
    deadline = project['deadline']['date']
    goal = project['goal']
    total = project['total symbols']

    # Нормализация дедлайна
    if isinstance(deadline, datetime):
        deadline_date = deadline.date()
    elif deadline == 'Нет':
        deadline_date = None
    else:
        deadline_date = deadline

    # === ПРОВЕРКА ЗАВЕРШЕНИЯ ===
    if total >= goal:
        if deadline_date is None or today <= deadline_date:
            return 'Complete'

    # === ЛОГИКА СТРИКОВ ===
    yesterday = today - timedelta(days=1)

    # Если дедлайна нет или цель на сегодня не установлена
    if today_goal <= 0:
        return None

    # === ПОВТОР В ДЕНЬ (ПРОВЕРИТЬ ДО ПРОВЕРКИ КОЛИЧЕСТВА) ===
    if len(streaks) > 0 and streaks[-1] == today:
        return 'Done'

    # Достаточно символов в этой сессии?
    if symbol_progress < today_goal:
        return None  # Цель не достигнута, ничего не делаем

    # === НАЧАЛО НОВОГО СТРИКА ===
    if len(streaks) == 0:
        streaks.append(today)
        streak_status = 'Start'

    # === ПРОДОЛЖЕНИЕ СТРИКА ===
    elif streaks[-1] == yesterday:
        streaks.append(today)
        streak_status = 'Go'

    # === ПОТЕРЯ СТРИКА ===
    else:  # Разрыв цепи
        lost_days = len(streaks)
        streaks = [today]  # Начинаем заново
        streak_status = f'Lose {lost_days}'

    data['projects']['active'][project_name]['streaks'] = streaks
    save_data(data)
    return streak_status


def new_note(choice=None):
    if choice is None:
        choice = choice_project()
        if choice is None: return

    data = load_data()

    if choice not in data['projects']['active']:
        print("Ошибка: Проект не найден (возможно, удален).")
        main_menu()
        return

    data['last'] = choice
    project = data['projects']['active'][choice]

    goal = project['goal']
    last_symbols = project['total symbols']  # Сколько было до ввода
    need_symbols = goal - last_symbols
    today_dt = today_for_test()  # Используем тестовую дату

    # Делаем today_dt объектом date, если он вдруг datetime (для ключей словаря)
    if isinstance(today_dt, datetime):
        today_date = today_dt.date()
    else:
        today_date = today_dt

    deadline = project['deadline']['date']

    print(f'Текущее кол-во символов в {choice}: {last_symbols} сим.')
    print(f'Осталось написать до цели: {need_symbols} сим.')

    # === ВЫЧИСЛЯЕМ ЦЕЛЬ НА СЕГОДНЯ ===
    today_goal = 0
    if deadline != 'Нет':
        # Приводим deadline к date для вычитания
        d_date = deadline.date() if isinstance(deadline, datetime) else deadline
        t_date = today_dt.date() if isinstance(today_dt, datetime) else today_dt

        days_left = (d_date - t_date).days
        if days_left > 0:
            today_goal = need_symbols // days_left
            print(f'Цель на сегодня: {today_goal} сим.')
        else:
            print('Дедлайн прошел или сегодня!')

    try:
        inp = input('Введите новое кол-во символов: ')
        if inp == '':
            main_menu()
            return
        new_symbols = int(inp)
    except ValueError:
        print('\n ЗНАЧЕНИЕ НЕКОРРЕКТНО \n')
        main_menu()
        return

    # 1. Считаем, сколько добавили ПРЯМО СЕЙЧАС (для опыта и монет)
    session_added = new_symbols - last_symbols

    # Если ввели меньше, чем было - значит удалили текст, опыт не даем
    if session_added < 0:
        session_added = 0

    # 2. Считаем прогресс ЗА ВЕСЬ ДЕНЬ (для записи в лог и стриков)
    # Если сегодня уже писали, берем старое значение за сегодня и добавляем новое
    current_today_progress = 0
    if today_date in project['notes']:
        current_today_progress = project['notes'][today_date].get('symbol_progress', 0)

    today_total_progress = current_today_progress + session_added

    progress = round(new_symbols / goal * 100)

    # Записываем в лог именно дневной прогресс
    project['notes'][today_date] = {
        'symbol_progress': today_total_progress,
        'last_total': new_symbols
    }
    project['progress'] = progress
    project['total symbols'] = new_symbols
    data['projects']['active'][choice] = project
    save_data(data)

    print(f'\nДобавлено сейчас: {session_added} сим.')
    print(f'Всего за сегодня: {today_total_progress} сим.')
    print(f'Общий прогресс: {progress}%\n')

    # Опыт даем только за то, что добавили сейчас
    if game.load_game() is not None and session_added > 0:
        print(f'Получено {game.give_coins(session_added)} монет и {game.give_exps(session_added)} опыта\n')

    # === ПРОВЕРКА СТРИКА ===
    # Проверяем стрик на основе ВСЕГО написанного за сегодня (today_total_progress)
    if session_added > 0 or today_total_progress > 0:
        streak_status = chek_streak(choice, today_total_progress, today_goal)

        # Перезагружаем data, так как chek_streak мог её обновить
        data = load_data()
        current_streak = len(data['projects']['active'][choice]['streaks'])

        if streak_status == 'Start':
            print('Старт стрика!\n')
        elif streak_status == 'Go':
            print(f'Стрик продлен! Дней подряд: {current_streak}\n')
        elif streak_status == 'Done':
            print('Цель на сегодня уже выполнена, ты хорошо постарался!\n')
        elif streak_status and streak_status.startswith('Lose'):
            lost = streak_status.split()[1]
            print(f'Стрик прерван (потеряно {lost} дн). Начнем снова?\n')

        # === БОНУС ЗА СТРИК ===
        if game.load_game() is not None and streak_status:
            # Обновляем notes локально, чтобы не затереть флаг бонуса
            notes = data['projects']['active'][choice]['notes']
            if today_date in notes:
                if not notes[today_date].get('streak_bonus', False):
                        print(game.give_streak_bonus(streak_status, new_symbols))
                        notes[today_date]['streak_bonus'] = True
                        save_data(data)

    # === ЗАВЕРШЕНИЕ ПРОЕКТА ===
    if goal <= new_symbols:
        print('Работа над проектом завершена!')
        if game.load_game() is not None:
            print(game.give_complete_bonus(True, new_symbols))

        data = load_data()
        if 'complete' not in data['projects']:
            data['projects']['complete'] = {}
        data['projects']['complete'][choice] = data['projects']['active'][choice]
        del data['projects']['active'][choice]
        save_data(data)
        main_menu()
        return

    main_menu()


def change_project():
    print('\nИЗМЕНЕНИЕ ПРОЕКТА\n')
    choice = choice_project()
    if choice is None:
        return

    def change_name():
        data = load_data()
        new_name = input(f'Введите новое имя для "{choice}": ')
        if new_name != '':
            # Копируем данные в новый ключ, удаляем старый
            data['projects']['active'][new_name] = data['projects']['active'][choice]
            del data['projects']['active'][choice]
            if data['last'] == choice:
                data['last'] = new_name
            save_data(data)
            print(f'\nИмя изменено на {new_name}.\n')
        main_menu()

    def change_goal():
        try:
            new_goal = int(input(f'Новая цель для "{choice}": '))
            if new_goal > 0:
                data = load_data()
                data['projects']['active'][choice]['goal'] = new_goal
                save_data(data)
                print('Цель изменена.\n')
            else:
                print('Цель должна быть > 0')
        except ValueError:
            print('Нужно число.')
        main_menu()

    def change_deadline():
        deadline_str = input('Новый дедлайн (дд.мм.гг): ')
        if deadline_str == '':
            main_menu()
            return
        try:
            new_deadline = datetime.strptime(deadline_str, '%d.%m.%y')
            data = load_data()
            # Важно: обновляем структуру правильно
            data['projects']['active'][choice]['deadline'] = {
                'date': new_deadline,
                'days left': (new_deadline.date() - date.today()).days
            }
            save_data(data)
            print(f'\nДедлайн изменён.\n')
        except ValueError:
            print('Ошибка формата даты.')
        main_menu()

    def delete_project():
        key = randint(1000, 9999)
        print(f'Удаление "{choice}" необратимо!')
        try:
            approve = int(input(f'Для подтверждения введите {key}: '))
            if approve == key:
                data = load_data()
                del data['projects']['active'][choice]
                if data['last'] == choice:
                    data['last'] = None
                save_data(data)
                print(f'\nПроект удален.\n')
            else:
                print('\nНеверный код.\n')
        except ValueError:
            print('\nОшибка.\n')
        main_menu()

    def change_symbols():
        print(f'\nИЗМЕНЕНИЕ СИМВОЛОВ В "{choice}"\n')
        data = load_data()  # Загружаем данные

        current = data['projects']['active'][choice]['total symbols']
        print(f'Текущее кол-во: {current}')

        try:
            new_symbols = int(input('Новое кол-во символов: '))
            data['projects']['active'][choice]['total symbols'] = new_symbols
            goal = data['projects']['active'][choice]['goal']
            data['projects']['active'][choice]['progress'] = round(new_symbols / goal * 100)

            save_data(data)
            print('\nИЗМЕНЕНИЯ СОХРАНЕНЫ\n')
            main_menu()
        except ValueError:
            print('\nНужно число!\n')

    def send_to_archive():
        print('\n ОТПРАВКА В АРХИВ \n')
        print('При добавлении в архив дедлайн проекта удаляется'
              '\nсам проект больше не будет виден в списке проектов'
              '\nи станет недоступным для выбора.')
        if game.load_game() is not None:
            print('Отправка в архив не влияет на вашего персонажа')
        data = load_data()
        if 'archive' not in data['projects']:
            data['projects']['archive'] = {}
        do = input('Введите 1 для подтверждения отправки в архив или Enter для выхода: ')
        if do == '1':
            archived = data['projects']['active'][choice]
            archived['archived_date'] = date.today().strftime('%d.%m.%y')
            archived['deadline'] = {'date': 'Нет', 'days left': 0}
            data['projects']['archive'][choice] = archived
            del data['projects']['active'][choice]
            save_data(data)
            print(f'/n Проект {choice} направлен в архив \n')
            main_menu()
        else:
            print('\n ДЕЙСТВИЕ ОТМЕНЕНО \n')
            main_menu()

        main_menu()

    print('1 - Изменить имя')
    print('2 - Изменить цель')
    print('3 - Изменить дедлайн')
    print('4 - Удалить проект')
    print('5 - Изменить кол-во символов (ручная правка)')
    print('6 - Отправить в архив')

    do = input('\nВыберите действие: ')
    actions = {
        '1': change_name,
        '2': change_goal,
        '3': change_deadline,
        '4': delete_project,
        '5': change_symbols,
        '6': send_to_archive,
    }

    try:
        actions[do]()
    except KeyError:
        print('НЕПРАВИЛЬНЫЙ ВЫБОР')
        change_project()


def more_details():
    print('\n ПОДРОБНОСТИ О ПРОЕКТЕ \n')
    choice = choice_project()
    if choice is None: return

    data = load_data()
    project = data['projects']['active'][choice]
    notes = project['notes']

    if len(notes) > 0:
        total_symbols_in_notes = sum(n['symbol_progress'] for n in notes.values())
        avg_symbols = round(total_symbols_in_notes / len(notes))
    else:
        avg_symbols = 0

    print(f'Название: {choice}')
    print(f'Цель: {project["goal"]}')
    print(f'Написано: {project["total symbols"]}')
    print(f'Прогресс: {project["progress"]}%')
    print(f'Среднее за сессию: {avg_symbols}')
    print(f'Создан: {project['created'].strftime("%d.%m.%y")}')

    dd = project["deadline"]["date"]
    if dd != 'Нет':
        dd_str = datetime.strftime(dd, '%d.%m.%y')
        print(f'Дедлайн: {dd_str}')
        print(f'Дней в стрике: {len(project["streaks"])}')
    else:
        print('Дедлайн: Нет')

    print(f'Всего записей: {len(notes)}')

    input('\nДля выхода нажмите Enter.')
    main_menu()

main_menu()