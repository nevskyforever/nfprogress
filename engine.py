import pickle

import game
from datetime import date, datetime, timedelta
from random import randint

version = '1.3'
last_update = '03.02.26'


def today_for_test():
    TEST_DATE = None #date(2026, 1, 31)
    if TEST_DATE is None:
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


def about_program():
    print('Автор: nevskyforever')
    print(f'Версия приложения: {version}')
    print(f'Дата последнего обновления: {last_update}')
    input('\nДля выхода в главное меню нажмите Enter: ')
    main_menu()


def notifications_view():
    print('\nУВЕДОМЛЕНИЯ\n')
    data = load_data()
    notifications = data.get('notifications', {'new': [], 'read': []})
    new = notifications['new']
    read = notifications['read']

    if len(new) == 0 and len(read) == 0:
        print('Уведомлений пока нет.')
    else:
        print('НОВЫЕ УВЕДОМЛЕННИЯ\n')
        if len(new) == 0:
            print('Новых пока нет.')
        for i in new:
            print(i)
    if len(read) != 0:
        print('\nПРОЧИТАННЫЕ УВЕДОМЛЕННИЯ\n')
        for i in read:
            print(i)

    do = input('\nДля очистки прочитанных введите 1'
               '\nДля выхода введите Enter: ')

    if do == '1':
        notifications['read'] = []
        data['notifications'] = notifications
        save_data(data)
        print('\nПрочитанные уведомления очищены.\n')
        main_menu()
    else:
        notifications['read'].extend(notifications['new'])
        notifications['new'] = []
        data['notifications'] = notifications
        save_data(data)
        main_menu()


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
        main_menu()
        return

    deadline_input = input('Введите дедлайн проекта в формате дд.мм.гг \n или Enter, чтобы пропустить: ')
    try:
        if deadline_input == '':
            deadline = 'Нет'
            deadline_str = 'Нет'
            days_left = 0
        else:
            deadline = datetime.strptime(deadline_input, '%d.%m.%y').date()
            deadline_str = deadline.strftime('%d.%m.%y')
            days_left = (deadline - date.today()).days
    except ValueError:
        print('\n ЗНАЧЕНИЕ НЕКОРРЕКТНО (Дедлайн установлен как "Нет") \n')
        deadline = 'Нет'
        deadline_str = 'Нет'
        days_left = 0

    data['projects']['active'][name] = {
        'goal': goal,
        'created': today_for_test(),
        'total symbols': 0,
        'progress': 0,
        'notes': {},
        'streaks': [],
        'deadline': {'date': deadline, 'days left': days_left}
    }
    data['last'] = name
    save_data(data)
    print(f'\nПроект {name} создан\n')

    timestamp = datetime.now().strftime('%H:%M %d.%m.%y')
    notification_text = f'🆕 Проект "{name}" создан (цель: {goal} сим., дедлайн: {deadline_str})'
    notification = f'{timestamp}: {notification_text}'

    notifications = data.get('notifications', {'new': [], 'read': []})
    notifications['new'].append(notification)
    data['notifications'] = notifications
    save_data(data)

    print(f'📌 {notification}\n')

    main_menu()


