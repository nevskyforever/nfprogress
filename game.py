import pickle
import game_data
from random import randint
from os import remove

from game_data import cf_exp


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
        exp = gamer['exp']
        if level < len(game_data.levels) - 1 and exp >= game_data.levels[level]:
            new_level = level + 1
            gamer['level'] = new_level
            gamer['exp'] = 0
            gamer['health'] = 100
            coins_bonus = game_data.lvl_coins_bonus[level]
            gamer['coins'] += coins_bonus
            gamer['cf']['coins'] = game_data.cf_coins[level]
            gamer['cf']['exp'] = game_data.cf_exp[level]
            save_game(gamer)
            return f'ПОЛУЧЕН НОВЫЙ {new_level} УРОВЕНЬ! \n Ваш бонус: {coins_bonus} монет \n'
    return None

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
            if params[choice - 1] not in ['cf', 'items']:
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

def menu():
    print('\n ИГРОВОЕ МЕНЮ \n')
    if load_game() is None:
        do = input('ИГРОВОЙ РЕЖИМ НЕ АКТИВИРОВАН \n'
        '\n Для активации режима введите 1, для выхода в главное меню - Enter: ')
        if do == '1':
            gamer = game_data.gamer.copy()
            gamer['items'] = {'health_recovery': 0, 'health_add': 0}
            save_game(gamer)
            menu()
        elif do == '':
            from engine import main_menu
            main_menu()
        else:
            menu()
    else:
        msg = update_gamer()
        if msg is not None:
            print(msg)
        gamer = load_game()
        level = gamer['level']
        max_exp = game_data.levels[level] if level < len(game_data.levels) else game_data.levels[-1]
        print(f'Уровень: {gamer["level"]}')
        print(f'Здоровье: {gamer["health"]}')
        print(f'Монеты: {gamer["coins"]}')
        print(f'Опыт: {gamer["exp"]}/{max_exp}\n')

        print('1 - О режиме')
        print('2 - Редактор персонажа')
        print('3 - Характеристики персонажа')
        print('4 - Инвентарь')
        print('5 - Магазин')
        print('off - Выключить режим')
        print('Enter - Выйти в главное меню\n')

        do = input("Выбор: ")

        if do == '1':
            print(game_data.about_mode)
            do = input('\nДля возврата в игровое меню нажмите Enter')
            if do == '':
                menu()
        elif do == '2':
            gamer_editor()
        elif do == 'off':
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
                    print('ОТМЕНО')
                    menu()
            except ValueError:
                print('НЕПРАВИЛЬНОЕ ЗНАЧЕНИЕ')
                menu()
        elif do == '3':
            gamer = load_game()
            cf_exp = gamer['cf']['exp']
            cf_coins = gamer['cf']['coins']
            print('\n КОЭФФИЦИЕНТЫ ПЕРСОНАЖА \n')
            print(f'Коэффициент умножения опыта: {cf_exp}')
            print(f'Коэффициент умножения монет: {cf_coins}')
            print('\n Коэффициенты умножения дают бонус к зарабатываемым монетам и опыту')
            print('Они зависят от уровня, предметов в инвентаре и примененных предметов')
            do = input("\nВыйти в игровое меню - Enter: ")
            if do == '':
                menu()
        elif do == '4':
            gamer = load_game()
            print('\n ИНВЕНТАРЬ \n')
            print('Для применения предмета введите его номер или Enter для выхода \n')
            print(f'1 - Зелья воскрешения: {gamer["items"].get("health_recovery", 0)}')
            print(f'2 - Зелья восстановления: {gamer["items"].get("health_add", 0)}')
            print(f'3 - Лотерейный билет: {gamer["items"].get("lottery_ticket", 0)}')
            print('Чтобы прочитать информацию о предмете, добавьте к его номеру знак вопроса')
            do = input('\nВыбор: ')
            if do == '1':
                print(game_data.health_recovery('use'))
                menu()
            elif do == '2':
                print(game_data.health_add('use'))
                menu()
            elif do == '3':
                print(game_data.lottery_ticket('use'))
                menu()
            elif do == '1?':
                print(game_data.health_add('?'))
                menu()
            elif do == '2?':
                print(game_data.health_recovery('?'))
                menu()
            elif do == '3?':
                print(game_data.lottery_ticket('?'))
            elif do == '':
                menu()
        elif do == '5':
            print('\n МАНАЗИН \n')
            print('1 - Зелья')
            print('2 - Лотерейный билет (15 монет)')
            print('Чтобы прочитать информацию о предмете, добавьте к его номеру знак вопроса')
            do = input('Выбор: ')
            if do == '1':
                print('1 - Зелье восстановления (+10 здоровья) - 10 монет')
                print('2 - Зелье воскрешения (восстановление здоровья) - 100 монет')
                do = input('Выбор: ')
                if do == '1':
                    print(game_data.health_add('buy'))
                    menu()
                if do == '2':
                    print(game_data.health_recovery('buy'))
                    menu()
                if do == '1?':
                    print(game_data.health_add('?'))
                    menu()
                if do == '2?':
                    print(game_data.health_recovery('?'))
                    menu()
            if do == '2':
                print(game_data.lottery_ticket('buy'))
                menu()
            elif do == '2?':
                print(game_data.lottery_ticket('?'))
        elif do == '':
            from engine import main_menu
            main_menu()
        else:
            menu()

