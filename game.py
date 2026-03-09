import os
import pickle
import platform  # Добавляем импорт platform
import sys
from pathlib import Path

import engine
import game_data

# Определяем систему
SYSTEM = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'


def get_app_data_dir():
    """
    Возвращает путь к директории для хранения данных приложения
    в зависимости от операционной системы.
    """
    if SYSTEM == 'Windows':
        # Windows: C:\Users\<USER>\Documents\MyAppData
        base_dir = Path(os.environ.get('USERPROFILE', '')) / 'Documents'
    elif SYSTEM == 'Darwin':  # macOS
        # macOS: /Users/<USER>/Documents/MyAppData
        base_dir = Path.home() / 'Documents'
    else:  # Linux и другие
        # Linux: /home/<USER>/Documents или ~/.local/share/MyApp
        base_dir = Path.home() / 'Documents'
        # Если папки Documents нет, используем стандартную директорию для данных
        if not base_dir.exists():
            base_dir = Path.home() / '.local' / 'share'

    # Создаем папку для нашего приложения
    app_data_dir = base_dir / 'nfprogress'

    # Создаем директорию, если её нет
    try:
        app_data_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Если нет прав на запись в Documents, используем домашнюю папку
        app_data_dir = Path.home() / '.nfprogress'
        app_data_dir.mkdir(parents=True, exist_ok=True)

    return app_data_dir


def get_data_file_path():
    """Возвращает путь к файлу данных игры"""
    return get_app_data_dir() / 'gamer.pkl'


def resource_path(relative_path):
    """Получить путь к ресурсу, работает и в .py, и в .app, и в .exe"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


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
        """Сохраняет данные игрока в кроссплатформенную директорию"""
        data_file = get_data_file_path()

        # Создаём временную копию для безопасного сохранения
        temp_file = data_file.with_suffix('.tmp')
        with open(temp_file, 'wb') as f:
            pickle.dump(self, f)
        # Заменяем старый файл новым
        temp_file.replace(data_file)

    # === 4. ИГРОВАЯ ЛОГИКА ===
    def give_symbol_bonus(self, symbols):
        exp_cf = self.cf.get('exp', 1.0)
        exps = symbols * 2 * exp_cf
        self.exp += exps
        self.save()
        coins_cf = self.cf.get('coins', 1.0)
        coins = round((symbols / 100 * coins_cf), 1)
        self.coins += coins
        self.save()
        return (f'Получено {coins} монет'
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
        msg = False
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
    """Загружает данные игрока из кроссплатформенной директории"""
    data_file = get_data_file_path()

    with open(data_file, 'rb') as f:
        gamer = pickle.load(f)
        gamer.check_integrity()
        return gamer