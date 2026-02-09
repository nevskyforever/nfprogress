import pickle
from datetime import timedelta
from random import randint
from os import remove

import engine
import game_data


class Gamer:
    # === 1. АТРИБУТЫ КЛАССА (ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ) ===
    level = 1
    exp = 0
    coins = 0
    health = 100

    # Значения "пустышки" для сложных структур
    cf = None
    items = None
    bank = None
    notifications = None

    last_used = None
    last_bought = None

    # === 2. ИНИЦИАЛИЗАЦИЯ (ТОЛЬКО ДЛЯ НОВЫХ ИГР) ===
    def __init__(self, level=1, exp=0, coins=0, health=100):
        self.level = level
        self.exp = exp
        self.coins = coins
        self.health = health

        self.cf = {'coins': 1.0, 'exp': 1.0}
        self.items = {'health_recovery': 0, 'health_add': 0, 'lottery_ticket': 0}
        self.notifications = {'new': [], 'read': []}

        self.bank = {
            'deposit': {'created_date': None, 'withdrawal_date': None, 'coins': 0, 'income': 0},
            'loan': {'created_date': None, 'return_date': None, 'coins': 0, 'return': 0, 'last_penalty_date': None}
        }

        self.last_used = None
        self.last_bought = None

    # === 3. СЛУЖЕБНЫЕ МЕТОДЫ ===
    def check_integrity(self):
        """Лечит старые сохранения"""
        if self.cf is None: self.cf = {'coins': 1.0, 'exp': 1.0}
        if self.items is None: self.items = {'health_recovery': 0, 'health_add': 0, 'lottery_ticket': 0}
        if self.notifications is None: self.notifications = {'new': [], 'read': []}
        if self.bank is None:
            self.bank = {
                'deposit': {'created_date': None, 'withdrawal_date': None, 'coins': 0, 'income': 0},
                'loan': {'created_date': None, 'return_date': None, 'coins': 0, 'return': 0, 'last_penalty_date': None}
            }

    def save(self):
        with open('game_mode.pkl', 'wb') as f:
            pickle.dump(self, f)

    # === 4. ИГРОВАЯ ЛОГИКА ===
    def add_exp(self, symbols):
        current_cf = self.cf.get('exp', 1.0)
        idx = self.level if self.level < len(game_data.cf_exp) else -1
        exps = symbols * 2 * current_cf
        self.exp += exps
        self.save()
        return int(exps)

    def add_coins(self, symbols):
        current_cf = self.cf.get('coins', 1.0)
        coins = symbols / 100
        self.coins += coins * current_cf
        self.save()
        return int(coins * current_cf)

    def level_up(self):
        data = engine.load_data()
        notifications = data.get('notifications', {'new': [], 'read': []})

        while self.level < len(game_data.levels) - 1 and self.exp >= game_data.levels[self.level]:
            new_level = self.level + 1
            coins_bonus = game_data.lvl_coins_bonus[self.level]

            self.level = new_level
            self.exp = self.exp - game_data.levels[self.level - 1]
            self.health = 100
            self.coins += coins_bonus

            self.cf['coins'] = game_data.cf_coins[self.level]
            self.cf['exp'] = game_data.cf_exp[self.level]

            msg = f'ПОЛУЧЕН НОВЫЙ {new_level} УРОВЕНЬ! Ваш бонус: {coins_bonus} монет'
            print(msg)
            notifications['new'].append(msg)

        self.save()
        data['notifications'] = notifications
        engine.save_data(data)

    def check_health(self):
        if self.health > 0:
            return True

        print('КРИТИЧЕСКИЙ УРОВЕНЬ ЗДОРОВЬЯ\n')
        has_potion = self.items.get('health_recovery', 0) > 0

        if has_potion:
            choice = input('1 - Применить зелье восстановления: ')
            if choice == '1':
                print("Зелье использовано!")
                self.items['health_recovery'] -= 1
                self.health = 100
                self.save()
                return True
        elif self.coins >= 100:
            choice = input('1 - Купить и применить зелье восстановления (100 монет): ')
            if choice == '1':
                self.coins -= 100
                print("Зелье куплено и использовано!")
                self.health = 100
                self.save()
                return True

        print('У ВАС НЕТ НИ ЗЕЛЕЙ, НИ МОНЕТ! ИГРОВОЙ ПРОГРЕСС ПОТЕРЯН!')
        self.reset()
        return False

    def reset(self):
        self.__init__()
        self.save()

    def check_loan_penalty(self):
        loan = self.bank['loan']
        if not loan['created_date'] or not loan['return_date']:
            return

        today = engine.today_for_test()

        if today > loan['return_date']:
            last_penalty = loan['last_penalty_date']
            start_date = last_penalty if last_penalty else loan['return_date']
            days_bad = (today - start_date).days

            if days_bad > 0:
                damage = days_bad * 10
                self.health = max(0, self.health - damage)
                msg = f'⚠️ ШТРАФ ЗА КРЕДИТ: -{damage} ❤️ (Осталось: {self.health})'
                print(msg)
                loan['last_penalty_date'] = today
                self.save()

    def give_streak_bonus(self, streak_status, total_symbols):
        idx = self.level if self.level < len(game_data.cf_coins) else -1
        cf_c = game_data.cf_coins[idx]
        idx_e = self.level if self.level < len(game_data.cf_exp) else -1
        cf_e = game_data.cf_exp[idx_e]

        msg = ''
        if streak_status == 'Go':
            coins = int(10 * (cf_c + 0.5))
            self.coins += coins
            msg = f'Вы продлили стрик и получили {coins} монет!'
        elif streak_status == 'Start':
            coins = int(10 * (cf_c + 0.25))
            self.coins += coins
            msg = f'Вы получили {coins} монет за старт стрика!'
        elif streak_status == 'Complete':
            exps = int(1000 * (total_symbols / 1000) * (cf_e + 4))
            coins = int((10 * (cf_c + 2)) + 100)
            self.coins += coins
            self.exp += exps
            msg = f'Проект завершен! Бонус: {coins} монет и {exps} опыта!'
        elif streak_status.startswith('Lose'):
            try:
                days = int(streak_status.split()[1])
                dmg = 5 * days
                self.health = max(0, self.health - dmg)
                msg = f'Стрик потерян. Урон здоровью: -{dmg}'
            except:
                msg = 'Ошибка стрика'

        self.save()
        return msg


