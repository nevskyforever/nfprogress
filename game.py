import pickle
from datetime import timedelta

import engine
import game_data
from random import randint
from os import remove



def load_game():
    try:
        with open('game_mode.pkl', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return game_data.gamer()


def save_game(gamer):
    with open('game_mode.pkl', 'wb') as f:
        pickle.dump(gamer, f)


def update_gamer():
    gamer = load_game()
    if gamer is not None:
        level = gamer['level']
        exp = gamer['exp']
        health = gamer['health']
        data = engine.load_data()
        notifications = data.get('notifications', {'new': [], 'read': []})

        while level < len(game_data.levels) - 1 and exp >= game_data.levels[level]:
            new_level = level + 1
            coins_bonus = game_data.lvl_coins_bonus[level]

            gamer['level'] = new_level
            gamer['exp'] = exp - game_data.levels[level]
            gamer['health'] = 100
            gamer['coins'] += coins_bonus
            gamer['cf']['coins'] = game_data.cf_coins[level]
            gamer['cf']['exp'] = game_data.cf_exp[level]

            new_notification = f'ПОЛУЧЕН НОВЫЙ {new_level} УРОВЕНЬ! Ваш бонус: {coins_bonus} монет'
            print(new_notification)
            notifications['new'].append(new_notification)

            exp = gamer['exp']
            level = new_level

        save_game(gamer)
        engine.save_data(data)

        if health == 0:
            print('КРИТИЧЕСКИЙ УРОВЕНЬ ЗДОРОВЬЯ\n')
            health_recovery = gamer['items']['health_recovery']
            if health_recovery > 0:
                do = input('1 - Применить зелье восстановления: ')
                if do == '1':
                    print(game_data.health_recovery('use'))
                    gamer = load_game()
                    gamer['health'] = 100
                    save_game(gamer)
                    new_notification = 'ПЕРСОНАЖ СПАСЕН!'
                    notifications['new'].append(new_notification)
                    data['notifications'] = notifications
                    engine.save_data(data)
                    menu()
            else:
                if gamer['coins'] >= 100:
                    do = input('1 - Купить и применить зелье восстановления: ')
                    if do == '1':
                        print(game_data.health_recovery('buy'))
                        print(game_data.health_recovery('use'))
                        gamer = load_game()
                        gamer['health'] = 100
                        save_game(gamer)
                        new_notification = 'ПЕРСОНАЖ СПАСЕН!'
                        notifications['new'].append(new_notification)
                        data['notifications'] = notifications
                        engine.save_data(data)
                        menu()
                else:
                    print('У ВАС НЕТ НИ ЗЕЛЕЙ ВОСКРЕШЕНИЯ, НИ МОНЕТ НА ИХ ПОКУПКУ! ИГРОВОЙ ПРОГРЕСС ПОТЕРЯН!')
                    new_notification = 'ПЕРСОНАЖ ПОГИБ!'
                    notifications['new'].append(new_notification)
                    data['notifications'] = notifications
                    engine.save_data(data)
                    gamer = game_data.gamer.copy()
                    gamer['items'] = {'health_recovery': 0, 'health_add': 0, 'lottery_ticket': 0}
                    gamer['last_used'] = None
                    gamer['last_bought'] = None
                    save_game(gamer)
                    menu()
        else:
            print('Приключения ждут!\n')


def check_loan_penalty():
    """Проверяет просрочку кредита и наносит урон"""
    gamer = load_game()
    if gamer is None:
        return

    if not gamer.get('bank', None):
        return

    data = engine.load_data()
    notifications = data.get('notifications', {'new': [], 'read': []})

    loan_created = gamer['bank']['loan'].get('created_date')
    loan_return_date = gamer['bank']['loan'].get('return_date')
    last_penalty_date = gamer['bank']['loan'].get('last_penalty_date')

    if loan_created is None or loan_return_date is None:
        return

    today = engine.today_for_test()

    if today > loan_return_date:
        if last_penalty_date is None:
            days_to_penalize = (today - loan_return_date).days
        else:
            days_to_penalize = (today - last_penalty_date).days

        if days_to_penalize > 0:
            damage = days_to_penalize * 10
            gamer_health = gamer['health']
            gamer_health -= damage
            gamer['health'] = max(0, gamer_health)

            penalty_msg = f'⚠️ ШТРАФ ЗА ПРОСРОЧКУ КРЕДИТА: -{damage} ❤️ (Осталось: {gamer["health"]} ❤️)'
            print(penalty_msg)
            notifications['new'].append(penalty_msg)
            data['notifications'] = notifications
            engine.save_data(data)

            gamer['bank']['loan']['last_penalty_date'] = today
            save_game(gamer)


# === ФУНКЦИИ МЕНЮ ===

def show_about():
    print(game_data.about_mode)
    input('\nДля возврата в игровое меню нажмите Enter')
    menu()


def gamer_editor():
    password = ''
    do = input('Введите пароль: ')
    if do == password:
        print('\n РЕДАКТОР ПЕРСОНАЖА \n')
        gamer = load_game()
        print('Какой параметр вы хотите изменить?')
        params = list(gamer.keys())
        for i in range(len(params)):
            print(f' {i + 1}. {params[i]}')
        try:
            choice = int(input('Введите номер параметра: '))
            if params[choice - 1] not in ['cf', 'items', 'last_used', 'last_bought']:
                gamer[params[choice - 1]] = int(input(f'Введите значение параметра {params[choice - 1]}: '))
                save_game(gamer)
                print(f'Параметр {params[choice - 1]} изменен на {gamer[params[choice - 1]]}.')
            else:
                print('Этот параметр изменить нельзя')
        except (ValueError, IndexError):
            print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ!')
        menu()
    else:
        print('НЕПРАВИЛЬНЫЙ ПАРОЛЬ')
        menu()


def bank():
    print('БАНК')
    gamer = load_game()
    data = engine.load_data()
    notifications = data.get('notifications', {'new': [], 'read': []})
    gamer_coins = gamer.get('coins', 0)

    if not gamer.get('bank', None):
        gamer['bank'] = {
            'deposit': {
                'created_date': None,
                'withdrawal_date': None,
                'coins': 0,
                'income': 0
            },
            'loan': {
                'created_date': None,
                'return_date': None,
                'coins': 0,
                'return': 0,
                'last_penalty_date': None
            }
        }
        save_game(gamer)

    today = engine.today_for_test()
    deposit_coins = gamer['bank']['deposit']['coins']
    deposit_created = gamer['bank']['deposit'].get('created_date')
    deposit_withdrawal = gamer['bank']['deposit'].get('withdrawal_date')
    deposit_income = gamer['bank']['deposit']['income']

    loan_coins = gamer['bank']['loan']['coins']
    loan_return = gamer['bank']['loan']['return']
    loan_created = gamer['bank']['loan'].get('created_date')
    loan_return_date = gamer['bank']['loan'].get('return_date')

    # === РАСЧЕТ ПРОЦЕНТОВ ПО ВКЛАДУ ===
    if deposit_created is not None:
        days_passed = (today - deposit_created).days
        if days_passed > 0:
            deposit_income = deposit_coins * 0.01 * days_passed
        gamer['bank']['deposit']['income'] = deposit_income

    # === РАСЧЕТ ПРОЦЕНТОВ ПО КРЕДИТУ ===
    if loan_created is not None:
        days_passed = (today - loan_created).days
        if days_passed > 0:
            if loan_return_date and today > loan_return_date:
                days_overdue = (today - loan_return_date).days
                days_ontime = days_passed - days_overdue
                loan_return = (loan_coins * 0.01 * days_ontime) + (loan_coins * 0.02 * days_overdue)
            else:
                loan_return = loan_coins * 0.01 * days_passed
        gamer['bank']['loan']['return'] = loan_return

    gamer['bank']['chek'] = today
    save_game(gamer)

    # === ПОКАЗЫВАЕМ ИНФОРМАЦИЮ ===
    print(f'Ваши наличные монеты: {int(gamer_coins)}')

    if deposit_created is None:
        print('В банке нет вклада.')
    else:
        print(f'Вклад: {deposit_coins} монет (создан {deposit_created.strftime("%d.%m.%y")})')
        if deposit_withdrawal:
            print(f'  Дата снятия: {deposit_withdrawal.strftime("%d.%m.%y")}')
        print(f'  Доход: {deposit_income:.0f} монет')

    if loan_created is None:
        print('В банке нет кредита.')
    else:
        print(f'Кредит: {loan_coins} монет (взят {loan_created.strftime("%d.%m.%y")})')
        if loan_return_date:
            status = "✓ В срок" if today <= loan_return_date else "⚠ ПРОСРОЧЕН"
            print(f'  Дата возврата: {loan_return_date.strftime("%d.%m.%y")} {status}')
        print(f'  Проценты: {loan_return:.0f} монет')

    print()
    if deposit_created is None:
        print('1 - Сделать вклад')
    else:
        print('d - Снять депозит')
    if loan_created is None:
        print('2 - Взять кредит')
    else:
        print('c - Погасить кредит')

    do = input('Выбор (или Enter для выхода): ').strip()

    # === ВКЛАД: ВНЕСЕНИЕ ===
    if do == '1' and deposit_created is None:
        print('\nВНЕСЕНИЕ ВКЛАДА\n')
        print('Условия:\n1. Доход 1% в день\n2. Срок не ограничен\n')

        try:
            deposit_coins = int(input('Сумма: '))
            if deposit_coins > gamer_coins:
                print('Недостаточно денег')
                return bank()

            print('\nУкажите желаемую дату снятия вклада (дни от сегодня):')
            days_until_withdrawal = int(input('Через сколько дней: '))
            withdrawal_date = today + timedelta(days=days_until_withdrawal)

            gamer_coins -= deposit_coins
            gamer['coins'] = gamer_coins
            gamer['bank']['deposit']['created_date'] = today
            gamer['bank']['deposit']['withdrawal_date'] = withdrawal_date
            gamer['bank']['deposit']['coins'] = deposit_coins
            gamer['bank']['deposit']['income'] = 0
            save_game(gamer)

            print(f'\nВклад {deposit_coins} монет создан')
            notifications['new'].append(f'Вклад {deposit_coins} монет создан до {withdrawal_date.strftime("%d.%m.%y")}')
            data['notifications'] = notifications
            engine.save_data(data)
            print(f'Дата снятия: {withdrawal_date.strftime("%d.%m.%y")}\n')
            return bank()
        except ValueError:
            print('Ошибка ввода')
            return bank()

    # === ВКЛАД: СНЯТИЕ ===
    if do == 'd':
        print('\nСНЯТИЕ ДЕПОЗИТА\n')

        is_early_withdrawal = today < deposit_withdrawal

        if is_early_withdrawal:
            print(f'⚠ ВНИМАНИЕ: Вы снимаете вклад раньше срока!')
            print(f'Плановая дата: {deposit_withdrawal.strftime("%d.%m.%y")}')
            print(f'Если снять раньше, проценты БУДУТ ПОТЕРЯНЫ!')
            print(f'\nВы получите только основную сумму: {deposit_coins} монет')

            confirm = input('\n1 - Снять раньше срока (потерять проценты)\n2 - Отмена\nВыбор: ')

            if confirm == '1':
                gamer['coins'] += deposit_coins
                gamer['bank']['deposit'] = {'created_date': None, 'withdrawal_date': None, 'coins': 0, 'income': 0}
                save_game(gamer)
                print(f'\nСнято {deposit_coins} монет (проценты потеряны)\n')
                notifications['new'].append(f'Снято {deposit_coins} монет со вклада (проценты потеряны)')
                data['notifications'] = notifications
                engine.save_data(data)
            else:
                print('Отмена\n')
            return bank()
        else:
            total = deposit_coins + deposit_income
            gamer['coins'] += total
            gamer['bank']['deposit'] = {'created_date': None, 'withdrawal_date': None, 'coins': 0, 'income': 0}
            save_game(gamer)
            print(f'Снято {total:.0f} монет (основная сумма: {deposit_coins}, доход: {deposit_income:.0f})\n')
            notifications['new'].append(f'Снято {total} молнет со вклада с учетом доходов')
            data['notifications'] = notifications
            engine.save_data(data)
            return bank()

    # === КРЕДИТ: ВЗЯТИЕ ===
    if do == '2' and loan_created is None:
        print('\nВЗЯТИЕ КРЕДИТА\n')
        print('Условия:')
        print('1. Проценты 1% в день до срока возврата')
        print('2. При просрочке - 2% в день (двойной размер)')
        print('3. За каждый день просрочки - -10 ❤️ здоровья')
        print('4. Досрочное погашение без штрафа\n')

        try:
            loan_coins = int(input('Сумма кредита: '))

            print('\nУкажите планируемую дату возврата (дни от сегодня):')
            days_until_return = int(input('Через сколько дней: '))
            return_date = today + timedelta(days=days_until_return)

            gamer_coins += loan_coins
            gamer['coins'] = gamer_coins
            gamer['bank']['loan']['created_date'] = today
            gamer['bank']['loan']['return_date'] = return_date
            gamer['bank']['loan']['coins'] = loan_coins
            gamer['bank']['loan']['return'] = 0
            gamer['bank']['loan']['last_penalty_date'] = None
            save_game(gamer)

            print(f'\nКредит {loan_coins} монет взят')
            print(f'Срок возврата: {return_date.strftime("%d.%m.%y")}\n')
            notifications['new'].append(f'Взят кредит в {loan_coins} монет до {return_date.strftime("%d.%m.%y")}')
            data['notifications'] = notifications
            engine.save_data(data)
            return bank()
        except ValueError:
            print('Ошибка ввода')
            return bank()

    # === КРЕДИТ: ПОГАШЕНИЕ ===
    if do == 'c':
        print('\nПОГАШЕНИЕ КРЕДИТА\n')

        total_to_pay = loan_coins + loan_return
        is_overdue = loan_return_date and today > loan_return_date

        print(f'Основная сумма: {loan_coins} монет')
        print(f'Проценты: {loan_return:.0f} монет')

        if is_overdue:
            days_overdue = (today - loan_return_date).days
            print(f'⚠ ПРОСРОЧКА: {days_overdue} дн. (проценты удвоены!)')

        print(f'ВСЕГО К ВОЗВРАТУ: {total_to_pay:.0f} монет')
        print(f'У вас есть: {int(gamer_coins)} монет\n')

        if gamer_coins < total_to_pay:
            shortage = total_to_pay - gamer_coins
            print(f'❌ Недостаточно денег. Не хватает {shortage:.0f} монет')
            return bank()

        confirm = input('1 - Погасить кредит, Enter - отмена: ').strip()

        if confirm == '1':
            gamer['coins'] -= total_to_pay
            gamer['bank']['loan'] = {'created_date': None, 'return_date': None, 'coins': 0, 'return': 0,
                                     'last_penalty_date': None}
            save_game(gamer)
            status = "(с просрочкой)" if is_overdue else ""
            print(f'\n✓ Кредит погашен {status}. Выплачено {total_to_pay:.0f} монет\n')
            notifications['new'].append(f'✓ Кредит погашен {status}. Выплачено {total_to_pay:.0f} монет')
            data['notifications'] = notifications
            engine.save_data(data)
        return bank()

    if do == '':
        return menu()


def show_characteristics():
    gamer = load_game()
    cf_exp_val = gamer['cf']['exp']
    cf_coins = gamer['cf']['coins']
    print('\n КОЭФФИЦИЕНТЫ ПЕРСОНАЖА \n')
    print(f'Коэффициент умножения опыта: {cf_exp_val}')
    print(f'Коэффициент умножения монет: {cf_coins}')
    print('\n Коэффициенты умножения дают бонус к зарабатываемым монетам и опыту')
    print('Они зависят от уровня, предметов в инвентаре и примененных предметов')
    input("\nВыйти в игровое меню - Enter: ")
    menu()


def inventory():
    """Инвентарь для просмотра и использования предметов"""
    # Грузим данные персонажа
    gamer = load_game()
    coins = gamer['coins']
    items = gamer.get('items', {})

    print('ИНВЕНТАРЬ')
    print(f'\n Баланс: {int(coins)}')

    # Проверяем, есть ли предметы в инвентаре
    if items == {}:
        print('\nВаш инвентарь пуст!')
        return

    # Получаем реестр всех предметов
    registry = game_data.ITEM_REGISTRY

    # Группируем предметы из инвентаря по категориям
    inventory_by_category = {}
    for item_name in items:
        # Ищем предмет в реестре и определяем его категорию
        for category, category_items in registry.items():
            if item_name in category_items:
                if category not in inventory_by_category:
                    inventory_by_category[category] = []
                inventory_by_category[category].append(item_name)
                break

    # Показываем категории, которые есть в инвентаре
    categories = list(inventory_by_category.keys())
    print('\nКатегории предметов:')
    for i, category in enumerate(categories, 1):
        print(f'{i}. {category}')

    # Получаем желаемый номер категории
    try:
        choice_category = int(input('Введите номер нужной категории: ')) - 1
    except ValueError:
        print('Некорректный номер категории!')
        return

    if choice_category < 0 or choice_category >= len(categories):
        print('Категория не найдена!')
        return

    # Получаем выбранную категорию
    selected_category = categories[choice_category]
    items_in_category = inventory_by_category[selected_category]

    # Показываем предметы в выбранной категории
    print(f'\nПредметы в категории "{selected_category}":')
    for i, item_name in enumerate(items_in_category, 1):
        print(f'{i}. {item_name}')

    # Получаем номер желаемого предмета
    try:
        choice_item = int(input('Введите номер предмета для использования: ')) - 1
    except ValueError:
        print('Некорректный номер предмета!')
        return

    if choice_item < 0 or choice_item >= len(items_in_category):
        print('Предмет не найден!')
        return

    # Получаем объект предмета
    selected_item_name = items_in_category[choice_item]
    item_obj = registry[selected_category][selected_item_name]

    # Используем предмет
    print(item_obj.use())


def shop():
    """Магазин для покупки предметов"""
    # Грузим данные персонажа
    gamer = load_game()
    coins = gamer['coins']
    items = gamer.get('items', {})
    print('МАГАЗИН')
    print(f'\n Баланс: {int(coins)}')

    # Показ категорий в магазине
    registry = game_data.ITEM_REGISTRY
    categories = list(registry.keys())
    for i, category in enumerate(categories, 1):
        print(f'{i}. {category}')

    # Получаем желаемый номер категории
    try:
        choice_category = int(input('Введите номер нужной категории: ')) - 1
    except ValueError:
        print('Некорректный номер категории товара!')
        choice_category = int(input('Введите номер нужной категории: ')) - 1

    # Получаем выбранную категорию
    selected_category = categories[choice_category]
    items_in_category = registry[selected_category]

    # Показываем товары в выбранной категории
    item_names = list(items_in_category.keys())
    for i, item_name in enumerate(item_names, 1):
        print(f'{i}. {item_name}')

    # Получаем номер желаемого товара
    try:
        choice_item = int(input('Введите номер нужного товара: ')) - 1
    except ValueError:
        print('Некорректный номер товара!')
        choice_item = int(input('Введите номер нужного товара: ')) - 1

    # Получаем объект товара
    selected_item_name = item_names[choice_item]
    item_obj = items_in_category[selected_item_name]
    print(item_obj.buy())

    shop()


def use_last_item():
    """Использовать последний использованный предмет"""
    gamer = load_game()
    last_used = gamer.get('last_used', None)

    if last_used:
        use_item(last_used)
    else:
        print('Нет последнего использованного предмета')

    menu()


def buy_last_item():
    """Купить последний купленный предмет"""
    gamer = load_game()
    last_bought = gamer.get('last_bought', None)

    item_costs = {
        'health_add': 10,
        'health_recovery': 100,
        'lottery_ticket': 10,
        'freeze': 100,
    }

    if last_bought and last_bought in item_costs:
        cost = item_costs[last_bought]
        buy_item(last_bought, cost)
    else:
        print('Нет последней покупки')

    menu()


def disable_mode():
    key = randint(1000, 9999)
    print('Если вы выключите режим, все его данные будут удалены без возможности восстановления \n'
          'При активации режима вам придется начинать сначала.')
    try:
        approve = int(input(f'Подтвердите удаление введя {key}: '))
        if approve == key:
            remove('game_mode.pkl')
            print('\n Игровой режим удален \n')
            from engine import main_menu
            main_menu()
        else:
            print('ОТМЕНЕНО')
            menu()
    except ValueError:
        print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ')
        menu()


def give_exps(symbols):
    gamer = load_game()
    if gamer is None:
        return 0
    level = gamer['level']
    cf = game_data.cf_exp[level] if level < len(game_data.cf_exp) else game_data.cf_exp[-1]
    exps = symbols * 2 * cf
    gamer['exp'] += exps
    save_game(gamer)
    return int(exps)


def give_streak_bonus(streak_status, total_symbols):
    gamer = load_game()
    if gamer is None:
        return 'Игровой режим не активирован'

    level = gamer['level']
    health = gamer['health']
    cf_coins = game_data.cf_coins[level] if level < len(game_data.cf_coins) else game_data.cf_coins[-1]
    cf_exp_val = game_data.cf_exp[level] if level < len(game_data.cf_exp) else game_data.cf_exp[-1]

    if streak_status == 'Go':
        coins = int(10 * (cf_coins + 0.5))
        gamer['coins'] += coins
        save_game(gamer)
        return f'Вы продлили стрик и получили {coins} монет! \n Так держать!'

    elif streak_status == 'Done':
        return f'Бонус за стрик сегодня уже получен, но символы лишними не будут ;)'

    elif streak_status == 'Complete':
        exps = int(1000 * (total_symbols / 1000) * (cf_exp_val + 4))
        coins = int((10 * (cf_coins + 2)) + 100)
        gamer['coins'] += coins
        gamer['exp'] += exps
        save_game(gamer)
        return (
            f'Вы вовремя завершили проект и получили дополнительный бонус в {coins} монет и {exps} опыта!'
            f'\nЭто просто потрясающе!')

    elif streak_status == 'Start':
        coins = int(10 * (cf_coins + 0.25))
        gamer['coins'] += coins
        save_game(gamer)
        return f'Вы получили {coins} монет за старт стрика! \n Отличное начало!'

    elif streak_status.split()[0] == 'Lose':
        try:
            lose_days = int(streak_status.split()[1])
            health -= 5 * lose_days
            if health <= 0:
                gamer['health'] = 0
                save_game(gamer)
                return f'\n ВЫ ПОТЕРЯЛИ СЛИШКОМ МНОГО ЗДОРОВЬЯ! \n \n Вернитесь в игровое меню, чтобы применить зелье воскрешения, \n если оно есть.'
            else:
                gamer['health'] = health
                save_game(gamer)
                return f'Стрик потерян. Потеряно здоровья: {5 * lose_days}'
        except (ValueError, IndexError):
            return 'Ошибка при обработке потери стрика'

    return ''


def give_complete_bonus(complete_status, total_symbols):
    gamer = load_game()
    if gamer is None:
        return 'Игровой режим не активирован'

    level = gamer['level']
    cf_coins = game_data.cf_coins[level] if level < len(game_data.cf_coins) else game_data.cf_coins[-1]
    cf_exp_val = game_data.cf_exp[level] if level < len(game_data.cf_exp) else game_data.cf_exp[-1]

    if complete_status is True:
        exps = int(1000 * (total_symbols / 1000) * (cf_exp_val + 2))
        coins = int((10 * (cf_coins + 1.5)) + 100)
        gamer['coins'] += coins
        gamer['exp'] += exps
        save_game(gamer)
        return (f'Вы завершили работу над проектом и получили бонус в {coins} монет и {exps} опыта!'
                f'\nЭто того стоило!')

    return ''


def menu():
    if load_game() is None:
        do = input('ИГРОВОЙ РЕЖИМ НЕ АКТИВИРОВАН \n'
                   '\n Для активации режима введите 1, для выхода в главное меню - Enter: ')
        if do == '1':
            gamer = game_data.gamer.copy()
            gamer['items'] = {'health_recovery': 0, 'health_add': 0, 'lottery_ticket': 0}
            gamer['last_used'] = None
            gamer['last_bought'] = None
            save_game(gamer)
            menu()
        elif do == '':
            from engine import main_menu
            main_menu()
        else:
            menu()
        return

    # ПРОВЕРКА ШТРАФА ЗА ПРОСРОЧКУ КРЕДИТА
    check_loan_penalty()

    update_gamer()
    gamer = load_game()
    level = gamer['level']
    max_exp = game_data.levels[level] if level < len(game_data.levels) else game_data.levels[-1]

    print(f'\nУровень: {gamer["level"]}')
    print(f'Здоровье: {gamer["health"]}')
    print(f'Монеты: {int(gamer["coins"])}')
    print(f'Опыт: {int(gamer["exp"])}/{max_exp}\n')

    print('1 - О режиме')
    print('2 - Редактор персонажа')
    print('3 - Характеристики персонажа')
    print('4 - Инвентарь')
    print('5 - Магазин')
    print('6 - Банк')

    last_used = gamer.get('last_used', None)
    item_names = {
        'health_recovery': 'Зелья воскрешения',
        'health_add': 'Зелья восстановления',
        'lottery_ticket': 'Лотерейный билет',
    }

    if last_used and last_used in item_names:
        count = gamer['items'].get(last_used, 0)
        print(f'u - Снова использовать - {item_names[last_used]} ({count})')

    last_bought = gamer.get('last_bought', None)
    item_costs = {
        'health_add': 10,
        'health_recovery': 100,
        'lottery_ticket': 15,
    }

    if last_bought and last_bought in item_costs:
        cost = item_costs[last_bought]
        count = gamer['items'].get(last_bought, 0)
        print(f'b - Купить еще - {item_names.get(last_bought, "Предмет")} ({count}) - {cost} монет')

    print('8 - Выключить режим')
    print('Enter - Выйти в главное меню\n')

    do_list = {
        '1': show_about,
        '2': gamer_editor,
        '3': show_characteristics,
        '4': inventory,
        '5': shop,
        '6': bank,
        'u': use_last_item,
        'b': buy_last_item,
        '8': disable_mode,
    }

    do = input("Выбор: ")

    if do in do_list:
        do_list[do]()
    elif do == '':
        from engine import main_menu
        main_menu()
    else:
        menu()


# === ИГРОВЫЕ БОНУСЫ ===

def give_coins(symbols):
    gamer = load_game()
    if gamer is None:
        return 0
    level = gamer['level']
    cf = game_data.cf_coins[level] if level < len(game_data.cf_coins) else game_data.cf_coins[-1]
    coins = symbols / 100
    gamer['coins'] += coins * cf
    save_game(gamer)
    return int(coins * cf)