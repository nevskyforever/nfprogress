import pickle

import game
from datetime import date, datetime, timedelta
from random import randint

TEST_DATE = None
version = '1.2.4.3'
last_update = '15.01.26'

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
            print('Новых пока нет.\n')
        for i in new:
            print(i)
    if len(read) != 0:
        print('ПРОЧИТАННЫЕ УВЕДОМЛЕННИЯ\n')
        for i in read:
            print(i)

    do = input('\nДля очистки прочитанных введите 1'
               '\nДля выхода введите Enter: ')

    if do == '1':
        # Перемещаем новые в прочитанные, затем очищаем новые
        notifications['read'] = []
        data['notifications'] = notifications
        save_data(data)  # ✅ Сохраняем полные данные!
        print('\nПрочитанные уведомления очищены.\n')
        main_menu()
    else:
        notifications['read'].extend(notifications['new'])
        notifications['new'] = []
        data['notifications'] = notifications
        save_data(data)  # ✅ Сохраняем полные данные!
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
        else:
            deadline = datetime.strptime(deadline_input, '%d.%m.%y')
            deadline_str = deadline.strftime('%d.%m.%y')
    except ValueError:
        print('\n ЗНАЧЕНИЕ НЕКОРРЕКТНО (Дедлайн установлен как "Нет") \n')
        deadline = 'Нет'
        deadline_str = 'Нет'

    data['projects']['active'][name] = {
        'goal': goal,
        'created': today_for_test(),
        'total symbols': 0,
        'progress': 0,
        'notes': {},
        'streaks': [],
        'deadline': {'date': deadline, 'days left': (deadline.date() - date.today()).days}
    }
    data['last'] = name
    save_data(data)
    print(f'\nПроект {name} создан\n')

    # === УВЕДОМЛЕНИЕ О СОЗДАНИИ ===
    timestamp = datetime.now().strftime('%H:%M %d.%m.%y')
    notification_text = f'🆕 Проект "{name}" создан (цель: {goal} сим., дедлайн: {deadline_str})'
    notification = f'{timestamp}: {notification_text}'

    # Добавляем в уведомления
    notifications = data.get('notifications', {'new': [], 'read': []})
    notifications['new'].append(notification)
    data['notifications'] = notifications
    save_data(data)

    print(f'📌 {notification}\n')

    main_menu()


def view_projects():
    data = load_data()
    projects = data['projects']['active']

    print('\nПРОСМОТР ПРОЕКТОВ\n')

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
                print(f'Название: {name}, прогресс: {progress}%, написано/цель: {symbols}/{goal}\n')
            else:
                deadline_str = datetime.strftime(deadline, '%d.%m.%y')
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
    notifications = data.get('notifications', {'new': [], 'read': []})
    new_notifications = notifications['new']

    goal = project['goal']
    last_symbols = project['total symbols']
    need_symbols = goal - last_symbols
    today_dt = today_for_test()

    if isinstance(today_dt, datetime):
        today_date = today_dt.date()
    else:
        today_date = today_dt

    deadline = project['deadline']['date']

    print(f'Текущее кол-во символов в {choice}: {last_symbols} сим.')
    print(f'Осталось написать до цели: {need_symbols} сим.')

    today_goal = 0
    if deadline != 'Нет':
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

    # === УВЕДОМЛЕНИЕ: НОВАЯ ЗАПИСЬ ===
    timestamp = datetime.now().strftime('%H:%M %d.%m.%y')
    entry_notification = f'{timestamp} в {choice}: ✏️ Добавлено {session_added} сим.'
    new_notifications.append(entry_notification)
    print(f'📌 {entry_notification}')

    # === ИГРОВЫЕ БОНУСЫ ===
    if game.load_game() is not None and session_added > 0:
        coins = game.give_coins(session_added)
        exps = game.give_exps(session_added)
        msg_game_bonus = f'Получено {coins} монет и {exps} опыта'
        game_notification = f'{timestamp} в {choice}: 🎮 {msg_game_bonus}'
        new_notifications.append(game_notification)
        print(f'📌 {game_notification}\n')

    # === ПРОВЕРКА СТРИКА ===
    if session_added > 0 or today_total_progress > 0:
        streak_status = chek_streak(choice, today_total_progress, today_goal)
        data = load_data()
        current_streak = len(data['projects']['active'][choice]['streaks'])

        # === УВЕДОМЛЕНИЯ ПО СТРИКУ ===
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

        # === БОНУС ЗА СТРИК ===
        if game.load_game() is not None and streak_status:
            notes = data['projects']['active'][choice]['notes']
            if today_date in notes:
                if not notes[today_date].get('streak_bonus', False):
                    bonus_msg = game.give_streak_bonus(streak_status, new_symbols)
                    bonus_notification = f'{timestamp} в {choice}: 🎁 {bonus_msg}'
                    new_notifications.append(bonus_notification)
                    print(f'📌 {bonus_notification}\n')
                    notes[today_date]['streak_bonus'] = True
                    save_data(data)

    # === ЗАВЕРШЕНИЕ ПРОЕКТА ===
    if goal <= new_symbols:
        complete_notification = f'{timestamp} в {choice}: 🏆 Проект завершен!'
        new_notifications.append(complete_notification)
        print(f'📌 {complete_notification}')

        if game.load_game() is not None:
            complete_bonus = game.give_complete_bonus(True, new_symbols)
            bonus_notification = f'{timestamp} в {choice}: 🎉 {complete_bonus}'
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

    # === СОХРАНЯЕМ ВСЕ УВЕДОМЛЕНИЯ ===
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
            new_deadline = datetime.strptime(deadline_str, '%d.%m.%y')
            data = load_data()
            old_deadline = data['projects']['active'][choice]['deadline']['date']

            # Форматируем для вывода
            old_deadline_str = old_deadline.strftime('%d.%m.%y') if old_deadline != 'Нет' else 'Нет'
            new_deadline_str = new_deadline.strftime('%d.%m.%y')

            data['projects']['active'][choice]['deadline'] = {
                'date': new_deadline,
                'days left': (new_deadline.date() - date.today()).days
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

            # Уведомление с направлением изменения
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

def main_menu():
    # === ПОСЛЕДНЕЕ УВЕДОМЛЕНИЕ ===
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
    # === СЧЕТЧИК УВЕДОМЛЕНИЙ ===
    print(f'6 - Уведомления ({count_new} новых)' if count_new > 0 else '6 - Уведомления')
    print('7 - Подробности о проекте')
    print('8 - О программе')

    last = data.get('last', None)

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
        new_note(last)

if __name__ == '__main__':
    main_menu()
