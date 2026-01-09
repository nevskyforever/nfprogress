import pickle
import game_data
from random import randint
from os import remove

from game_data import cf_exp, cf_coins


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
        if exp >= game_data.levels[level]:
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
        choice = int(input('Введите номер параметра: '))
        gamer[params[choice - 1]] = int(input(f'Введите значение параметра {params[choice - 1]}: '))
        save_game(gamer)
        print(f'Параметр {params[choice - 1]} изменен на {gamer[params[choice - 1]]}.')
        menu()


def menu():
    print('\n ИГРОВОЕ МЕНЮ \n')
    if load_game() is None:
        do = input('МГРОВОЙ РЕЖИМ НЕ АКТИВИРОВАН \n'
              '\n Для активации режима введите 1, для выхода в главное меню - Enter: ')
        if do == '1':
            save_game(game_data.gamer)
            menu()
        if do == '':
            from engine import main_menu
            main_menu()
    else:
        msg = update_gamer()
        if msg is not None:
            print(msg)
        gamer = load_game()
        print(f'Уровень: {gamer['level']}')
        print(f'Здоровье: {gamer['health']}')
        print(f'Монеты: {gamer["coins"]}')
        print(f'Опыт: {gamer['exp']}/{game_data.levels[gamer["level"]]}\n')
        print('1 - О режиме')
        print('2 - Редактор персонажа')
        print('3 - Характеристики персонажа')
        print('off - Выключить режим')
        print(f'Enter - Выйти в главное меню\n')
        print(f'Выберите пункт из меню: ')
        do = input("Выбор: ")
        if do == '1':
            print(game_data.about_mode)
            do = input('Для возврата в игровое меню нажмите Enter')
            if do == '':
                menu()
        if do == '2':
            gamer_editor()
        if do == 'off':
            key = randint(1000, 9999)
            print('Если вы выключите режим, все его данные будут удалены без возможности восстановления \n'
                  'При активации режима вам придется начинать сначала.')
            approve = int(input(f'Подтвердите удаление введя {key}: '))
            if approve == key:
                remove('game_mode.pkl')
                print('\n Игровой режим удален \n')
                from engine import main_menu
                main_menu()
        if do == '3':
            cf_exp = gamer['cf']['exp']
            cf_coins = gamer['cf']['coins']
            print('\n КОЭФФИЦИЕНТЫ ПЕРСОНАЖА \n')
            print(f'Коэффициент умножения опыта: {cf_exp}')
            print(f'Коэффициент умножения монет: {cf_coins}')
            print('\n Коэффициенты умножения дают бонус к зарабатываемым монетам и опыту'
                  '\n Они зависят от уровня, предметов в инвентаре и примененных предметов')
            do = input("Выйти в игровое меню - Enter: ")
            if do == '':
                menu()

        if do == '':
            from engine import main_menu
            main_menu()

def give_coins(symbols):
    gamer = load_game()
    level = gamer['level']
    cf = game_data.cf_coins[level]
    coins = symbols / 100
    gamer['coins'] += coins * cf
    save_game(gamer)
    return coins

def give_exps(symbols):
    gamer = load_game()
    level = gamer['level']
    cf = game_data.cf_coins[level]
    exps = symbols * cf
    gamer['exp'] += exps
    save_game(gamer)
    return exps

def give_streak_bonus():
    gamer = load_game()
    level = gamer['level']
    cf = game_data.cf_coins[level]
    coins = 10 * cf
    gamer['coins'] += coins
    save_game(gamer)
    return coins