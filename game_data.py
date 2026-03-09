from datetime import timedelta
from game_UI import GameMenuController
from random import randint

import engine
import game

about_mode = ('Игровой режим позволяет улучшить мотивацию, сделав из писательства игру.\n'
              '1. При написании текста за каждые 100 символов вы получаете 1 монету, а так же бонус за достигнутый уровень на данный момент\n'
              '2. Монеты можно тратить на предметы, которые улучшают ваш игровой опыт.\n'
              '3. В зависимости от вашего уровня вы можете получить бонус в виде монет и опыта на каждые 100 символов\n'
              'Бонус считается исходя из коэффициентов вашего уровня, их можно посмотреть в отдельном меню.')

levels = [0, 4000, 16000, 36000, 64000, 100000, 144000, 196000, 256000, 324000, 400000, 484000, 576000, 676000, 784000, 900000, 1024000, 1156000, 1296000, 1444000, 1600000, 1764000, 1936000, 2116000, 2304000, 2500000, 2704000, 2916000, 3136000, 3364000, 3600000, 3844000, 4096000, 4356000, 4624000, 4900000, 5184000, 5476000, 5776000, 6084000, 6400000, 6724000, 7056000, 7396000, 7744000, 8100000, 8464000, 8836000, 9216000, 9604000, 10000000]

cf_exp = [0, 1.0, 1.125, 1.25, 1.375, 1.5, 1.625, 1.75, 1.875, 2.0, 2.125, 2.25, 2.375, 2.5, 2.625, 2.75, 2.875, 3.0, 3.125, 3.25, 3.375, 3.5, 3.625, 3.75, 3.875, 4.0, 4.125, 4.25, 4.375, 4.5, 4.625, 4.75, 4.875, 5.0, 5.125, 5.25, 5.375, 5.5, 5.625, 5.75, 5.875, 6.0, 6.125, 6.25, 6.375, 6.5, 6.625, 6.75, 6.875, 7.0, 7.125, 7.25, 7.375, 7.5, 7.625, 7.75, 7.875, 8.0, 8.125, 8.25, 8.375, 8.5, 8.625, 8.75, 8.875, 9.0, 9.125, 9.25, 9.375, 9.5, 9.625, 9.75, 9.875, 10.0, 10.125, 10.25, 10.375, 10.5, 10.625, 10.75, 10.875, 11.0, 11.125, 11.25, 11.375, 11.5, 11.625, 11.75, 11.875, 12.0, 12.125, 12.25, 12.375, 12.5, 12.625, 12.75, 12.875, 13.0, 13.125, 13.25, 13.375, 13.5]

cf_coins = [0, 1.0, 1.0625, 1.125, 1.1875, 1.25, 1.3125, 1.375, 1.4375, 1.5, 1.5625, 1.625, 1.6875, 1.75, 1.8125, 1.875, 1.9375, 2.0, 2.0625, 2.125, 2.1875, 2.25, 2.3125, 2.375, 2.4375, 2.5, 2.5625, 2.625, 2.6875, 2.75, 2.8125, 2.875, 2.9375, 3.0, 3.0625, 3.125, 3.1875, 3.25, 3.3125, 3.375, 3.4375, 3.5, 3.5625, 3.625, 3.6875, 3.75, 3.8125, 3.875, 3.9375, 4.0, 4.0625, 4.125, 4.1875, 4.25, 4.3125, 4.375, 4.4375, 4.5, 4.5625, 4.625, 4.6875, 4.75, 4.8125, 4.875, 4.9375, 5.0, 5.0625, 5.125, 5.1875, 5.25, 5.3125, 5.375, 5.4375, 5.5, 5.5625, 5.625, 5.6875, 5.75, 5.8125, 5.875, 5.9375, 6.0, 6.0625, 6.125, 6.1875, 6.25, 6.3125, 6.375, 6.4375, 6.5, 6.5625, 6.625, 6.6875, 6.75, 6.8125, 6.875, 6.9375, 7.0, 7.0625, 7.125, 7.1875, 7.25]

lvl_coins_bonus = [0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2250, 2500, 2750, 3000, 3250, 3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500, 5750, 6000, 6250, 6500, 6750, 7000, 7250, 7500, 7750, 8000, 8250, 8500, 8750, 9000, 9250, 9500, 9750, 10000, 10250, 10500, 10750, 11000, 11250, 11500, 11750, 12000, 12250, 12500, 12750, 13000, 13250, 13500, 13750, 14000, 14250, 14500, 14750, 15000, 15250, 15500, 15750, 16000, 16250, 16500, 16750, 17000, 17250, 17500, 17750, 18000, 18250, 18500, 18750, 19000, 19250, 19500, 19750, 20000, 20250, 20500, 20750, 21000, 21250, 21500, 21750, 22000, 22250, 22500, 22750, 23000, 23250, 23500, 23750, 24000, 24250, 24500, 24750, 25000]

# Классы объектов