def view_projects():
    data = load_data()
    projects = data['projects']['active']

    # --- БЛОК ОБНОВЛЕНИЯ ДЕДЛАЙНОВ ---
    today = today_for_test()
    updated = False

    for name in projects:
        proj = projects[name]
        if proj['deadline']['date'] != 'Нет':
            deadline_val = proj['deadline']['date']

            # Приводим к date если это datetime
            if isinstance(deadline_val, datetime):
                deadline_val = deadline_val.date()
                proj['deadline']['date'] = deadline_val
                updated = True

            actual_days_left = (deadline_val - today).days

            if proj['deadline']['days left'] != actual_days_left:
                proj['deadline']['days left'] = actual_days_left
                updated = True

    if updated:
        save_data(data)
    # ---------------------------------

    print('\nПРОСМОТР ПРОЕКТОВ\n')

    if len(projects) == 0:
        print('\nАктивных проектов пока нет.')
    else:
        if 'settings' not in data:
            data['settings'] = {}
        if 'view_projects' not in data['settings']:
            data['settings']['view_projects'] = None
        save_data(data)

        view_settings = data['settings']['view_projects']

        if view_settings == 'progress':
            print('Сортировка: по прогрессу (от меньшего к большему)\n')
            projects = dict(sorted(projects.items(), key=lambda item: item[1]['progress']))
        elif view_settings == 'deadline':
            print('Сортировка: по дедлайну (от большего к меньшему)\n')
            projects = dict(sorted(projects.items(), key=lambda item: item[1]['deadline']['days left']))

        for name in projects.keys():
            if not isinstance(projects[name], dict):
                continue

            proj = projects[name]
            goal = proj['goal']
            progress = proj['progress']
            symbols = proj['total symbols']
            deadline = proj['deadline']['date']

            if deadline == 'Нет':
                print(f'Название: {name}, прогресс: {progress}%, написано/цель: {symbols}/{goal}\n')
            else:
                deadline_str = deadline.strftime('%d.%m.%y')
                days_left = proj['deadline']['days left']
                streaks = len(proj['streaks'])
                print(f'Название: {name}, прогресс: {progress}%, написано: {symbols}/{goal}, '
                      f'дедлайн: {deadline_str}, дней: {days_left}, стрик: {streaks}\n')

    archived = data['projects'].get('archive', {})
    completed = data['projects'].get('complete', {})

    print('\nДля выхода нажмите Enter\n')

    if len(archived) > 0:
        print('Для просмотра проектов в архиве введите 1')
    if len(completed) > 0:
        print('Для просмотра завершенных проектов введите 2')
    print('Для сортировки проектов по прогрессу введите p')
    print('Для сортировки проектов по дедлайну введите d\n')

    if len(archived) > 0 or len(completed) > 0:
        print()

    do = input('Выбор: ')

    if do == '':
        main_menu()
        return

    if do == 'p':
        data['settings']['view_projects'] = 'progress'
        save_data(data)
        view_projects()
        return

    if do == 'd':
        data['settings']['view_projects'] = 'deadline'
        save_data(data)
        view_projects()
        return

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

                key = randint(1000, 9999)
                print(f'Удаление "{choice_name}" необратимо!')

                try:
                    approve = int(input(f'Для подтверждения введите {key}: '))
                    if approve == key:
                        data = load_data()
                        del data['projects']['complete'][choice_name]
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
            return None


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
        deadline = deadline.date()
        project['deadline']['date'] = deadline

    deadline_date = None if deadline == 'Нет' else deadline

    # Проверка на завершение всего проекта
    if total >= goal:
        if deadline_date is None or today <= deadline_date:
            return 'Complete'

    yesterday = today - timedelta(days=1)

    if today_goal <= 0:
        return 'Today'

    # Получаем дату ПОСЛЕДНЕГО стрика
    last_streak_date = None
    if len(streaks) > 0:
        last = streaks[-1]
        if isinstance(last, datetime):
            last_streak_date = last.date()
        else:
            last_streak_date = last

    # --- ГЛАВНАЯ ПРОВЕРКА ---
    if last_streak_date == today:
        return 'Done'

    if symbol_progress < today_goal:
        return 'No'

    # --- ЛОГИКА ОБНОВЛЕНИЯ СТРИКА ---
    streak_status = None

    if len(streaks) == 0:
        streaks.append(today)
        streak_status = 'Start'

    elif last_streak_date == yesterday:
        streaks.append(today)
        streak_status = 'Go'

    else:
        lost_days = len(streaks)
        streaks = [today]
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
    notifications = data.get('notifications', {'new': [], 'read': []})
    new_notifications = notifications['new']

    goal = project['goal']
    last_symbols = project['total symbols']
    need_symbols = goal - last_symbols
    streaks = project['streaks']
    today_date = today_for_test()

    deadline = project['deadline']['date']

    # Нормализация дедлайна
    if isinstance(deadline, datetime):
        deadline = deadline.date()
        project['deadline']['date'] = deadline

    print(f'Текущее кол-во символов в {choice}: {last_symbols} сим.')
    if today_date not in streaks:
        print(f'Осталось написать до цели: {need_symbols} сим.')
    else:
        print('Цель на сегодня уже выполнена.')

    today_goal = 0
    if deadline != 'Нет':
        days_left = (deadline - today_date).days
        if days_left > 0:
            raw_goal = need_symbols // days_left
            today_goal = raw_goal if raw_goal > 0 else 1
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

    session_added = new_symbols - last_symbols
    if session_added < 0:
        session_added = 0

    current_today_progress = 0
    if today_date in project['notes']:
        current_today_progress = project['notes'][today_date].get('symbol_progress', 0)

    today_total_progress = current_today_progress + session_added

    progress = round(new_symbols / goal * 100)

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

    timestamp = datetime.now().strftime('%H:%M %d.%m.%y')
    entry_notification = f'{timestamp} в {choice}: ✏️ Добавлено {session_added} сим.'
    new_notifications.append(entry_notification)
    print(f'📌 {entry_notification}')

    if game.load_game() is not None and session_added > 0:
        coins = game.give_coins(session_added)
        exps = game.give_exps(session_added)
        msg_game_bonus = f'Получено {coins} монет и {exps} опыта'
        game_notification = f'{timestamp} в {choice}: 🎮 {msg_game_bonus}'
        new_notifications.append(game_notification)
        print(f'📌 {game_notification}\n')

    streak_status = None

    if session_added > 0 or today_total_progress > 0:
        streak_status = chek_streak(choice, today_total_progress, today_goal)
        data = load_data()
        current_streak = len(data['projects']['active'][choice]['streaks'])

        if streak_status == 'Start':
            streak_notification = f'{timestamp} в {choice}: 🔥 Старт стрика!'
            new_notifications.append(streak_notification)
            print(f'📌 {streak_notification}\n')
        elif streak_status == 'Go':
            streak_notification = f'{timestamp} в {choice}: 🔥 Стрик продлен! {current_streak} дн подряд'
            new_notifications.append(streak_notification)
            print(f'📌 {streak_notification}\n')
        elif streak_status == 'Done':
            done_notification = f'{timestamp} в {choice}: ✅ Цель на сегодня выполнена!'
            new_notifications.append(done_notification)
            print(f'📌 {done_notification}\n')
        elif streak_status and streak_status.startswith('Lose'):
            lost = streak_status.split()[1]
            lose_notification = f'{timestamp} в {choice}: ❌ Стрик прерван (потеряно {lost} дн)'
            new_notifications.append(lose_notification)
            print(f'📌 {lose_notification}\n')

        if game.load_game() is not None and deadline != 'Нет' and streak_status.split()[0] in ['Start', 'Go', 'Lose']:
            bonus_msg = game.give_streak_bonus(streak_status, new_symbols)
            bonus_notification = f'{timestamp} в {choice}: 🔥 {bonus_msg}'
            new_notifications.append(bonus_notification)
            print(f'📌 {bonus_notification}\n')

    # === ПРОВЕРКА ЗАВЕРШЕНИЯ ПРОЕКТА ===
    if goal <= new_symbols:
        print(f'\n🎯 Проект "{choice}" достиг цели ({new_symbols}/{goal} сим.)!\n')

        while True:
            choice_complete = input(
                'Что вы хотите сделать?\n1 - Завершить проект\n2 - Изменить цель и продолжить\n> ').strip()

            if choice_complete == '1':
                complete_notification = f'{timestamp} в {choice}: 🏆 Проект завершен!'
                new_notifications.append(complete_notification)
                print(f'📌 {complete_notification}')

                if game.load_game() is not None:
                    complete_bonus = game.give_complete_bonus(True, new_symbols)
                    bonus_notification = f'{timestamp} в {choice}: 🎉 {complete_bonus}'
                    new_notifications.append(bonus_notification)
                    print(f'📌 {bonus_notification}\n')
                if game.load_game() is not None:
                    bonus_msg = game.give_streak_bonus(streak_status, new_symbols)
                    bonus_notification = f'{timestamp} в {choice}: 🔥 {bonus_msg}'
                    new_notifications.append(bonus_notification)
                    print(f'📌 {bonus_notification}\n')

                data = load_data()
                if 'complete' not in data['projects']:
                    data['projects']['complete'] = {}
                data['projects']['complete'][choice] = data['projects']['active'][choice]
                del data['projects']['active'][choice]
                data['notifications'] = notifications
                save_data(data)
                main_menu()
                return

            elif choice_complete == '2':
                try:
                    new_goal = input('Введите новую цель по символам: ').strip()
                    if new_goal == '':
                        print('Отменено.\n')
                        break
                    new_goal = int(new_goal)

                    if new_goal <= new_symbols:
                        print('⚠️ Новая цель должна быть больше текущего кол-ва символов!\n')
                        continue

                    data = load_data()
                    data['projects']['active'][choice]['goal'] = new_goal
                    new_progress = round(new_symbols / new_goal * 100)
                    data['projects']['active'][choice]['progress'] = new_progress
                    data['notifications'] = notifications
                    save_data(data)

                    goal_notification = f'{timestamp} в {choice}: 🎯 Цель изменена на {new_goal} сим.'
                    new_notifications.append(goal_notification)
                    print(f'📌 {goal_notification}\n')

                    if deadline != 'Нет':
                        if deadline >= today_date:
                            deadline_str = deadline.strftime('%d.%m.%y')
                            print(f'Текущий дедлайн: {deadline_str}\n')

                            change_deadline_input = input(
                                'Изменить дедлайн? (введите новую дату дд.мм.гг или Enter для пропуска): ').strip()

                            if change_deadline_input != '':
                                try:
                                    new_deadline = datetime.strptime(change_deadline_input, '%d.%m.%y').date()
                                    old_deadline_str = deadline.strftime('%d.%m.%y')
                                    new_deadline_str = new_deadline.strftime('%d.%m.%y')

                                    data['projects']['active'][choice]['deadline'] = {
                                        'date': new_deadline,
                                        'days left': (new_deadline - date.today()).days
                                    }
                                    data['notifications'] = notifications
                                    save_data(data)

                                    deadline_notification = f'{timestamp} в {choice}: 📅 Дедлайн изменен: {old_deadline_str} → {new_deadline_str}'
                                    new_notifications.append(deadline_notification)
                                    print(f'📌 {deadline_notification}\n')

                                except ValueError:
                                    print('⚠️ Ошибка формата даты. Дедлайн не изменен.\n')

                    data['notifications'] = notifications
                    save_data(data)
                    main_menu()
                    return

                except ValueError:
                    print('⚠️ Введите корректное число.\n')
                    continue
            else:
                print('⚠️ Выберите 1 или 2.\n')
                continue

    data['notifications'] = notifications
    save_data(data)
    main_menu()


