from datetime import datetime, timedelta
from random import randint

import engine
import game
about_mode = ('Игровой режим позволяет улучшить мотивацию, сделав из писательства игру.\n'
              '1. При написании текста за каждые 100 символов вы получаете 1 монету, а так же бонус за достигнутый уровень на данный момент\n'
              '2. Монеты можно тратить на предметы, которые улучшают ваш игровой опыт.\n'
              '3. В зависимости от вашего уровня вы можете получить бонус в виде монет и опыта на каждые 100 символов\n'
              'Бонус считается исходя из коэффициентов вашего уровня, их можно посмотреть в отдельном меню.')

# Генераторы параметров для уровней
# Задайте нужное количество уровней (например, n = 51 для уровней 0-50)
n = 100

# 1. Опыт: 4000 * (уровень в квадрате)
levels = [8000 * (i ** 2) for i in range(n)]

# 2. Коэффициент опыта: 0 для нулевого уровня, далее стартует с 1.0 и прибавляет по 0.125
cf_exp = [0 if i == 0 else 1.0 + (i - 1) * 0.125 for i in range(n)]

# 3. Коэффициент монет: 0 для нулевого уровня, далее стартует с 1.0 и прибавляет по 0.0625
cf_coins = [0 if i == 0 else 1.0 + (i - 1) * 0.0625 for i in range(n)]

# 4. Бонус монет: прибавляет по 250 за каждый уровень
lvl_coins_bonus = [i * 250 for i in range(n)]

# Классы объектов

class Buff:
    """Положительный или отрицательный эффект для коэффициента персонажа."""

    POSITIVE = 'positive'
    NEGATIVE = 'negative'

    def __init__(self, name, description, buff_type, target_cf, value, duration_minutes=None,
                 start_time=None, end_time=None, source=None, stackable=False):
        self.name = name
        self.description = description
        self.buff_type = buff_type
        self.target_cf = target_cf
        self.value = value
        self.duration_minutes = duration_minutes
        self.start_time = start_time
        self.end_time = end_time
        self.source = source
        self.stackable = stackable

    def activate(self, start_time=None):
        """Возвращает копию бафа с рассчитанным временем начала и окончания."""
        start_time = start_time or datetime.now()
        end_time = None
        if self.duration_minutes is not None:
            end_time = start_time + timedelta(minutes=self.duration_minutes)

        return Buff(
            name=self.name,
            description=self.description,
            buff_type=self.buff_type,
            target_cf=self.target_cf,
            value=self.value,
            duration_minutes=self.duration_minutes,
            start_time=start_time,
            end_time=end_time,
            source=self.source,
            stackable=self.stackable,
        )

    def is_positive(self):
        return self.buff_type == self.POSITIVE

    def is_negative(self):
        return self.buff_type == self.NEGATIVE

    def is_expired(self, now=None):
        if self.end_time is None:
            return False
        return (now or datetime.now()) >= self.end_time

    def signed_value(self):
        value = abs(self.value)
        return value if self.is_positive() else -value

    def remaining_time(self, now=None):
        if self.end_time is None:
            return None

        remaining = self.end_time - (now or datetime.now())
        if remaining.total_seconds() <= 0:
            return timedelta(0)
        return remaining


class Item:
    """Основной класс"""

    def __init__(self, name, price, item_type=None, level=1, description='Нет описания', buff=None):
        self.name = name
        self.item_type = item_type
        self._price = price
        self.level = level
        self.description = description
        self.buff = buff

    @property
    def price(self):
        # Если в price передана функция, вызываем её. Если число — возвращаем число.
        if callable(self._price):
            return self._price()
        return self._price

    def buy(self):
        gamer = game.load_game()
        coins = gamer.get_coins()
        items = gamer.get_items()

        # Проверяем цену
        if coins < self.price:
            return 'Недостаточно монет!'

        # 1. Списываем деньги
        gamer.remove_coins(self.price)

        # --- ЛОГИКА ДОБАВЛЕНИЯ ---
        # 1. Если такой категории (напр. "Еда") нет в инвентаре — создаем её
        if self.item_type not in items:
            items[self.item_type] = {}

        # 2. Если такого предмета нет в этой категории — создаем запись с 0
        if self.name not in items[self.item_type]:
            items[self.item_type][self.name] = 0

        # 3. Теперь безопасно прибавляем
        items[self.item_type][self.name] += 1

        # 3. Сохраняем
        gamer.set_items(items)
        gamer.save()
        return f'Вы купили: {self.name}'

    def about(self):
        return f'{self.name}: {self.description} (Цена: {self.price})'


