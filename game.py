import os
import pickle
import sys
import math

import engine
import game_data


def get_data_file_path():
    """Возвращает путь к файлу данных игры.

    В режиме разработчика файл хранится в папке test_data.
    """
    return engine.get_data_file_path('gamer')


def resource_path(relative_path):
    """Получить путь к ресурсу, работает и в .py, и в .app, и в .exe"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class Gamer:
    # === 2. ИНИЦИАЛИЗАЦИЯ ===
    def __init__(self, level=1, exp=0, coins=0, health=100):
        self.level = level
        self.exp = exp
        self.coins = coins
        self.inflation = self.calculate_inflation()
        self.health = health

        self.cf = {'coins': 1.0, 'exp': 1.0}
        self.items = {}

        self.bank_account = game_data.BankAccount()
        self.last_lose_global_streak_damage = None
        self.last_bonus_dates = {}

        self.global_streak_len_bonus = 0

    # === 3. СЛУЖЕБНЫЕ МЕТОДЫ ===
    def check_integrity(self):
        """Лечит старые сохранения"""
        self.migrate()  # Просто вызываем migrate вместо ручной проверки

    def save(self):
        data_file = get_data_file_path()
        engine.atomic_pickle_save(self, data_file)

    # === 4. ИГРОВАЯ ЛОГИКА ===
    def give_symbol_bonus(self, symbols):
        exp_cf = self.cf.get('exp', 1.0)
        exps = symbols * 4 * exp_cf
        self.exp += exps
        self.save()
        coins_cf = self.cf.get('coins', 1.0)
        coins = round((symbols / 100 * coins_cf), 1)
        self.set_coins(coins)
        self.save()
        return (f'Получено {coins} монет'
                f'\nПолучено {exps} опыта')

    def give_streak_bonus(self, status, streak_type, streak_len=1):
        st = status.split()
        cf_coins = self.cf['coins']
        cf_exp = self.cf['exp']
        msg = None

        # Комбинированный статус для глобального стрика (урон + бонус)
        if 'Lose' in st and 'Start' in st and streak_type == 'Global':
            today = engine.today_for_test()
            days = int(st[1]) if len(st) > 1 and st[1].isdigit() else 1
            if self.last_lose_global_streak_damage != today:
                damage = days * 5
                self.damage(damage)
                self.last_lose_global_streak_damage = today
            else:
                damage = days * 5  # для отображения
            bonus = round(25 * cf_coins * self.calculate_inflation(True), 1)
            self.set_coins(bonus)
            msg = (f'🥺 СТРИК ПОТЕРЯН\n'
                   f'Урон за потерю глобального стрика: {damage}❤️\n'
                   f'🔥 Новый стрик начат! Бонус: {bonus} монет')

        # Комбинированный статус для локального стрика (только бонус за старт)
        elif 'Lose' in st and 'Start' in st and streak_type == 'Local':
            bonus = round(25 * cf_coins * self.calculate_inflation(True), 1)
            self.set_coins(bonus)
            msg = f'Получен бонус {bonus} монет за старт стрика в проекте (после потери).'

        # Обычный старт (без потери)
        elif 'Start' in st and 'Lose' not in st:
            if streak_type == 'Local':
                bonus = round(25 * cf_coins, 1)
                msg = f'Получен бонус {bonus} монет за старт стрика в проекте.'
            else:
                bonus = round(25 * cf_coins, 1)
                msg = f'Получен бонус {bonus} монет за старт глобального стрика.'
            self.set_coins(bonus)

        # Продолжение стрика
        elif 'Go' in st:
            coin_bonus = round((10 * streak_len * cf_coins), 2)
            exp_bonus = round((100 * streak_len * cf_exp))
            if streak_type == 'Local':
                coin_bonus = round(25 * cf_coins * streak_len * self.calculate_inflation(True), 1)
                exp_bonus = round((100 * streak_len * cf_exp))
                msg = f'Получен бонус {coin_bonus} монет и {exp_bonus} оп. за продление стрика в проекте.'
            else:
                coin_bonus = round(25 * cf_coins * streak_len * self.calculate_inflation(True), 1)
                exp_bonus = round((1000 * streak_len * cf_exp))
                msg = f'Получен бонус {coin_bonus} монет и {exp_bonus} оп. за продление глобального стрика.'
            self.set_coins(coin_bonus)
            self.exp += exp_bonus

        # Завершение стрика (только локальный)
        elif 'Complete' in st:
            coin_bonus = round(50 * cf_coins * streak_len * self.calculate_inflation(True), 1)
            exp_bonus = round((5000 * streak_len * cf_exp))
            msg = (f'СТРИК В ПРОЕКТЕ ЗАВЕРШЕН!'
                   f'\nВы были в цели {streak_len} д. подряд!'
                   f'\nВы получили награду: {coin_bonus} монет и {exp_bonus} опыта!')
            self.set_coins(coin_bonus)
            self.exp += exp_bonus

        # Чистая потеря (только глобальный)
        elif 'Lose' in st and streak_type == 'Global':
            today = engine.today_for_test()
            if self.last_lose_global_streak_damage != today:
                days = 1
                for part in st:
                    if part.isdigit():
                        days = int(part)
                        break
                damage = days * 5
                self.damage(damage)
                self.last_lose_global_streak_damage = today
                msg = (f'🥺 СТРИК ПОТЕРЯН\n'
                       f'Урон за потерю глобального стрика: {damage}❤️')

        self.save()
        return msg

    def give_complete_bonus(self, project_status, project_total):
        cf_total = round(project_total / 1000 + 0.5)  # обычное деление, не целочисленное
        cf_coins = self.cf['coins']
        cf_exp = self.cf['exp']

        coin_bonus = round((100 * cf_total * cf_coins), 1)
        exp_bonus = round(10000 * cf_total * cf_exp)

        self.set_coins(coin_bonus)
        self.exp += exp_bonus
        msg = f'Вы получили награду {coin_bonus} монет и {exp_bonus} оп.'

        self.save()
        return msg

    def give_len_streak_bonus(self, streak_status, streak_len):
        """Выдача бонуса за длительность стрика"""

        cf_coins = self.cf['coins']
        cf_exp = self.cf['exp']
        msg = None

        if streak_len >= 365 and self.global_streak_len_bonus != 365:
            coins_bonus = round((365 * 50 * cf_coins) * self.calculate_inflation(True), 1)
            exp_bonus = round(10000 * 182 * cf_exp)
            self.global_streak_len_bonus = 365
            msg = (f'Вы получили бонус за 365 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 182 and self.global_streak_len_bonus != 182:
            coins_bonus = round((182 * 50 * cf_coins) * self.calculate_inflation(True), 1)
            exp_bonus = round(10000 * 182 * cf_exp)
            self.global_streak_len_bonus = 182
            msg = (f'Вы получили бонус за 182 дня непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 90 and self.global_streak_len_bonus != 90:
            coins_bonus = round((90 * 50 * cf_coins) * self.calculate_inflation(True), 1)
            exp_bonus = round(10000 * 90 * cf_exp)
            self.global_streak_len_bonus = 90
            msg = (f'Вы получили бонус за 90 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 30 and self.global_streak_len_bonus != 30:
            coins_bonus = round((50 * 30 * cf_coins) * self.calculate_inflation(True), 1)
            exp_bonus = round(10000 * 30 * cf_exp)
            self.global_streak_len_bonus = 30
            msg = (f'Вы получили бонус за 90 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 21 and self.global_streak_len_bonus != 21:
            coins_bonus = round((50 * 21 * cf_coins) * self.calculate_inflation(True), 1)
            exp_bonus = round(10000 * 21 * cf_exp)
            self.global_streak_len_bonus = 21
            msg = (f'Вы получили бонус за 21 день непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 14 and self.global_streak_len_bonus != 14:
            coins_bonus = round((50 * 14 * cf_coins) * self.calculate_inflation(True), 1)
            exp_bonus = round(10000 * 14 * cf_exp)
            self.global_streak_len_bonus = 14
            msg = (f'Вы получили бонус за 14 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 7 and self.global_streak_len_bonus != 7:
            coins_bonus = round((50 * 7 * cf_coins) * self.calculate_inflation(True), 1)
            exp_bonus = round(10000 * 7 * cf_exp)
            self.global_streak_len_bonus = 7
            msg = (f'Вы получили бонус за 7 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')

        self.set_coins(coins_bonus)
        self.exp += exp_bonus
        self.save()
        return msg

    def get_items(self):
        return self.items

    def set_items(self, items):
        self.items = items

    def remove_coins(self, removed):
        self.coins -= removed
        self.calculate_inflation()

    def get_coins(self):
        return self.coins

    def set_coins(self, coins):
        self.coins += coins
        self.calculate_inflation()

    def update_cf(self):
        """Обновляет коэффициенты монет и опыта согласно текущему уровню"""
        self.cf['coins'] = game_data.cf_coins[self.level]
        self.cf['exp'] = game_data.cf_exp[self.level]

    def level_up(self):
        data = engine.load_data()
        notifications = data.get('notifications', {'new': [], 'read': []})
        msg = False
        while self.level < len(game_data.levels) - 1 and self.exp >= game_data.levels[self.level]:
            new_level = self.level + 1
            coins_bonus = game_data.lvl_coins_bonus[self.level] * self.calculate_inflation(True)

            self.level = new_level
            self.exp = self.exp - game_data.levels[self.level - 1]
            self.health = 100
            self.coins += coins_bonus

            self.cf['coins'] = game_data.cf_coins[self.level]
            self.cf['exp'] = game_data.cf_exp[self.level]

            msg = f'ПОЛУЧЕН НОВЫЙ {new_level} УРОВЕНЬ! Ваш бонус: {coins_bonus} монет'

        self.save()
        data['notifications'] = notifications
        engine.save_data(data)
        return msg

    def check_health(self):
        if self.health > 0:
            return True

        # Ищем любое зелье в инвентаре по ключевому слову
        has_potion = any('зелье' in k.lower() and v > 0 for k, v in self.items.items())

        if has_potion:
            # Для простоты в критической ситуации даем шанс восстановиться вручную
            return False
        elif self.coins >= 100:
            choice = input('1 - Купить и применить зелье восстановления (100 монет): ')
            if choice == '1':
                self.coins -= 100
                self.health = 100
                self.save()
                return True


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

    def migrate(self):
        """Проверяет наличие всех атрибутов и добавляет недостающие"""
        defaults = {
            'level': 1,
            'exp': 0,
            'coins': 0,
            'health': 100,
            'cf': {'coins': 1.0, 'exp': 1.0},
            'items': {'Предметы': {},'Зелья': {},'Награды': {}},
            'notifications': {'new': [], 'read': []},
            'bank_account': None,
            'last_lose_global_streak_damage': None,
            'last_bonus_dates': {},
            'inflation': 1,
            'global_streak_len_bonus': 0
        }

        for attr, default_value in defaults.items():
            # Проверка флага финансовой реформы
            if not hasattr(self, 'economy_rebalanced_v1'):
                setattr(self, 'economy_rebalanced_v1', False)
            if not hasattr(self, attr):
                setattr(self, attr, default_value)
            elif attr == 'cf' and not isinstance(getattr(self, attr), dict):
                setattr(self, attr, {'coins': 1.0, 'exp': 1.0})
            elif attr == 'items' and not isinstance(getattr(self, attr), dict):
                setattr(self, attr, {})
            elif attr == 'notifications':
                notifications = getattr(self, attr)
                if not isinstance(notifications, dict):
                    setattr(self, attr, {'new': [], 'read': []})
                else:
                    # Убеждаемся, что оба ключа существуют
                    if 'new' not in notifications:
                        notifications['new'] = []
                    if 'read' not in notifications:
                        notifications['read'] = []

        if not self.economy_rebalanced_v1:
            # Считаем, сколько сейчас стоит зелье для игрока
            current_potion_cost = int(200 * self.calculate_inflation())

            # Определяем потолок адекватного богатства (например, стоимость 15 зелий)
            sane_balance_limit = current_potion_cost * 10

            if self.coins > sane_balance_limit:
                # Создаем раздел 'Награды', если его еще нет в инвентаре
                if 'Награды' not in self.items:
                    self.items['Награды'] = {}
                # Если игрок сверхбогат, даем ему памятный предмет ветерана
                self.items['Награды']['👑 Корона Первой Эпохи'] = 1

                # Если у него больше миллиона монет, даем еще один уникальный статус
                if self.coins >= 1000000:
                    self.items['Награды']['💎 Перо Миллионера'] = 1

                # Срезаем баланс до адекватного лимита
                self.coins = sane_balance_limit

            # Отмечаем, что реформа пройдена
            self.economy_rebalanced_v1 = True
            self.save()

        # Задаем структуру инвентаря
        if self.items == {}:
            self.items = {'Предметы': {},'Зелья': {},'Награды': {}}

        # Особая обработка для bank_account
        if self.bank_account is None:
            self.bank_account = game_data.BankAccount()

    def calculate_inflation(self):
        """
        Считает инфляцию цен в зависимости от уровня игрока.
        Например, +15% к базовой цене за каждый уровень после первого.
        Уровень 1: множитель 1.0 (базовые цены)
        Уровень 2: множитель 1.15
        Уровень 10: множитель 2.35
        """
        self.inflation = 1.0 + (self.level - 1) * 0.15
        self.save()
        return self.inflation

def load_game():
    """Загружает данные игрока из кроссплатформенной директории"""
    data_file = get_data_file_path()

    try:
        with open(data_file, 'rb') as f:
            gamer = pickle.load(f)
            gamer.migrate()  # Добавляем вызов migrate здесь
            return gamer
    except (FileNotFoundError, EOFError):
        return Gamer()