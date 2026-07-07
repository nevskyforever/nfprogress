import os
import pickle
import sys
import math
from datetime import datetime, timedelta
import engine
import game_data


CF_META = {
    'coins': {
        'name': 'Монеты',
        'description': 'Коэффициент награды монетами. За 100 символов вы получите {coins_per_100} монет.',
    },
    'exp': {
        'name': 'Опыт',
        'description': 'Коэффициент награды опытом. За 100 символов вы получите {exp_per_100} опыта.',
    },
}


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
        self.coins = self.round_money(coins)
        self.inflation = self.calculate_inflation()
        self.health = health

        self.cf = {
            'coins': self._make_cf_parameter('coins', 1.0),
            'exp': self._make_cf_parameter('exp', 1.0),
        }
        self.items = {}
        self.custom_awards = []
        self.custom_awards_inventory = {}

        self.bank_account = game_data.BankAccount()
        self.last_lose_global_streak_damage = None
        self.last_bonus_dates = {}
        self.buffs = []
        self.debuffs = []

        self.global_streak_len_bonus = 0

    def _make_cf_parameter(self, key, value, base_value=None):
        meta = CF_META.get(key, {})
        if base_value is None:
            base_value = value
        return {
            'value': float(value),
            'base_value': float(base_value),
            'name': meta.get('name', key),
            'description': meta.get('description', ''),
        }

    def normalize_cf(self):
        """Приводит коэффициенты к формату с названием, описанием и значением."""
        if not isinstance(getattr(self, 'cf', None), dict):
            self.cf = {}

        normalized = {}
        for key in CF_META:
            current_value = self.cf.get(key, 1.0)
            if isinstance(current_value, dict):
                value = current_value.get('value', 1.0)
                base_value = current_value.get('base_value', value)
            else:
                value = current_value
                base_value = current_value
            normalized[key] = self._make_cf_parameter(key, value, base_value)
        self.cf = normalized

    def get_cf_value(self, key, default=1.0):
        current_value = self.cf.get(key, default)
        if isinstance(current_value, dict):
            return current_value.get('value', default)
        return current_value

    def set_cf_value(self, key, value):
        self.cf[key] = self._make_cf_parameter(key, value)

    def reset_cf_to_base(self):
        self.normalize_cf()
        for parameter in self.cf.values():
            parameter['value'] = parameter.get('base_value', parameter.get('value', 1.0))

    def _apply_buff_to_cf(self, buff, stacks=1):
        if buff.target_cf not in self.cf:
            return

        parameter = self.cf[buff.target_cf]
        parameter['value'] = max(0, parameter.get('value', 1.0) + buff.signed_value() * stacks)

    def get_timed_buffs(self):
        return list(self.buffs) + list(self.debuffs)

    def get_inventory_buffs(self):
        inventory_buffs = []

        if not isinstance(self.items, dict):
            return inventory_buffs

        for category, items in self.items.items():
            if category not in game_data.ITEM_REGISTRY or not isinstance(items, dict):
                continue

            for item_name, count in items.items():
                if count <= 0:
                    continue

                _, item = game_data.find_registry_item(category, item_name)
                if not item:
                    continue

                buff = getattr(item, 'buff', None)
                if not buff:
                    continue
                if buff.duration_minutes is not None:
                    continue

                item_buff = buff.activate(start_time=None)
                item_buff.start_time = None
                item_buff.end_time = None
                item_buff.source = item.name
                inventory_buffs.append((item_buff, count if item_buff.stackable else 1))

        return inventory_buffs

    def remove_expired_buffs(self, now=None):
        now = now or datetime.now()
        active_buffs = [buff for buff in self.buffs if not buff.is_expired(now)]
        active_debuffs = [buff for buff in self.debuffs if not buff.is_expired(now)]
        changed = len(active_buffs) != len(self.buffs) or len(active_debuffs) != len(self.debuffs)
        self.buffs = active_buffs
        self.debuffs = active_debuffs
        return changed

    def apply_buffs_to_cf(self, save=False):
        changed = self.remove_expired_buffs()
        self.reset_cf_to_base()

        for buff in self.get_timed_buffs():
            self._apply_buff_to_cf(buff)

        for buff, stacks in self.get_inventory_buffs():
            self._apply_buff_to_cf(buff, stacks)

        if save or changed:
            self.save()
        return changed

    def get_all_buffs(self, positive=True, include_inventory=True):
        self.remove_expired_buffs()
        timed = self.buffs if positive else self.debuffs
        result = [(buff, 1) for buff in timed]

        if include_inventory:
            for buff, stacks in self.get_inventory_buffs():
                if buff.is_positive() == positive:
                    result.append((buff, stacks))

        return result

    def add_buff(self, buff):
        active_buff = buff.activate()
        self.remove_expired_buffs()
        target_list = self.buffs if active_buff.is_positive() else self.debuffs

        for existing_buff in target_list:
            if (
                existing_buff.name == active_buff.name
                and existing_buff.target_cf == active_buff.target_cf
                and existing_buff.buff_type == active_buff.buff_type
            ):
                if existing_buff.end_time is None:
                    self.apply_buffs_to_cf(save=True)
                    return existing_buff

                if active_buff.end_time is None:
                    existing_buff.end_time = None
                else:
                    duration_delta = active_buff.end_time - active_buff.start_time
                    existing_buff.end_time = max(datetime.now(), existing_buff.end_time) + duration_delta

                self.apply_buffs_to_cf(save=True)
                return existing_buff

        target_list.append(active_buff)
        self.apply_buffs_to_cf(save=True)
        return active_buff

    def remove_buff(self, buff_name, positive=True):
        target_list = self.buffs if positive else self.debuffs
        initial_len = len(target_list)
        target_list[:] = [buff for buff in target_list if buff.name != buff_name]
        changed = len(target_list) != initial_len
        if changed:
            self.apply_buffs_to_cf(save=True)
        return changed

    def adjust_buff_duration(self, buff_name, minutes, positive=True):
        """Добавляет или отнимает минуты у активного временного бафа."""
        self.remove_expired_buffs()
        target_list = self.buffs if positive else self.debuffs

        for buff in target_list:
            if buff.name != buff_name or buff.end_time is None:
                continue

            buff.end_time += timedelta(minutes=minutes)
            self.apply_buffs_to_cf(save=True)
            return True

        return False

    def get_cf_description(self, key):
        parameter = self.cf.get(key, self._make_cf_parameter(key, 1.0))
        template = parameter.get('description', '')
        coins_per_100 = round(self.get_cf_value('coins', 1.0), 1)
        exp_per_100 = round(100 * 4 * self.get_cf_value('exp', 1.0))
        return template.format(coins_per_100=coins_per_100, exp_per_100=exp_per_100)

    def get_cf_parameters(self):
        self.normalize_cf()
        return [
            {
                'key': key,
                'name': parameter['name'],
                'value': parameter['value'],
                'description': self.get_cf_description(key),
            }
            for key, parameter in self.cf.items()
        ]

    # === 3. СЛУЖЕБНЫЕ МЕТОДЫ ===
    @staticmethod
    def round_money(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0
        return round(math.ceil((value - 1e-9) * 10) / 10, 1)

    def normalize_coins(self):
        self.coins = self.round_money(getattr(self, 'coins', 0))
        return self.coins

    def check_integrity(self):
        """Лечит старые сохранения"""
        self.migrate()  # Просто вызываем migrate вместо ручной проверки

    def save(self):
        self.normalize_coins()
        data_file = get_data_file_path()
        engine.atomic_pickle_save(self, data_file)

    # === 4. ИГРОВАЯ ЛОГИКА ===
    def give_symbol_bonus(self, symbols):
        exp_cf = self.get_cf_value('exp', 1.0)
        exps = symbols * 4 * exp_cf
        self.exp += exps
        self.save()
        coins_cf = self.get_cf_value('coins', 1.0)
        coins = symbols / 100 * coins_cf
        coins = self.set_coins(coins)
        self.save()
        return (f'Получено {coins} монет'
                f'\nПолучено {exps} опыта')

    def give_streak_bonus(self, status, streak_type, streak_len=1):
        st = status.split()
        cf_coins = self.get_cf_value('coins')
        cf_exp = self.get_cf_value('exp')
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
            bonus = self.set_coins(10 * cf_coins * self.calculate_inflation())
            msg = (f'🥺 СТРИК ПОТЕРЯН\n'
                   f'Урон за потерю глобального стрика: {damage}❤️\n'
                   f'🔥 Новый стрик начат! Бонус: {bonus} монет')

        # Комбинированный статус для локального стрика (только бонус за старт)
        elif 'Lose' in st and 'Start' in st and streak_type == 'Local':
            bonus = self.set_coins(10 * cf_coins * self.calculate_inflation())
            msg = f'Получен бонус {bonus} монет за старт стрика в проекте (после потери).'

        # Обычный старт (без потери)
        elif 'Start' in st and 'Lose' not in st:
            if streak_type == 'Local':
                bonus = self.set_coins(50 * cf_coins)
                msg = f'Получен бонус {bonus} монет за старт стрика в проекте.'
            else:
                bonus = self.set_coins(50 * cf_coins)
                msg = f'Получен бонус {bonus} монет за старт глобального стрика.'

        # Продолжение стрика
        elif 'Go' in st:
            if streak_type == 'Local':
                coin_bonus = self.set_coins(10 * cf_coins * streak_len * self.calculate_inflation())
                exp_bonus = round((100 * streak_len * cf_exp))
                msg = f'Получен бонус {coin_bonus} монет и {exp_bonus} оп. за продление стрика в проекте.'
            else:
                coin_bonus = self.set_coins(10 * cf_coins * streak_len * self.calculate_inflation())
                exp_bonus = round((1000 * streak_len * cf_exp))
                msg = f'Получен бонус {coin_bonus} монет и {exp_bonus} оп. за продление глобального стрика.'
            self.exp += exp_bonus

        # Завершение стрика (только локальный)
        elif 'Complete' in st:
            coin_bonus = self.set_coins(25 * cf_coins * streak_len * self.calculate_inflation())
            exp_bonus = round((5000 * streak_len * cf_exp))
            msg = (f'СТРИК В ПРОЕКТЕ ЗАВЕРШЕН!'
                   f'\nВы были в цели {streak_len} д. подряд!'
                   f'\nВы получили награду: {coin_bonus} монет и {exp_bonus} опыта!')
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
        cf_coins = self.get_cf_value('coins')
        cf_exp = self.get_cf_value('exp')

        coin_bonus = self.set_coins(100 * cf_total * cf_coins)
        exp_bonus = round(10000 * cf_total * cf_exp)

        self.exp += exp_bonus
        msg = f'Вы получили награду {coin_bonus} монет и {exp_bonus} оп.'

        self.save()
        return msg

    def give_len_streak_bonus(self, streak_status, streak_len):
        """Выдача бонуса за длительность стрика"""

        cf_coins = self.get_cf_value('coins')
        cf_exp = self.get_cf_value('exp')
        msg = None

        if streak_len >= 365 and self.global_streak_len_bonus != 365:
            coins_bonus = self.set_coins((365 * 25 * cf_coins) * self.calculate_inflation())
            exp_bonus = round(10000 * 182 * cf_exp)
            self.global_streak_len_bonus = 365
            msg = (f'Вы получили бонус за 365 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 182 and self.global_streak_len_bonus != 182:
            coins_bonus = self.set_coins((182 * 25 * cf_coins) * self.calculate_inflation())
            exp_bonus = round(10000 * 182 * cf_exp)
            self.global_streak_len_bonus = 182
            msg = (f'Вы получили бонус за 182 дня непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 90 and self.global_streak_len_bonus != 90:
            coins_bonus = self.set_coins((90 * 25 * cf_coins) * self.calculate_inflation())
            exp_bonus = round(10000 * 25 * cf_exp)
            self.global_streak_len_bonus = 90
            msg = (f'Вы получили бонус за 90 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 30 and self.global_streak_len_bonus != 30:
            coins_bonus = self.set_coins((50 * 15 * cf_coins) * self.calculate_inflation())
            exp_bonus = round(10000 * 15 * cf_exp)
            self.global_streak_len_bonus = 30
            msg = (f'Вы получили бонус за 90 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 21 and self.global_streak_len_bonus != 21:
            coins_bonus = self.set_coins((10 * 21 * cf_coins) * self.calculate_inflation())
            exp_bonus = round(10000 * 21 * cf_exp)
            self.global_streak_len_bonus = 21
            msg = (f'Вы получили бонус за 21 день непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 14 and self.global_streak_len_bonus != 14:
            coins_bonus = self.set_coins((10 * 14 * cf_coins) * self.calculate_inflation())
            exp_bonus = round(10000 * 14 * cf_exp)
            self.global_streak_len_bonus = 14
            msg = (f'Вы получили бонус за 14 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')
        elif streak_len >= 7 and self.global_streak_len_bonus != 7:
            coins_bonus = self.set_coins((50 * 7 * cf_coins) * self.calculate_inflation())
            exp_bonus = round(10000 * 7 * cf_exp)
            self.global_streak_len_bonus = 7
            msg = (f'Вы получили бонус за 7 дней непрерывного стрика!'
                   f'\nВаш бонус: {coins_bonus} м. и {exp_bonus} оп.')

        if msg:
            self.exp += exp_bonus
        self.save()
        return msg

    def get_items(self):
        return self.items

    def set_items(self, items):
        self.items = items

    def remove_coins(self, removed, process_bank_events=True, save=True):
        removed = self.round_money(removed)
        self.coins = self.round_money(self.coins - removed)
        self.calculate_inflation()
        if process_bank_events:
            self.process_bank_events(save=False)
        if save:
            self.save()
        return removed

    def get_coins(self):
        return self.normalize_coins()

    def set_coins(self, coins, process_bank_events=True, save=True):
        coins = self.round_money(coins)
        self.coins = self.round_money(self.coins + coins)
        self.calculate_inflation()
        if process_bank_events:
            self.process_bank_events(save=False)
        if save:
            self.save()
        return coins

    def process_bank_events(self, save=True):
        bank_account = getattr(self, 'bank_account', None)
        if not bank_account:
            return []
        messages = bank_account.process_daily_events(self, auto_pay=True, notify=True, save=False)
        if messages and save:
            self.save()
        return messages

    def update_cf(self):
        """Обновляет коэффициенты монет и опыта согласно текущему уровню"""
        self.set_cf_value('coins', game_data.cf_coins[self.level])
        self.set_cf_value('exp', game_data.cf_exp[self.level])

    def level_up(self):
        data = engine.load_data()
        notifications = data.get('notifications', {'new': [], 'read': []})
        msg = False
        while self.level < len(game_data.levels) - 1 and self.exp >= game_data.levels[self.level]:
            new_level = self.level + 1
            coins_bonus = game_data.lvl_coins_bonus[self.level] * self.calculate_inflation()

            self.level = new_level
            self.exp = self.exp - game_data.levels[self.level - 1]
            self.health = 100
            coins_bonus = self.set_coins(coins_bonus, process_bank_events=False, save=False)

            self.set_cf_value('coins', game_data.cf_coins[self.level])
            self.set_cf_value('exp', game_data.cf_exp[self.level])

            msg = f'ПОЛУЧЕН НОВЫЙ {new_level} УРОВЕНЬ! Ваш бонус: {coins_bonus} монет'

        self.save()
        data['notifications'] = notifications
        engine.save_data(data)
        return msg

    def check_health(self):
        if self.health > 0:
            return True

        # Ищем любое зелье в инвентаре по категории и названию предмета.
        has_potion = any(
            count > 0 and 'зелье' in str(item_name).casefold()
            for item_name, count in self.items.get('Зелья', {}).items()
        )

        if has_potion:
            # Для простоты в критической ситуации даем шанс восстановиться вручную
            return False
        elif self.get_coins() >= 100:
            choice = input('1 - Купить и применить зелье восстановления (100 монет): ')
            if choice == '1':
                self.remove_coins(100, process_bank_events=False, save=False)
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

    def migrate_legacy_award_names(self):
        """Переносит старые ключи наград с эмодзи на ключи без эмодзи."""
        if not isinstance(self.items, dict):
            return False

        awards = self.items.setdefault('Награды', {})
        if not isinstance(awards, dict):
            self.items['Награды'] = {}
            return True

        legacy_awards = {
            '👑 Корона Первой Эпохи': 'Корона Первой Эпохи',
            '💎 Перо Миллионера': 'Перо Миллионера',
        }

        changed = False
        for old_name, new_name in legacy_awards.items():
            old_count = awards.pop(old_name, 0)
            if old_count > 0:
                awards[new_name] = awards.get(new_name, 0) + old_count
                changed = True

        return changed

    def migrate(self):
        """Проверяет наличие всех атрибутов и добавляет недостающие"""
        defaults = {
            'level': 1,
            'exp': 0,
            'coins': 0,
            'health': 100,
            'cf': {
                'coins': self._make_cf_parameter('coins', 1.0),
                'exp': self._make_cf_parameter('exp', 1.0),
            },
            'items': {'Предметы': {},'Зелья': {},'Награды': {}},
            'custom_awards': [],
            'custom_awards_inventory': {},
            'notifications': {'new': [], 'read': []},
            'bank_account': None,
            'last_lose_global_streak_damage': None,
            'last_bonus_dates': {},
            'inflation': 1,
            'global_streak_len_bonus': 0,
            'buffs': [],
            'debuffs': [],
        }

        for attr, default_value in defaults.items():
            # Проверка флага финансовой реформы
            if not hasattr(self, 'economy_rebalanced_v1'):
                setattr(self, 'economy_rebalanced_v1', False)
            if not hasattr(self, attr):
                setattr(self, attr, default_value)
            elif attr == 'cf' and not isinstance(getattr(self, attr), dict):
                setattr(self, attr, {
                    'coins': self._make_cf_parameter('coins', 1.0),
                    'exp': self._make_cf_parameter('exp', 1.0),
                })
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
            elif attr in ('buffs', 'debuffs') and not isinstance(getattr(self, attr), list):
                setattr(self, attr, [])

        if not self.economy_rebalanced_v1:
            # Считаем, сколько сейчас стоит зелье для игрока
            current_potion_cost = int(200 * self.calculate_inflation())

            # Определяем потолок адекватного богатства (например, стоимость 15 зелий)
            sane_balance_limit = current_potion_cost * 10

            if self.get_coins() > sane_balance_limit:
                # Создаем раздел 'Награды', если его еще нет в инвентаре
                if 'Награды' not in self.items:
                    self.items['Награды'] = {}
                # Если игрок сверхбогат, даем ему памятный предмет ветерана
                self.items['Награды']['👑 Корона Первой Эпохи'] = 1

                # Если у него больше миллиона монет, даем еще один уникальный статус
                if self.get_coins() >= 1000000:
                    self.items['Награды']['💎 Перо Миллионера'] = 1

                # Срезаем баланс до адекватного лимита
                self.coins = self.round_money(sane_balance_limit)

            # Отмечаем, что реформа пройдена
            self.economy_rebalanced_v1 = True
            self.save()

        # Задаем структуру инвентаря
        if self.items == {}:
            self.items = {'Предметы': {},'Зелья': {},'Награды': {}}
        migrated_awards = self.migrate_legacy_award_names()
        self.normalize_coins()

        # Особая обработка для bank_account
        self.normalize_cf()
        self.apply_buffs_to_cf()
        if self.bank_account is None:
            self.bank_account = game_data.BankAccount()
        else:
            self.bank_account.normalize()

        if migrated_awards:
            self.save()

    def calculate_inflation(self):
        """
        Считает инфляцию цен в зависимости от уровня игрока.
        Например, +15% к базовой цене за каждый уровень после первого.
        Уровень 1: множитель 1.0 (базовые цены)
        Уровень 2: множитель 1.15
        Уровень 10: множитель 2.35
        """
        self.inflation = 1.0 + (self.level - 1) * 0.15
        return self.inflation

def load_game():
    """Загружает данные игрока из кроссплатформенной директории"""
    data_file = get_data_file_path()

    try:
        # 1. Открываем и считываем файл.
        # Как только этот блок завершается, Python автоматически закрывает файл.
        with open(data_file, 'rb') as f:
            gamer = pickle.load(f)
    except (FileNotFoundError, EOFError):
        # Если файла нет или он пуст, создаем нового игрока
        return Gamer()

    # 2. Файл гарантированно закрыт, блокировка Windows снята.
    # Теперь вызов migrate() и все внутренние вызовы save() отработают без ошибок.
    gamer.migrate()
    return gamer