def give_coins(symbols):
    gamer = load_game()
    if gamer is None:
        return 0
    level = gamer['level']
    cf = game_data.cf_coins[level] if level < len(game_data.cf_coins) else game_data.cf_coins[-1]
    coins = int(symbols / 100)
    gamer['coins'] += coins * cf
    save_game(gamer)
    return coins * cf

def give_exps(symbols):
    gamer = load_game()
    if gamer is None:
        return 0
    level = gamer['level']
    cf = game_data.cf_exp[level] if level < len(game_data.cf_exp) else game_data.cf_exp[-1]
    exps = symbols * cf
    gamer['exp'] += exps
    save_game(gamer)
    return exps

def give_streak_bonus(streak_status, total_symbols):
    gamer = load_game()
    if gamer is None:
        return 'Игровой режим не активирован'

    level = gamer['level']
    health = gamer['health']
    cf_coins = game_data.cf_coins[level] if level < len(game_data.cf_coins) else game_data.cf_coins[-1]
    cf_exp = game_data.cf_exp[level] if level < len(game_data.cf_exp) else game_data.cf_exp[-1]
    if streak_status == 'Go':
        coins = int(10 * (cf_coins + 0.5))
        gamer['coins'] += coins
        save_game(gamer)
        return f'Вы продлили стрик и получили {coins} монет! \n Так держать!'

    elif streak_status == 'Done':
        return f'Бонус за стрик сегодня уже получен, но символы лишними не будут ;)'

    elif streak_status == 'Complete':
        exps = int(1000 * (total_symbols / 1000) * (cf_exp + 4))
        coins = int((10 * (cf_coins + 2)) + 100)
        gamer['coins'] += coins
        gamer['exp'] += exps
        save_game(gamer)
        return (f'Вы завершили работу над проектом вовремя и получили дополнительный бонус в {coins} монет и {exps} опыта!'
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
    level = gamer['level']
    cf_coins = game_data.cf_coins[level] if level < len(game_data.cf_coins) else game_data.cf_coins[-1]
    cf_exp = game_data.cf_exp[level] if level < len(game_data.cf_exp) else game_data.cf_exp[-1]
    if gamer is None:
        return 'Игровой режим не активирован'
    else:
        if complete_status is True:
            exps = int(1000 * (total_symbols / 1000) * (cf_exp + 2))
            coins = int((10 * (cf_coins + 1.5)) + 100)
            gamer['coins'] += coins
            gamer['exp'] += exps
            save_game(gamer)
            return (f'Вы завершили работу над проектом и получили бонус в {coins} монет и {exps} опыта!'
                f'\nЭто того стоило!')
    return ''