def change_project():
    print('\nИЗМЕНЕНИЕ ПРОЕКТА\n')
    choice = choice_project()
    if choice is None:
        return

    def get_timestamp():
        return datetime.now().strftime('%H:%M %d.%m.%y')

    def add_notification(text):
        data = load_data()
        notifications = data.get('notifications', {'new': [], 'read': []})
        timestamp = get_timestamp()
        notification = f'{timestamp}: {text}'
        notifications['new'].append(notification)
        data['notifications'] = notifications
        save_data(data)
        print(f'📌 {notification}')

    def change_name():
        data = load_data()
        new_name = input(f'Введите новое имя для "{choice}": ')
        if new_name != '':
            data['projects']['active'][new_name] = data['projects']['active'][choice]
            del data['projects']['active'][choice]
            if data['last'] == choice:
                data['last'] = new_name
            save_data(data)
            print(f'\nИмя изменено на {new_name}.\n')
            add_notification(f'✏️ Проект "{choice}" переименован в "{new_name}"')
        main_menu()

    def change_goal():
        try:
            new_goal = int(input(f'Новая цель для "{choice}": '))
            if new_goal > 0:
                data = load_data()
                old_goal = data['projects']['active'][choice]['goal']
                data['projects']['active'][choice]['goal'] = new_goal
                save_data(data)
                print('Цель изменена.\n')
                add_notification(f'🎯 Цель "{choice}" изменена: {old_goal} → {new_goal} сим.')
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
            new_deadline = datetime.strptime(deadline_str, '%d.%m.%y').date()
            data = load_data()
            old_deadline = data['projects']['active'][choice]['deadline']['date']

            old_deadline_str = old_deadline.strftime('%d.%m.%y') if old_deadline != 'Нет' else 'Нет'
            new_deadline_str = new_deadline.strftime('%d.%m.%y')

            data['projects']['active'][choice]['deadline'] = {
                'date': new_deadline,
                'days left': (new_deadline - date.today()).days
            }
            save_data(data)
            print(f'\nДедлайн изменён.\n')
            add_notification(f'📅 Дедлайн "{choice}" изменен: {old_deadline_str} → {new_deadline_str}')
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
                add_notification(f'🗑️ Проект "{choice}" удален')
            else:
                print('\nНеверный код.\n')
        except ValueError:
            print('\nОшибка.\n')
        main_menu()

    def change_symbols():
        print(f'\nИЗМЕНЕНИЕ СИМВОЛОВ В "{choice}"\n')
        data = load_data()

        current = data['projects']['active'][choice]['total symbols']
        print(f'Текущее кол-во: {current}')

        try:
            new_symbols = int(input('Новое кол-во символов: '))
            old_symbols = current
            diff = new_symbols - old_symbols

            data['projects']['active'][choice]['total symbols'] = new_symbols
            goal = data['projects']['active'][choice]['goal']
            old_progress = data['projects']['active'][choice]['progress']
            new_progress = round(new_symbols / goal * 100)
            data['projects']['active'][choice]['progress'] = new_progress

            save_data(data)
            print('\nИЗМЕНЕНИЯ СОХРАНЕНЫ\n')

            if diff > 0:
                add_notification(
                    f'➕ Символы в "{choice}": +{diff} сим. ({old_symbols} → {new_symbols}, прогресс {old_progress}% → {new_progress}%)')
            elif diff < 0:
                add_notification(
                    f'➖ Символы в "{choice}": {diff} сим. ({old_symbols} → {new_symbols}, прогресс {old_progress}% → {new_progress}%)')
            else:
                add_notification(f'🔄 Попытка изменить символы в "{choice}" (значение не изменилось)')

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
            print(f'\n Проект {choice} направлен в архив \n')
            add_notification(f'📦 Проект "{choice}" отправлен в архив ({date.today().strftime('%d.%m.%y')})')
            main_menu()
        else:
            print('\n ДЕЙСТВИЕ ОТМЕНЕНО \n')
            main_menu()

    def add_custom_date_note():
        print(f'\n ДОБАВЛЕНИЕ ЗАПИСИ С ПРОИЗВОЛЬНОЙ ДАТОЙ \n')
        data = load_data()
        project = data['projects']['active'][choice]
        notes = project.get('notes', {})

        date_str = input('Введите дату записи (дд.мм.гг) или Enter для отмены: ')
        if date_str == '':
            print('\n ДЕЙСТВИЕ ОТМЕНЕНО \n')
            main_menu()
            return

        try:
            custom_date = datetime.strptime(date_str, '%d.%m.%y').date()
        except ValueError:
            print('\n ОШИБКА ФОРМАТА ДАТЫ \n')
            main_menu()
            return

        # Сортируем даты
        sorted_dates = sorted(notes.keys())
        prev_date = None
        prev_total = 0

        for d in sorted_dates:
            # Нормализуем дату если это datetime
            if isinstance(d, datetime):
                d = d.date()

            if d < custom_date:
                prev_date = d
                if isinstance(notes[d], dict) and 'last_total' in notes[d]:
                    prev_total = notes[d]['last_total']
            else:
                break

        print(f'\n--- КОНТЕКСТ ---')
        if prev_date:
            print(f'Предыдущая запись от {prev_date.strftime("%d.%m.%y")}: всего {prev_total} сим.')
        else:
            print(f'Предыдущих записей нет. Начальный отсчет: 0 сим.')

        if custom_date in notes:
            current_record_total = notes[custom_date].get('last_total', 0)
            print(f'⚠️ На дату {date_str} уже записано: всего {current_record_total} сим.')

        print('----------------')

        try:
            input_total = int(input(f'Введите ОБЩЕЕ кол-во символов, которое было {date_str}: '))
        except ValueError:
            print('\n НУЖНО ЧИСЛО \n')
            main_menu()
            return

        session_added = input_total - prev_total

        if session_added < 0:
            print(f'\n⚠️ Внимание: введенное значение ({input_total}) меньше предыдущего ({prev_total}).')
            print('Прогресс за день будет отрицательным. Если это ошибка, повторите ввод.\n')
            confirm = input('Нажмите Enter для продолжения или введите что-угодно для отмены: ')
            if confirm != '':
                main_menu()
                return

        notes[custom_date] = {
            'symbol_progress': session_added,
            'last_total': input_total
        }

        project['notes'] = notes

        latest_date = sorted(notes.keys())[-1]
        current_project_total = project['total symbols']

        if custom_date == latest_date or input_total > current_project_total:
            project['total symbols'] = input_total
            goal = project['goal']
            new_progress = round(input_total / goal * 100)
            project['progress'] = new_progress
            updated_msg = f'(Общий прогресс проекта обновлен: {new_progress}%)'
        else:
            updated_msg = '(Общий прогресс проекта не изменен, так как запись историческая)'

        data['projects']['active'][choice] = project
        save_data(data)

        print(f'\n✅ Запись сохранена: {date_str}')
        print(f'Всего на тот момент: {input_total} сим.')
        print(f'Записано в этот день ("symbol_progress"): {session_added} сим.')
        print(updated_msg + '\n')

        add_notification(f'📝 Ручная запись в "{choice}" за {date_str}: +{session_added} сим. (всего {input_total})')
        main_menu()

    print('1 - Изменить имя')
    print('2 - Изменить цель')
    print('3 - Изменить дедлайн')
    print('4 - Удалить проект')
    print('5 - Изменить кол-во символов (ручная правка)')
    print('6 - Отправить в архив')
    print('7 - Добавить запись с произвольной датой')

    do = input('\nВыберите действие: ')
    actions = {
        '1': change_name,
        '2': change_goal,
        '3': change_deadline,
        '4': delete_project,
        '5': change_symbols,
        '6': send_to_archive,
        '7': add_custom_date_note,
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

    created = project['created']
    if isinstance(created, datetime):
        created = created.date()
    print(f'Создан: {created.strftime("%d.%m.%y")}')

    dd = project["deadline"]["date"]
    if dd != 'Нет':
        if isinstance(dd, datetime):
            dd = dd.date()
        dd_str = dd.strftime('%d.%m.%y')
        print(f'Дедлайн: {dd_str}')
        print(f'Дней в стрике: {len(project["streaks"])}')
    else:
        print('Дедлайн: Нет')

    print(f'Всего записей: {len(notes)}')

    input('\nДля выхода нажмите Enter.')
    main_menu()


def main_menu():
    data = load_data()
    notifications = data.get('notifications', {'new': [], 'read': []})
    new_notifs = notifications['new']
    count_new = len(new_notifs)

    print(f'nfprogress\n')
    print(f'Сегодня: {today_for_test().strftime("%d.%m.%y")}')

    if new_notifs:
        last_notification = new_notifs[-1]
        print(f'\n📌 Последнее уведомление:'
              f'\n{last_notification}')

    print('\nЧто вы хотите сделать?\n')
    print('1 - Новая запись')
    print('2 - Просмотр проектов')
    print('3 - Новый проект')
    print('4 - Изменить проект')
    print('5 - Игровой режим')
    print(f'6 - Уведомления ({count_new} новых)' if count_new > 0 else '6 - Уведомления')
    print('7 - Подробности о проекте')
    print('8 - О программе')

    last = data.get('last', None)

    if last is not None and last not in data['projects']['active']:
        last = None

    if last is not None:
        print(f'\nЗапись в последний проект ({last}) - Enter')

    do_list = {
        '1': new_note,
        '2': view_projects,
        '3': new_project,
        '4': change_project,
        '5': game.menu,
        '6': notifications_view,
        '7': more_details,
        '8': about_program
    }

    do = input('\nВыберите пункт из меню: ')

    if do != '':
        try:
            do_list[do]()
        except KeyError:
            print('НЕПРАВИЛЬНЫЙ ВЫБОР')
            main_menu()
    else:
        if last is not None:
            new_note(last)
        else:
            main_menu()


if __name__ == '__main__':
    main_menu()