class FuncItem(Item):
    """Предмет с функцией (зелья и т.д.)"""

    def __init__(self, name, price, item_type, func=None, add=None, **kwargs):
        # Передаем item_type корректно в родителя
        super().__init__(name, price, item_type=item_type, **kwargs)
        self._func = func
        self.add = add  # Сохраняем add как атрибут

    def use(self, do='use', add=None):
        gamer = game.load_game()
        items = gamer.get_items()

        # Проверяем, есть ли предмет в наличии
        if items[self.item_type][self.name] > 0:
            messages = []

            # Выполняем функцию предмета
            if self._func:
                # Используем переданный add или сохраненный из конструктора
                use_add = add if add is not None else self.add
                messages.append(self._func(do, use_add))

            if do == 'use' and self.buff:
                gamer.add_buff(self.buff)
                messages.append(f"Получен эффект: {self.buff.name}")

            if messages:
                return "\n".join(message for message in messages if message)

            return "Предмет использован."
        else:
            return "У вас нет этого предмета!"
class Credit:
    def __init__(self, credit_sum, days_until_return, interest_rate_on_loan=2):
        self.take_date = engine.today_for_test()
        self.days_until_return = days_until_return
        gamer = game.load_game()
        self.interest_rate_on_loan = interest_rate_on_loan * (gamer.get_cf_value('coins') if gamer else 1.0)
        self.credit_sum = credit_sum
        self.interest = 0

    def get_return_date(self):
        return self.take_date + timedelta(days=self.days_until_return)

    def get_sum(self):
        return self.credit_sum

    def get_status(self):
        today = engine.today_for_test()
        return_date = self.get_return_date()
        if today < return_date:
            return 'OK'
        elif today == return_date:
            return 'Возврат сегодня'
        else:
            return 'Просрочен'

    def get_interest_rate(self):
        return self.interest_rate_on_loan

    def calculate_interest(self):
        today = engine.today_for_test()
        passed_days = (today - self.take_date).days
        rate = self.interest_rate_on_loan

        if self.get_status() == 'Просрочен':
            passed_days *= 2  # Удвоение за просрочку
        self.interest = (self.credit_sum / 100) * (rate * passed_days)
        return self.interest

    def get_interest(self):
        return self.calculate_interest()

    def get_total_sum(self):
        return self.credit_sum + self.get_interest()

    def get_damage(self):
        today = engine.today_for_test()
        return_date = self.get_return_date()
        if today > return_date:
            return (today - return_date).days * 5
        return 0

    def repay(self, gamer):
        """Полное погашение с учётом просрочки"""
        total_sum = self.get_total_sum()

        if gamer.coins < total_sum:
            return f'Недостаточно монет. Нужно: {total_sum}'

        gamer.coins -= total_sum

        # Урон за просрочку
        damage = self.get_damage()
        if damage > 0:
            gamer.health -= damage

        return f'КРЕДИТ ПОГАШЕН\nСумма: {self.credit_sum}, Проценты: {self.interest}, Урон: {damage}'
class Deposit:
    def __init__(self, deposit_sum, days_until_return, interest_rate_on_deposit=1):
        self.give_date = engine.today_for_test()
        self.deposit_sum = deposit_sum
        self.days_until_return = days_until_return
        self.interest_rate_on_deposit = interest_rate_on_deposit * game.load_game().get_cf_value('coins')
        self.interest = 0

    def get_sum(self):
        return self.deposit_sum

    def get_return_date(self):
        return self.give_date + timedelta(days=self.days_until_return)

    def set_interest(self):
        rate = self.interest_rate_on_deposit
        self.interest = (self.deposit_sum / 100) * (self.days_until_return * rate)

    def get_interest(self):
        self.set_interest()
        return self.interest

    def get_status(self):
        today = engine.today_for_test()
        return_date = self.get_return_date()
        if today < return_date:
            status = 'Нельзя снять'
        elif today == return_date or today > return_date:
            status = 'Можно снять'
        return status
    def get_total_sum(self):
        return self.deposit_sum + self.get_interest()
class BankAccount:
    def __init__(self, credit=None, deposit=None):
        self.credit = credit
        self.deposit = deposit
    def set_credit(self, credit):
        self.credit = credit
    def set_deposit(self, deposit):
        self.deposit = deposit
    def get_credit(self):
        return self.credit
    def get_deposit(self):
        return self.deposit

    def return_deposit(self):
        gamer = game.load_game()

        # Считаем итоговую сумму
        total_sum = self.deposit.get_total_sum()

        # ТОЛЬКО ОДНА операция с монетами!
        gamer.coins += total_sum

        # Удаляем депозит
        gamer.bank_account.set_deposit(None)

        # Сохраняем
        gamer.save()

        return (f'\nДЕПОЗИТ СНЯТ\n'
                f'Вы получили {total_sum} монет')

    def return_credit(self):
        gamer = game.load_game()
        if not self.credit:
            return 'Нет кредита'

        result = self.credit.repay(gamer)
        gamer.bank_account.credit = None  # Полное удаление
        gamer.save()
        return result