# === ФУНКЦИИ-ОБЕРТКИ ===

def load_game():
    try:
        with open('game_mode.pkl', 'rb') as f:
            gamer = pickle.load(f)
            gamer.check_integrity()
            return gamer
    except FileNotFoundError:
        return None


def update_gamer():
    gamer = load_game()
    if gamer:
        gamer.check_loan_penalty()
        gamer.level_up()
        if not gamer.check_health():
            menu()


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
        params = ['level', 'exp', 'coins', 'health']
        for i, p in enumerate(params):
            print(f' {i + 1}. {p}')
        try:
            choice = int(input('Введите номер параметра: '))
            param_name = params[choice - 1]
            new_value = int(input(f'Введите значение {param_name}: '))
            setattr(gamer, param_name, new_value)
            gamer.save()
            print(f'Параметр {param_name} изменен на {new_value}.')
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

    today = engine.today_for_test()
    deposit = gamer.bank['deposit']
    loan = gamer.bank['loan']

    # РАСЧЕТ ПРОЦЕНТОВ (ВКЛАД)
    if deposit['created_date']:
        days = (today - deposit['created_date']).days
        if days > 0:
            deposit['income'] = deposit['coins'] * 0.01 * days

    # РАСЧЕТ ПРОЦЕНТОВ (КРЕДИТ)
    if loan['created_date']:
        days = (today - loan['created_date']).days
        if days > 0:
            if loan['return_date'] and today > loan['return_date']:
                overdue = (today - loan['return_date']).days
                ontime = days - overdue
                loan['return'] = (loan['coins'] * 0.01 * ontime) + (loan['coins'] * 0.02 * overdue)
            else:
                loan['return'] = loan['coins'] * 0.01 * days

    gamer.save()

    print(f'Ваши наличные: {int(gamer.coins)}')

    if not deposit['created_date']:
        print('В банке нет вклада.')
    else:
        print(f'Вклад: {deposit["coins"]} (Доход: {deposit["income"]:.0f})')

    if not loan['created_date']:
        print('В банке нет кредита.')
    else:
        print(f'Кредит: {loan["coins"]} (Проценты: {loan["return"]:.0f})')

    print('\n1 - Вклад, d - Снять вклад')
    print('2 - Кредит, c - Погасить кредит')

    do = input('Выбор (Enter - выход): ').strip()

    # ЛОГИКА ВКЛАДА (Упрощенно)
    if do == '1' and not deposit['created_date']:
        try:
            amount = int(input('Сумма: '))
            if amount <= gamer.coins:
                days = int(input('Дней: '))
                gamer.coins -= amount
                deposit['created_date'] = today
                deposit['withdrawal_date'] = today + timedelta(days=days)
                deposit['coins'] = amount
                gamer.save()
                print('Вклад создан!')
        except ValueError:
            print('Ошибка')

    # ЛОГИКА СНЯТИЯ
    elif do == 'd' and deposit['created_date']:
        total = deposit['coins'] + deposit['income']
        gamer.coins += total
        gamer.bank['deposit'] = {'created_date': None, 'withdrawal_date': None, 'coins': 0, 'income': 0}
        gamer.save()
        print(f'Снято {total:.0f} монет')

    # ЛОГИКА КРЕДИТА
    elif do == '2' and not loan['created_date']:
        try:
            amount = int(input('Сумма: '))
            days = int(input('Дней: '))
            gamer.coins += amount
            loan['created_date'] = today
            loan['return_date'] = today + timedelta(days=days)
            loan['coins'] = amount
            loan['last_penalty_date'] = None
            gamer.save()
            print('Кредит взят!')
        except ValueError:
            pass

    # ЛОГИКА ПОГАШЕНИЯ
    elif do == 'c' and loan['created_date']:
        debt = loan['coins'] + loan['return']
        if gamer.coins >= debt:
            gamer.coins -= debt
            gamer.bank['loan'] = {'created_date': None, 'return_date': None, 'coins': 0, 'return': 0,
                                  'last_penalty_date': None}
            gamer.save()
            print('Кредит погашен!')
        else:
            print('Не хватает денег!')

    if do != '':
        bank()
    else:
        menu()


