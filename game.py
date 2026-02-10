import pickle
from datetime import timedelta
from random import randint, choice
from os import remove
from unicodedata import category

import engine
import game_data
from engine import main_menu
from game_data import Deposit, cf_coins


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

    def give_streak_bonus(self, status, total_symbols):
        # 1. Исправляем ошибку формата из engine.py (склеиваем буквы в слова)
        st = status.split()

        # 2. Берем коэффициент из текущего объекта (self)
        cf_coins = self.cf['coins']
        msg = 'Бонус за стрик ждет вас, просто выполните цель на день!'

        # 3. Проверяем вхождение ключевых слов в строку статуса
        if 'Start' in st and 'Lose' not in st:
            bonus = 25 * cf_coins
            self.coins += bonus
            msg = f'СТРИК НАЧАТ! Получено {bonus} монет.'

        elif 'Go' in st:
            bonus = 10 * cf_coins
            self.coins += bonus
            msg = f'СТРИК ПРОДЛЕН! Получено {bonus} монет.'

        elif 'Done' in st:
            msg = 'Бонус за стрик сегодня уже получен, но символы лишними не будут.'

        elif 'Complete' in st:
            bonus = 500 * cf_coins
            self.coins += bonus
            msg = f'СТРИК ЗАВЕРШЕН! Вы получили награду: {bonus}!'

        elif 'Lose' in st:
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
            msg = (f'СТРИК ПОТЕРЯН'
                   f'\nВы получили урон за потерю стрика: {damage}')

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


def update_gamer():
    gamer = load_game()
    if gamer:
        gamer.check_loan_penalty()
        gamer.level_up()
        if not gamer.check_health():
            menu()


# === ФУНКЦИИ МЕНЮ ===

def shop():
    """Магазин"""
    gamer = load_game()
    registry = game_data.ITEM_REGISTRY

    print('\n--- МАГАЗИН ---')
    print(f'Ваш баланс: {gamer.get_coins()} монет')

    # 1. Список категорий
    categories = list(registry.keys())
    for i, cat in enumerate(categories):
        print(f'{i + 1}. {cat}')

    try:
        cat_idx = int(input('Выберите категорию (номер): ')) - 1
        if not (0 <= cat_idx < len(categories)):
            return print("Неверная категория")

        selected_cat_name = categories[cat_idx]  # Например "Зелья"
        items_in_cat = registry[selected_cat_name]  # Словарь предметов
        item_names_list = list(items_in_cat.keys())

        # 2. Список предметов
        print(f'\n--- {selected_cat_name} ---')
        for i, name in enumerate(item_names_list):
            item_obj = items_in_cat[name]
            print(f'{i + 1}. {name} — {item_obj.price} монет')

        item_idx = int(input('Купить предмет (номер): ')) - 1
        if 0 <= item_idx < len(item_names_list):
            name_to_buy = item_names_list[item_idx]
            # Вызываем метод buy() у самого объекта
            result = items_in_cat[name_to_buy].buy()
            print(result)
            menu()
        else:
            print("Неверный номер предмета")
            menu()

    except ValueError:
        print("Нужно вводить цифры!")


def inventory():
    """Инвентарь"""
    gamer = load_game()
    # Получаем словарь {Категория: {Имя: Кол-во}}
    saved_items = gamer.get_items()
    registry = game_data.ITEM_REGISTRY

    print('\n--- ВАШ ИНВЕНТАРЬ ---')

    # Собираем доступные предметы в плоский список для удобного выбора
    available_items = []

    counter = 1
    for cat, items_dict in saved_items.items():
        for name, count in items_dict.items():
            if count > 0:
                print(f'{counter}. {name} (x{count})')
                # Запоминаем ссылку на объект из REGISTRY, чтобы потом вызвать use()
                # Проверяем, существует ли такой предмет в базе данных игры
                if cat in registry and name in registry[cat]:
                    real_object = registry[cat][name]
                    available_items.append(real_object)
                else:
                    available_items.append(None)  # Заглушка, если предмет удален из базы
                counter += 1

    if not available_items:
        print("Пусто.")
        return

    try:
        choice = int(input('\nИспользовать предмет (номер) или 0 для выхода: ')) - 1
        if choice == -1: return

        if 0 <= choice < len(available_items):
            obj = available_items[choice]
            if obj and hasattr(obj, 'use'):
                print(obj.use()) # Используем
            elif obj:
                print(obj.about())  # Просто читаем описание
            else:
                print("Ошибка: предмет есть в сохранении, но удален из кода игры.")
        else:
            print("Неверный номер.")


    except ValueError:
        print("Вводите только цифры.")
    menu()