# Функции для объектов-функций
def health_potion_func(do, add=None):
    """Функция для зелий здоровья"""
    # Загружаем объект игрока
    gamer = game.load_game()

    if do == 'use':
        # Проверка: не лечим, если здоровье уже полное
        if gamer.health >= 100:
            # Возвращаем False или строку, чтобы FuncItem мог понять (опционально)
            # Но так как предмет уже списан в FuncItem.use, просто лечим "в пустоту"
            # или можно восстановить предмет, если здоровье полное (сложная логика).
            # Пока просто восстанавливаем до 100.
            pass

        old_health = gamer.health
        gamer.health += add

        # Ограничиваем максимумом (100)
        if gamer.health > 100:
            gamer.health = 100

        gamer.save()

        healed_amount = gamer.health - old_health
        return f'\nЗдоровье восстановлено на {healed_amount}. Текущее: {gamer.health}'

    if do == '?':
        return 'Восстанавливает здоровье'

    return 'Неизвестное действие'


def lottery_ticket_func(do, add=None):
    """Функция лотерейного билета"""

    gamer = game.load_game()
    price = round(calculate_item_price(10))  # Базовая цена билета

    if do == 'use':
        # Классическая система лотереи "5 из 30"
        chance = set()
        win = set()

        # Генерируем 5 уникальных чисел от 1 до 30 для игрока
        while len(chance) < 5:
            chance.add(randint(1, 30))

        # Генерируем 5 уникальных выигрышных чисел
        while len(win) < 5:
            win.add(randint(1, 30))

        # Считаем совпадения
        matches = len(chance.intersection(win))

        win_prize = 0
        # Показываем игроку, какие числа выпали, чтобы добавить азарта
        message = f'Ваши числа: {sorted(chance)}\nВыигрышные: {sorted(win)}\n\n'

        if matches == 2:
            win_prize = price * 2
            message += f'Совпало 2 числа! Выигрыш: {win_prize} монет.'
        elif matches == 3:
            win_prize = price * 10
            message += f'Совпало 3 числа! Выигрыш: {win_prize} монет.'
        elif matches == 4:
            win_prize = price * 250
            message += f'Отлично! Совпало 4 числа! Выигрыш: {win_prize} монет.'
        elif matches == 5:
            win_prize = price * 10000
            message += f'ДЖЕКПОТ!! Совпало 5 чисел из 5! Выигрыш: {win_prize} монет!'
        else:
            message += f'Совпало чисел: {matches}. В этот раз не повезло :('

        if win_prize > 0:
            gamer.coins += win_prize
            gamer.save()

        return message

    if do == '?':
        return 'Усугубляет лудоманию'

    return 'Неизвестное действие'

def calculate_item_price(price):
    """Считает стоимость предмета для игрока с учетом инфляции"""
    gamer = game.load_game()
    inflation = gamer.inflation

    return round((price * inflation), 1)

def calculate_freeze_price():
    """Считает стоимость заморозки в зависимости от кол-ва использований"""
    projects = engine.load_data()['projects']
    len_global_streak = len(engine.load_data()['global_streaks'])
    global_streak_cf = (len_global_streak / 100) + 1
    used_freezes = 0
    total_price = 250

    for project in projects.values():
        if project.status == 'активен':
            used_freezes += project.freezes
    if not used_freezes:
        used_freezes = 1
    total_price *= used_freezes
    total_price *= global_streak_cf
    return calculate_item_price(total_price)

# Инициализация объектов

freeze = FuncItem('Заморозка', price=calculate_freeze_price, item_type='Предметы', level=3,
                  description='Заморозка позволяет пропустить один день стрика в проекте с дедлайном и активным стриком'
                              '️\n⚠️ Важно: чем больше заморозок вы используете, тем дороже они становятся.'
                              '\nМожно иметь не более 2 заморозок в инвентаре и купить только 1 за раз.')
lottery_ticket = FuncItem("Лотерейный билет", price=lambda: calculate_item_price(10), item_type='Предметы', level=3, func=lottery_ticket_func,
                          description=f'Лотерейный билет "5 из 30". Угадайте числа и сорвите джекпот!')