def show_characteristics():
    gamer = load_game()
    print(f'\nКоэф. опыта: {gamer.cf["exp"]}')
    print(f'Коэф. монет: {gamer.cf["coins"]}')
    input("Enter - назад: ")
    menu()


def shop():
    gamer = load_game()
    print(f'МАГАЗИН (Баланс: {int(gamer.coins)})')

    # Здесь логика показа товаров из game_data.ITEM_REGISTRY
    # Для примера упрощенно:
    registry = game_data.ITEM_REGISTRY
    cats = list(registry.keys())

    for i, c in enumerate(cats, 1): print(f'{i}. {c}')

    try:
        c_choice = int(input('Категория: ')) - 1
        cat_name = cats[c_choice]
        items = list(registry[cat_name].keys())

        for i, item in enumerate(items, 1): print(f'{i}. {item}')

        i_choice = int(input('Товар: ')) - 1
        item_name = items[i_choice]

        # Покупка
        item_obj = registry[cat_name][item_name]
        print(item_obj.buy())  # Метод buy должен быть в game_data

    except (ValueError, IndexError):
        print('Ошибка выбора')

    menu()


def inventory():
    gamer = load_game()
    print(f'ИНВЕНТАРЬ (Баланс: {int(gamer.coins)})')

    if not gamer.items:
        print('Пусто')
    else:
        for k, v in gamer.items.items():
            if v > 0: print(f'{k}: {v} шт.')

    input('Enter - назад')
    menu()


def disable_mode():
    key = randint(1000, 9999)
    print('ВНИМАНИЕ! Удаление прогресса!')
    try:
        if int(input(f'Введите {key} для удаления: ')) == key:
            remove('game_mode.pkl')
            print('Режим удален.')
            engine.main_menu()
    except:
        menu()


def menu():
    gamer = load_game()

    if gamer is None:
        print('РЕЖИМ НЕ АКТИВЕН')
        if input('1 - Активировать, Enter - Выход: ') == '1':
            Gamer().save()
            menu()
        else:
            engine.main_menu()
        return

    update_gamer()
    gamer = load_game()  # Перезагружаем после обновления

    print(f'\n--- ГЕРОЙ: Ур.{gamer.level} | Опыт {int(gamer.exp)}/{game_data.levels[gamer.level]}| ❤️ {gamer.health} | 💰 {int(gamer.coins)}')
    print('1 - Инфо')
    print('2 - Редактор (Dev)')
    print('3 - Характеристики')
    print('4 - Инвентарь')
    print('5 - Магазин')
    print('6 - Банк')
    print('8 - Удалить режим')
    print('Enter - Выход')

    actions = {
        '1': show_about, '2': gamer_editor, '3': show_characteristics,
        '4': inventory, '5': shop, '6': bank, '8': disable_mode
    }

    choice = input('Выбор: ')
    if choice in actions:
        actions[choice]()
    else:
        engine.main_menu()
