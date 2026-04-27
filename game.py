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
        exps = symbols * 2 * exp_cf
        self.exp += exps
        self.save()
        coins_cf = self.cf.get('coins', 1.0)
        coins = round((symbols / 100 * coins_cf) * self.calculate_inflation(True), 1)
        self.coins += coins
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
            self.coins += bonus
            msg = (f'🥺 СТРИК ПОТЕРЯН\n'
                   f'Урон за потерю глобального стрика: {damage}❤️\n'
                   f'🔥 Новый стрик начат! Бонус: {bonus} монет')

        # Комбинированный статус для локального стрика (только бонус за старт)
        elif 'Lose' in st and 'Start' in st and streak_type == 'Local':
            bonus = 25 * cf_coins
            self.coins += bonus
            msg = f'Получен бонус {bonus} монет за старт стрика в проекте (после потери).'

        # Обычный старт (без потери)
        elif 'Start' in st and 'Lose' not in st:
            if streak_type == 'Local':
                bonus = round((25 * cf_coins), 2)
                msg = f'Получен бонус {bonus} монет за старт стрика в проекте.'
            else:
                bonus = round((50 * cf_coins), 2)
                msg = f'Получен бонус {bonus} монет за старт глобального стрика.'
            self.coins += bonus

        # Продолжение стрика
        elif 'Go' in st:
            coin_bonus = round((10 * streak_len * cf_coins), 2)
            exp_bonus = round((100 * streak_len * cf_exp))
            if streak_type == 'Local':
                coin_bonus = round((10 * streak_len * cf_coins), 2)
                exp_bonus = round((100 * streak_len * cf_exp))
                msg = f'Получен бонус {coin_bonus} монет и {exp_bonus} оп. за продление стрика в проекте.'
            else:
                coin_bonus = round((25 * streak_len * cf_coins), 2)
                exp_bonus = round((250 * streak_len * cf_exp))
                msg = f'Получен бонус {coin_bonus} монет и {exp_bonus} оп. за продление глобального стрика.'
            self.coins += coin_bonus
            self.exp += exp_bonus

        # Завершение стрика (только локальный)
        elif 'Complete' in st:
            coin_bonus = round((25 * streak_len * cf_coins), 2)
            exp_bonus = round((250 * streak_len * cf_exp))
            msg = (f'СТРИК В ПРОЕКТЕ ЗАВЕРШЕН!'
                   f'\nВы были в цели {streak_len} д. подряд!'
                   f'\nВы получили награду: {coin_bonus} монет и {exp_bonus} опыта!')
            self.coins += coin_bonus
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

        coin_bonus = round((100 * cf_total * cf_coins) * self.calculate_inflation(True), 1)
        exp_bonus = round(1000 * cf_total * cf_exp)

        self.coins += coin_bonus
        self.exp += exp_bonus
        msg = f'Вы получили награду {coin_bonus} монет и {exp_bonus} оп.'

        self.save()
        return msg

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
            'items': {},
            'notifications': {'new': [], 'read': []},
            'bank_account': None,
            'last_lose_global_streak_damage': None,
            'last_bonus_dates': {},
            'inflation': 1,
        }

        for attr, default_value in defaults.items():
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

        # Особая обработка для bank_account
        if self.bank_account is None:
            self.bank_account = game_data.BankAccount()

    def calculate_inflation(self, income=None):
        """Считает адаптивную инфляцию игрока (без ограничений по балансу)"""
        # Защита от логарифма нуля/отрицательных чисел и порог начала инфляции
        if self.coins < 1000:
            self.inflation = 1
        else:
            # math.log10() вернет 3 для 1000, 4 для 10000 и т.д.
            # int() отбрасывает дробную часть, оставляя "ступенчатую" инфляцию
            power_of_ten = int(math.log10(self.coins))

            # Возводим 2 в полученную степень
            self.inflation = 2 ** power_of_ten

        if income is not None:
            return self.inflation / 100 * 75
        else:
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