health_potion_5 = FuncItem('Микро зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(10), add=5,
                           description='Восстанавливает здоровье на 5 единиц')
health_potion_10 = FuncItem('Малое зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(20), add=10,
                           description='Восстанавливает здоровье на 10 единиц')
health_potion_25 = FuncItem('Среднее зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(50), add=25,
                            description='Восстанавливает здоровье на 25 единиц')
health_potion_50 = FuncItem('Большое зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(100), add=50,
                            description='Восстанавливает здоровье на 50 единиц')
health_recovery = FuncItem('Зелье воскрешения', item_type='Зелья', level=3, func=health_potion_func, price=lambda: calculate_item_price(200), add=100,
                           description='Полностью восстанавливает здоровье')
crown_of_the_first_era = Item(name='👑 Корона Первой Эпохи', item_type='Награды', price=0,
                              description='Корона выдается игрокам, которые прошли первую экономическую реформу в игре',
                              buff=Buff(name='Опыт миллионера',
                                        description='+1 к коэффициенту опыта',
                                        buff_type=Buff.POSITIVE,
                                        target_cf='exp',
                                        value=1.0)
                              )
millionaires_pen = Item(name='💎 Перо Миллионера', item_type='Награды', price=0,
                        description='Перо выдается игрокам, которые заработали больше миллиона монет до первой экономической реформы в игре',
                        buff=Buff(name='Удача миллионера',
                                  description='+1 к коэффициенту заработка',
                                  buff_type=Buff.POSITIVE,
                                  target_cf='coins',
                                  value= 1.0))
exp_potion_1hrs = FuncItem(name='Часовое зелье познания',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(100),
                           description='Увеличивает коэффициент опыта на 1 на один час',
                           buff=Buff(name='Бустер опыта',
                                     description='Применено зелье познания',
                                     target_cf='exp',
                                     value=1.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60))
exp_potion_24hrs = FuncItem(name='Суточное зелье опыта',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(2400),
                           description='Увеличивает коэффициент опыта на 1 на один день',
                           buff=Buff(name='Бустер опыта',
                                     description='Применен зелье познания',
                                     target_cf='exp',
                                     value=1.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60*24))
super_exp_potion_1hrs = FuncItem(name='Часовое зелье просвещения',
                           item_type='Зелья',
                           level=8,
                           price=lambda: calculate_item_price(1000),
                           description='Увеличивает коэффициент опыта на 10 на один час',
                           buff=Buff(name='Бустер опыта',
                                     description='Применено зелье познания',
                                     target_cf='exp',
                                     value=10.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60))
super_exp_potion_24hrs = FuncItem(name='Суточное зелье просвещения',
                           item_type='Зелья',
                           level=8,
                           price=lambda: calculate_item_price(24000),
                           description='Увеличивает коэффициент опыта на 10 на один день',
                           buff=Buff(name='Бустер опыта',
                                     description='Применен зелье познания',
                                     target_cf='exp',
                                     value=10.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60*24))

coin_potion_1hrs = FuncItem(name='Часовое зелье доходности',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(200),
                           description='Увеличивает коэффициент монет на 0.5 на один час',
                           buff=Buff(name='Минибустер прибыли',
                                     description='Применено зелье прибыли',
                                     target_cf='coins',
                                     value=0.5,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60))
coin_potion_24hrs = FuncItem(name='Суточное зелье доходности',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(4800),
                           description='Увеличивает коэффициент монет на 0.5 на один день',
                           buff=Buff(name='Минибустер прибыли',
                                     description='Применен зелье прибыли',
                                     target_cf='coins',
                                     value=0.5,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60*24))

# Реестр предметов
ITEM_REGISTRY = {'Зелья':
                     {'Микро зелье здоровья': health_potion_5,
                      'Малое зелье здоровья': health_potion_10,
                      'Среднее зелье здоровья': health_potion_25,
                      'Большое зелье здоровья': health_potion_50,
                      'Зелье воскрешения': health_recovery,
                      'Часовое зелье познания': exp_potion_1hrs,
                      'Суточное зелье познания': exp_potion_24hrs,
                      'Часовое зелье доходности': coin_potion_1hrs,
                      'Суточное зелье доходности': coin_potion_24hrs,
                      'Часовое зелье просвещения': super_exp_potion_1hrs,
                      'Cуточное зелье просвещения': super_exp_potion_24hrs,},
                 'Предметы': {'Заморозка': freeze,
                              'Лотерейный билет': lottery_ticket,},
                 'Награды': {'👑 Корона Первой Эпохи': crown_of_the_first_era,
                             '💎 Перо Миллионера': millionaires_pen,},}
