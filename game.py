import pickle
from datetime import timedelta
from random import randint
from os import remove

import engine
import game_data

class Gamer:
    # === 1. АТРИБУТЫ КЛАССА ===
    level = 1
    exp = 0
    coins = 0
    health = 100

    cf = None
    items = None
    bank = None
    notifications = None

    # === 2. ИНИЦИАЛИЗАЦИЯ ===
    def __init__(self, level=1, exp=0, coins=0, health=100):
        self.level = level
        self.exp = exp
        self.coins = coins
        self.health = health

        self.cf = {'coins': 1.0, 'exp': 1.0}
        self.items = {}  # Теперь словарь: "Название предмета": количество
        self.notifications = {'new': [], 'read': []}

        self.bank = {
            'deposit': {'created_date': None, 'withdrawal_date': None, 'coins': 0, 'income': 0},
            'loan': {'created_date': None, 'return_date': None, 'coins': 0, 'return': 0, 'last_penalty_date': None}
        }

    # === 3. СЛУЖЕБНЫЕ МЕТОДЫ ===
    def check_integrity(self):
        """Лечит старые сохранения"""
        if self.cf is None: self.cf = {'coins': 1.0, 'exp': 1.0}
        if self.items is None: self.items = {}
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
        # Ищем любое зелье в инвентаре по ключевому слову
        has_potion = any('зелье' in k.lower() and v > 0 for k, v in self.items.items())

        if has_potion:
            print("У вас есть зелья в инвентаре! Зайдите в инвентарь, чтобы использовать.")
            # Для простоты в критической ситуации даем шанс восстановиться вручную
            return False
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
        pass


    def give_streak_bonus(self, streak_status, total_symbols):
       pass

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

def shop():
    pass


def inventory():
    pass


def bank():
    pass


def disable_mode():
    key = randint(1000, 9999)
    if input(f'Введите {key} для удаления режима: ') == str(key):
        try:
            remove('game_mode.pkl')
            print('Режим удален.')
        except:
            pass
        engine.main_menu()
    else:
        menu()


def menu():
    gamer = load_game()
    if gamer is None:
        print('\nИГРОВОЙ РЕЖИМ ОТКЛЮЧЕН')
        if input('1 - Включить, Enter - Назад: ') == '1':
            Gamer().save()
            menu()
        else:
            engine.main_menu()
        return

    update_gamer()
    gamer = load_game()

    print(
        f'\n--- ГЕРОЙ: Ур.{gamer.level} | Опыт {int(gamer.exp)}/{game_data.levels[gamer.level]} | ❤️ {int(gamer.health)} | 💰 {int(gamer.coins)}')
    print('1 - Инфо - в разработке')
    print('2 - Редактор - в разработке')
    print('3 - Характеристики - в разработке')
    print('4 - Инвентарь - в разработке')
    print('5 - Магазин - в разработке')
    print('6 - Банк - в разработке')
    print('8 - Удалить режим')
    print('Enter - Выход')

    cmd = input('Выбор: ')
    actions = {}

    if cmd in actions:
        actions[cmd]()
    else:
        engine.main_menu()