class Item:
    """Основной класс"""

    def __init__(self, name, price, item_type=None, level=1, description='Нет описания'):
        self.name = name
        self.item_type = item_type
        self.price = price
        self.level = level
        self.description = description

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
            # Выполняем функцию предмета
            if self._func:
                # Используем переданный add или сохраненный из конструктора
                use_add = add if add is not None else self.add
                return self._func(do, use_add)
            return "Предмет использован."
        else:
            return "У вас нет этого предмета!"
class Credit:
    def __init__(self, credit_sum, days_until_return, interest_rate_on_loan=2):
        self.take_date = engine.today_for_test()
        self.days_until_return = days_until_return
        self.interest_rate_on_loan = interest_rate_on_loan * (game.load_game().cf['coins'] if game.load_game() else 1.0)
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
        self.interest_rate_on_deposit = interest_rate_on_deposit * game.load_game().cf['coins']
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

    return 'Неизвестное действие'


def lottery_ticket_func(do, add=None):
    """Функция лотерейного билета"""
    print(f"DEBUG: lottery_ticket_func called with do={do}, add={add}")  # Отладка

    gamer = game.load_game()
    price = 10  # Базовая цена билета для расчета выигрыша

    if do == 'use':
        print('DEBUG: Используем лотерейный билет')

        # Генерируем сеты чисел
        chance = set()
        win = set()
        while len(chance) < 3:
            chance.add(randint(1, 10))
        while len(win) < 3:
            win.add(randint(1, 10))

        print(f'DEBUG: Ваши числа: {chance}')
        print(f'DEBUG: Выпавшие числа: {win}')

        # Считаем совпадения
        matches = len(chance.intersection(win))
        print(f'DEBUG: Совпадений: {matches}')

        win_prize = 0
        message = 'В этот раз не повезло :('

        if matches == 1:
            win_prize = price * 5
            message = f'Совпало 1 число! Выигрыш: {win_prize} монет.'
        elif matches == 2:
            win_prize = price * 50
            message = f'Совпало 2 числа!! Выигрыш: {win_prize} монет.'
        elif matches == 3:
            win_prize = price * 1000
            message = f'ДЖЕКПОТ!!! 3 из 3! Выигрыш: {win_prize} монет.'

        print(f'DEBUG: Выигрыш: {win_prize}')

        if win_prize > 0:
            # Сохраняем текущее количество монет для отладки
            old_coins = gamer.coins
            gamer.coins += win_prize
            print(f'DEBUG: Было монет: {old_coins}, стало: {gamer.coins}')
            gamer.save()
            print('DEBUG: Игрок сохранен')
            return f'{message}\n💰 Выигрыш зачислен!'

        return message

    return 'Неизвестное действие'

def freeze_local_func(do, add=None):
    pass

def freeze_global_func(do, add=None):
    if do == 'use':
        # 1. Выбираем проект
        data = engine.load_data()
        gamer = game.load_game()
        items = gamer.get_items()
        streaks = data.get('global_streaks', [])
        today = engine.today_for_test()
        if len(streaks) > 0:
            if today in streaks:
                return 'Сейчас для глобального стрика заморозка не нужна'
            else:
                streaks.append(today)
                items['Предметы']["Глобальная заморозка"] -= 1  # Уменьшаем кол-во
                gamer.set_items(items)  # Обновляем данные в объекте игрока
                engine.save_data(data)
                gamer.save()
                data['global_streak_status'] = 'Freeze'
                engine.save_data(data)
                return f'Глобальный стрик заморожен'
        else:
            return 'Глобальный стрик не начат'

    elif do == '?':
        return 'Заморозка позволяет засчитать день в стрике без написания кода.'

# Инициализация объектов

freeze = FuncItem('Заморозка', price=100, item_type='Предметы', level=3,
                  description='Заморозка позволяет пропустить один день стрика в проекте с дедлайном и активным стриком')
lottery_ticket = FuncItem("Лотерейный билет", price=10, item_type='Предметы', level=2, func=lottery_ticket_func,
                          description='Лотерейный билет позволяет выиграть от 100 до 10К монет')
health_potion_5 = FuncItem('Малое зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=10, add=5,
                           description='Восстанавливает здоровье на 5 единиц')
health_potion_25 = FuncItem('Среднее зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=50, add=25,
                            description='Восстанавливает здоровье на 25 единиц')
health_potion_50 = FuncItem('Большое зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=100, add=50,
                            description='Восстанавливает здоровье на 50 единиц')
health_recovery = FuncItem('Зелье воскрешения', item_type='Зелья', level=3, func=health_potion_func, price=200, add=100,
                           description='Полностью восстанавливает здоровье')


# Реестр предметов
ITEM_REGISTRY = {'Зелья':
                     {'Малое зелье здоровья': health_potion_5,
                      'Среднее зелье здоровья': health_potion_25,
                      'Большое зелье здоровья': health_potion_50,
                      'Зелье воскрешения': health_recovery,},
                 'Предметы': {'Заморозка': freeze,
                              'Лотерейный билет': lottery_ticket,}}
