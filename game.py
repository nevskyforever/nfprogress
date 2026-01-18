import pickle
from time import strptime

from dateutil.utils import today

import engine
import game_data
from random import randint
from os import remove
from datetime import date


def load_game():
    try:
        with open('game_mode.pkl', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None


def save_game(gamer):
    with open('game_mode.pkl', 'wb') as f:
        pickle.dump(gamer, f)


def update_gamer():
    gamer = load_game()
    if gamer is not None:
        level = gamer['level']
        old_level = level
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

            exp = gamer['exp']  # Обнови exp для следующей итерации
            level = new_level  # Обнови level для проверки условия

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
    # Получение данных
    gamer = load_game()
    gamer_coins = gamer.get('coins', 0)
    if gamer.get('bank', None):
        gamer['bank'] = {'chek': None, 'deposit': {'date': None, 'coins': None, 'income': None}, 'loan': {'date': None, 'coins': None, 'return': None}}
        save_game(gamer)
    deposit_coins = gamer['bank']['deposit']['coins']
    deposit_date = gamer['bank']['deposit']['date']
    loan_coins = gamer['bank']['loan']['coins']
    loan_date = gamer['bank']['loan']['date']
    chek_date = gamer['bank']['chek']
    # Расчет процентов по вкладу, если он старый.
    if chek_date is not None and chek_date > today():
        deposit_income = deposit_coins / 100 * (deposit_date - today()).days
        loan_return = (deposit_coins / 100) * 2 * (deposit_date - today()).days
        gamer['bank']['deposit']['income'] = deposit_income
        gamer['bank']['loan']['return'] = loan_return
        gamer['bank']['chek'] = today()
        save_game(gamer)
    # Вывод данных
    print(f'Ваши наличные монеты: {gamer_coins}')
    if deposit_coins is None:
        print('В банке нет вклада.')
    else:
        print(f'Есть вклад на сумму: {loan_coins} можно снять: {deposit_date}, доход: {deposit_coins - deposit_income} монет')
    if loan_coins is None:
        print('В банке нет кредита.')
    else:
        print(f'Есть кредит на сумму: {loan_coins}, надо вернуть до: {loan_date}, проценты: {loan_coins - loan_return} монет')
    if deposit_coins is None:
        print('1 - Сделать вклад')
    if loan_coins is None:
        print('2 - Взять кредит')
    do = input('Выбор: ')
    # Сделать вклад, если его нет
    if do == '1' and deposit_coins is None:
        print('\nВНЕСЕНИЕ ВКЛАДА\n')
        print('Условия вклада:\n'
              '1. Вклад дает базовый доход в 1% в день\n'
              '2. Срок и сумма вклада не ограничены'
              '3. Вклад можно забрать досрочно, но с потерей дохода (процентов)')
        deposit_coins = int(input('Введите кол-во монет: '))
        if deposit_coins < gamer_coins:
            print('НЕДОСТАТОЧНО ДЕНЕГ ДЛЯ ДЕПОЗИТА')
        else:
            gamer_coins -= deposit_coins
        deposit_date = strptime(input('Введите дату возврата вклада в формате дд.мм.гг: '), '%d.%m.%y')
        gamer['bank']['deposit']['date'] = deposit_date
        gamer['bank']['deposit']['coins'] = deposit_coins
        save_game(gamer)
        print(f'\nСДЕЛАН ВКЛАД В РАЗМЕРЕ {deposit_coins} МОНЕТ ДО {deposit_date}.\n')
        bank()

    # Взять кредит, если его нет

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


def show_inventory():
    gamer = load_game()
    print('\n ИНВЕНТАРЬ \n')
    print('Для применения предмета введите его номер или Enter для выхода \n')

    print(f'1 - Зелья воскрешения: {gamer["items"].get("health_recovery", 0)}')
    print(f'2 - Зелья восстановления: {gamer["items"].get("health_add", 0)}')
    print(f'3 - Лотерейный билет: {gamer["items"].get("lottery_ticket", 0)}')

    print('\nЧтобы прочитать информацию о предмете, добавьте к его номеру знак вопроса')

    do = input('\nВыбор: ')

    if do == '1':
        use_item('health_recovery')
    elif do == '2':
        use_item('health_add')
    elif do == '3':
        use_item('lottery_ticket')
    elif do == '1?':
        print(game_data.health_recovery('?'))
    elif do == '2?':
        print(game_data.health_add('?'))
    elif do == '3?':
        print(game_data.lottery_ticket('?'))
    elif do != '':
        print('Неправильный выбор')

    menu()


def use_item(item_id):
    """Использовать предмет из инвентаря"""
    item_map = {
        'health_recovery': game_data.health_recovery,
        'health_add': game_data.health_add,
        'lottery_ticket': game_data.lottery_ticket,
    }

    if item_id in item_map:
        print(item_map[item_id]('use'))
        gamer = load_game()
        gamer['last_used'] = item_id
        save_game(gamer)


def show_shop():
    print('\n МАГАЗИН \n')
    print('1 - Зелья')
    print('2 - Лотерейный билет (10 монет)')
    print('Чтобы прочитать информацию о предмете, добавьте к его номеру знак вопроса')

    do = input('Выбор: ')

    if do == '1':
        shop_potions()
    elif do == '2':
        buy_item('lottery_ticket', 15)
        menu()
    elif do == '2?':
        print(game_data.lottery_ticket('?'))
        menu()
    elif do != '':
        print('Неправильный выбор')
        menu()
    else:
        menu()


def shop_potions():
    gamer = load_game()
    print('\n ЗЕЛЬЯ \n')
    print('1 - Зелье восстановления (+10 здоровья) - 10 монет')
    print('2 - Зелье воскрешения (восстановление здоровья) - 100 монет')

    do = input('\nВыбор: ')

    if do == '1':
        buy_item('health_add', 10)
    elif do == '2':
        buy_item('health_recovery', 100)
    elif do == '1?':
        print(game_data.health_add('?'))
    elif do == '2?':
        print(game_data.health_recovery('?'))
    elif do != '':
        print('Неправильный выбор')

    menu()


def buy_item(item_id, cost):
    """Купить предмет в магазине"""
    item_map = {
        'health_add': game_data.health_add,
        'health_recovery': game_data.health_recovery,
        'lottery_ticket': game_data.lottery_ticket,
    }

    if item_id in item_map:
        print(item_map[item_id]('buy'))
        gamer = load_game()
        gamer['last_bought'] = item_id
        save_game(gamer)


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
        'lottery_ticket': 15,
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


# === ГЛАВНОЕ МЕНЮ ===

def menu():
    data = engine.load_data()

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

    # Показываем последний использованный предмет
    last_used = gamer.get('last_used', None)
    item_names = {
        'health_recovery': 'Зелья воскрешения',
        'health_add': 'Зелья восстановления',
        'lottery_ticket': 'Лотерейный билет',
    }

    if last_used and last_used in item_names:
        count = gamer['items'].get(last_used, 0)
        print(f'6 - Снова использовать - {item_names[last_used]} ({count})')

    # Показываем последнюю покупку
    last_bought = gamer.get('last_bought', None)
    item_costs = {
        'health_add': 10,
        'health_recovery': 100,
        'lottery_ticket': 15,
    }

    if last_bought and last_bought in item_costs:
        cost = item_costs[last_bought]
        count = gamer['items'].get(last_bought, 0)
        print(f'7 - Купить еще - {item_names.get(last_bought, "Предмет")} ({count}) - {cost} монет')

    print('8 - Выключить режим')
    print('Enter - Выйти в главное меню\n')

    do_list = {
        '1': show_about,
        '2': gamer_editor,
        '3': show_characteristics,
        '4': show_inventory,
        '5': show_shop,
        '6': use_last_item,
        '7': buy_last_item,
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
