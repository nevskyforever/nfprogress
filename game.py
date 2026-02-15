import pickle
from datetime import timedelta
from random import randint, choice
from os import remove
from unicodedata import category

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
    bank_account = None
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

        self.bank_account = game_data.BankAccount()

    # === 3. СЛУЖЕБНЫЕ МЕТОДЫ ===
    def check_integrity(self):
        """Лечит старые сохранения"""
        if self.cf is None: self.cf = {'coins': 1.0, 'exp': 1.0}
        if self.items is None: self.items = {}
        if self.notifications is None: self.notifications = {'new': [], 'read': []}
        if self.bank_account is None: self.bank_account = game_data.BankAccount()

    def save(self):
        with open('game_mode.pkl', 'wb') as f:
            pickle.dump(self, f)
    # === 4. ИГРОВАЯ ЛОГИКА ===
    def give_symbol_bonus(self, symbols):
        exp_cf = self.cf.get('exp', 1.0)
        exps = symbols * 2 * exp_cf
        self.exp += exps
        self.save()
        coins_cf = self.cf.get('coins', 1.0)
        coins = symbols / 100
        self.coins += coins * coins_cf
        self.save()
        return (f'Получено {coins * coins_cf} монет'
                f'\nПолучено {exps} опыта')
    def get_items(self):
        return self.items
    def set_items(self, items):
        self.items = items
    def remove_coins(self, removed):
        self.coins -= removed
    def get_coins(self):
        return self.coins
    def set_coins(self, coins):
        self.coins += coins

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

    def damage(self, damage):
        self.health -= damage
        self.save()
        return (f'Вы потеряли {damage} ед. здоровья'
                f'У вас осталось {self.health} ед. здоровья')

    def reset(self):
        self.__init__()
        self.save()

    def check_loan_penalty(self):
        pass

    def give_streak_bonus(self, status, total_symbols, streak_type):
        # 1. Исправляем ошибку формата из engine.py (склеиваем буквы в слова)
        st = status.split()

        # 2. Берем коэффициент из текущего объекта (self)
        cf_coins = self.cf['coins']
        msg = '👀Бонусы за стрики ждут вас, просто выполните цель на день!'

        # 3. Проверяем вхождение ключевых слов в строку статуса
        if 'Start' in st and 'Lose' not in st:
            bonus = 25 * cf_coins
            self.coins += bonus
            if streak_type == 'Local':
                msg = f'Получен бонус {bonus} монет за старт стрика в проекте.'
            else:
                msg = f'Получен бонус {bonus} монет за старт глобального стрика.'

        elif 'Go' in st:
            bonus = 10 * cf_coins
            self.coins += bonus
            if streak_type == 'Local':
                msg = f'Получен бонус {bonus} монет за продление стрика в проекте.'
            else:
                msg = f'Получен бонус {bonus} монет за продление глобального стрика.'

        elif 'Done' in st:
            if streak_type == 'Local':
                msg = 'Бонус за продление стрика в проекте уже получен.'
            else:
                msg = 'Бонус за продление глобального стрика уже получен.'

        elif 'Complete' in st:
            bonus = 500 * cf_coins
            self.coins += bonus
            msg = f'СТРИК В ПРОЕКТЕ ЗАВЕРШЕН! Вы получили награду: {bonus}!'

        elif 'Lose' in st and streak_type == 'Global':
            # Ищем число дней в статусе для расчета урона
            days = 1
            # Разбиваем строку по пробелам и ищем число
            # Например из "Lose 5" достанем 5
            parts = st
            for part in parts:
                if part.isdigit():
                    days = int(part)
                    break

            damage = days * 5
            self.damage(damage)
            msg = (f'🥺СТРИК ПОТЕРЯН'
                   f'\nВы получили урон за потерю глобального стрика: {damage}❤️')

            # Если потеряли стрик, но сразу начали новый (Lose ... Start)
            if 'Start' in st:
                bonus = 25 * cf_coins
                self.coins += bonus
                msg += (f'НАЧАТ НОВЫЙ СТРИК'
                        f'\nВы получили бонус за начало нового стрика: {bonus}')

        # 4. Сохраняем прогресс и возвращаем сообщение
        self.save()
        return msg


def load_game():
    try:
        with open('game_mode.pkl', 'rb') as f:
            gamer = pickle.load(f)
            gamer.check_integrity()
            return gamer
    except FileNotFoundError:
        return None