def bank():
    gamer = load_game()
    bank_account = gamer.bank_account
    deposit = bank_account.get_deposit()
    credit = bank_account.get_credit()
    print('\nБАНК\n')
    print(f'Ваш баланс: {gamer.get_coins()}')
    if credit:
        credit_sum = credit.get_sum()
        credit_status = credit.get_status()
        credit_interest = credit.get_interest()
        print(f'В банке есть кредит на сумму: {credit_sum}, '
              f'нужно вернуть: {credit_sum + credit_interest}, '
              f'статус: {credit_status}')
    else:
        print('В банке нет кредита')
    if deposit:
        deposit_sum = deposit.get_sum()
        deposit_status = deposit.get_status()
        deposit_interest = deposit.get_interest()
        print(f'В банке есть депозит на сумму: {deposit_sum}, '
              f'итог: {deposit_sum + deposit_interest}, '
              f'статус: {deposit_status}')
    else:
        print('В банке нет депозита')
    if deposit is None:
        print('d - сделать депозит')
    if deposit and deposit_status == 'Можно снять':
        print('rd - снять депозит')
    if credit is None:
        print('c - взять кредит')
    print('Вернуться в главное меню - Enter')
    if credit:
        print('rc - вернуть кредит')
    do = input('Выбор: ')
    if do == '':
        menu()
    elif do == 'd':
        cf_coins = gamer.cf['coins']
        print('\nВНЕСЕНИЕ ДЕПОЗИТА\n')
        print(f'Депозит позволяет заработать {1 * cf_coins}% в день от суммы вклада'
              f'\nДепозит можно снять не раньше даты, которую вы выбрали.')
        # Получаем параметки вклада
        sumd = int(input('Введите сумму вклада: '))
        days = int(input('Введите срок влада (кол-во дней): '))
        # Создаем вклад
        deposit = game_data.Deposit(sumd, days)
        # Добавляем вклад в аккаунт
        bank_account.set_deposit(deposit)
        gamer.save()
        print('ДЕПОЗИТ ВНЕСЕН')
        menu()
    elif do == 'rd':
        print(bank_account.return_deposit())
        menu()
    elif do == 'c':
        cf_coins = gamer.cf['coins']
        print('\nВЗЯТИЕ КРЕДИТА\n')
        print(f'Кредит позволяет одолжить деньги у банка'
              f'\nКредит стоит {1 * cf_coins}% в день от суммы'
              f'\nКредит можно погасить в любой момент'
              f'\nПросрочка по кредиту нанесет вам урон в 5 ед. за день и удвоит проценты')
        # Получаем параметки вклада
        sumc = int(input('Введите сумму кредита: '))
        days = int(input('Введите срок кредита (кол-во дней): '))
        # Создаем вклад
        credit = game_data.Credit(sumc, days)
        # Добавляем вклад в аккаунт
        bank_account.set_credit(credit)
        gamer.set_coins(sumc)
        gamer.save()
        print('КРЕДИТ ЗАЧИСЛЕН')
        menu()
    elif do == 'rc':
        print(bank_account.return_credit())
        menu()

    menu()

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

def gamer_editor():
    gamer = load_game()
    print('\nРЕДАКТОР ПЕРСОНАЖА\n')
    print('1 - Монеты')
    print('2 - Опыт')
    print("3 - Здоровье")
    print('4 - Уровень')
    cmd = input('Выберите параметр: ')
    if cmd == '1':
        val = int(input('Введите кол-во монет: '))
        gamer.coins = val
        gamer.save()
    if cmd == '2':
        val = int(input('Введите кол-во опыта: '))
        gamer.exp = val
        gamer.save()
    if cmd == '3':
        val = int(input('Введите здоровье: '))
        gamer.health = val
        gamer.save()
    if cmd == '4':
        val = int(input('Введите уровень: '))
        gamer.level = val
        gamer.save()
    print('Параметр изменен')
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
    credit = gamer.bank_account.get_credit()
    deposit = gamer.bank_account.get_deposit()

    print(
        f'\n--- ГЕРОЙ: Ур.{gamer.level} | Опыт {int(gamer.exp)}/{game_data.levels[gamer.level]} | ❤️ {int(gamer.health)} | 💰 {int(gamer.coins)}')
    print('1 - Инфо - в разработке')
    print('2 - Редактор - в разработке')
    print('3 - Характеристики - в разработке')
    print('4 - Инвентарь')
    print('5 - Магазин')
    if credit and deposit is None:
        credit_status = credit.get_status()
        print(f'6 - Банк (Есть кредит - {credit_status})')
    elif deposit and credit is None:
        deposit_status = deposit.get_status()
        print(f'6 - Банк (Есть депозит - {deposit_status})')
    elif deposit and credit:
        deposit_status = deposit.get_status()
        credit_status = credit.get_status()
        print(f'6 - Банк (Есть депозит - {deposit_status} и кредит - {credit_status})')
    else:
        print('6 - Банк')
    print('8 - Удалить режим')
    print('Enter - Выход')

    cmd = input('Выбор: ')
    actions = {'2': gamer_editor, '4': inventory, '5': shop,'6': bank}

    if cmd in actions:
        actions[cmd]()
    else:
        engine.main_menu()
