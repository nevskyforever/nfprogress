from random import randint
from datetime import datetime

import engine
import game

gamer = {'level': 1,
'health': 100,
'exp': 0,
'coins': 0,
'cf': {'coins': 1.0, 'exp': 1.0},}

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
class Gamer:
    level = 1
    exp = 0
    coins = 0
    cf = None
    notifications = None

    def __init__(self, level=0, exp=0, coins=0, cf={'coins': 1.0, 'exp': 1.0}, notifications={'new': [], 'read': []}):
        self.level = level
        self.exp = exp
        self.coin = coins
        self.cf = cf
        self.notifications = notifications

class Item:
    """Основной класс для создания игровых объектов"""
    def __init__(self, tag, price, level=1, description='У предмета пока нет описания'):
        self.tag = tag
        self.price = price
        self.level = level
        self.description = description
    def buy(self):
        gamer = game.load_game()
        coins = gamer['coins']
        amount = gamer['items'].get(self.tag, 0)
        if coins < self.price:
            return 'Недостаточно монет для покупки'
        else:
            coins -= self.price
            amount += 1
            game.save_game(gamer)
            return 'Предмет куплен'
    def about(self):
        return (f'Стоимость предмета: {self.price}'
                f'Уровень, с которого доступен предмет: {self.level}'
                f'\nОписание предмета: {self.description}')


class FuncItem(Item):
    """Подкласс для объектов с индивидуальными функциями"""
    def __init__(self, tag, price, func=None, add=None, **kwargs):
        super().__init__(tag, price, **kwargs)
        self._func = func        # храним внешнюю функцию

    def use(self, do='use', add=None):           # отдельный метод для вызова
        return self._func(do, add)

# Функции для объектов-функций
def health_add_func(do, price, add):
    gamer = game.load_game()
    if gamer is None:
        return 'Игровой режим не активирован'
    coins = gamer['coins']
    price = 25
    if do == 'use':
        items = gamer['items'].get('health_add', 0)
        if items == 0:
            return 'Зелья восстановления нет в инвентаре'
        else:
            gamer['items']['health_add'] -= 1
            gamer['health'] += add
            if gamer['health'] > 100:
                gamer['health'] = 100
            game.save_game(gamer)
            return '\nПРИМЕНЕНО ЗЕЛЬЕ ВОССТАНОВЛЕНИЯ'

def lottery_ticket_func(do, price, add=None):
    gamer = game.load_game()
    if gamer is None:
        return 'Игровой режим не активирован'
    coins = gamer['coins']
    if do == 'use':
        items = gamer['items'].get('lottery_ticket', 0)
        if items == 0:
            return 'Лотерейного билета нет в инвентаре'
        else:
            print('\n Пусть удача всегда будет с вами! \n')
            gamer['items']['lottery_ticket'] -= 1
            # Генерируем неодинаковые числа
            chance = set()
            win = set()
            while len(chance) != 3 and len(win) != 3:
                chance.add(randint(1, 10))
                win.add(randint(1, 10))
            # Проверяем числа
            cnt = 0
            win_prize = 0
            for i in chance:
                if i in win:
                    cnt += 1
            if cnt == 0:
                return 'В этот раз не повезло :('
            if cnt == 1:
                win_prize = price * 10
                return f'ВЫ ВЫИГРАЛИ {win_prize} МОНЕТ! Совпало 1 число из 3.'
            if cnt == 2:
                win_prize = price * 100
                return f'ВЫ ВЫИГРАЛИ {win_prize} МОНЕТ! Совпало 2 числа из 3.'
            if cnt == 3:
                win_prize = price * 1000
                return f'ВЫ ВЫИГРАЛИ СУПЕРПРИЗ {win_prize} МОНЕТ! Совпало 3 число из 3.'
        gamer['coins'] += win_prize
        game.save_game(gamer)

def freeze_func(do, price, add=None):
    gamer = game.load_game()
    coins = gamer['coins']
    if do == 'use':
        items = gamer['items'].get('freeze', 0)
        if items == 0:
            return 'Заморозок нет в инвентаре'
        else:
            choice = engine.choice_project()
            data = engine.load_data()
            project = data['projects']['active'][choice]
            streaks = project['streaks']
            today = engine.today_for_test()
            if project['deadline'] != "Нет":
                if today not in streaks:
                    streaks.append(today)
                    engine.save_data(data)
                    gamer['items']['freeze'] -= 1
                    game.save_game(gamer)
                    return f'Применена заморозка для {choice}'
                else:
                    return f'Сегодня цель уже выполнена'
            else:
                return 'У этого проекта ннт дедлайна!'
    elif do == '?':
        return 'Заморозка позволяет пропустить один день в стрике'

# Инициализация объектов

freeze = FuncItem(0, func=freeze_func, price=100, level=3,
                  description='Заморозка позволяет пропустить один день стрика в проекте с дедлайном')
lottery_ticket = FuncItem(1, func=lottery_ticket_func, price=10,
                          description='Лотерейный билет позволяет выиграть от 100 до 10К монет')
health_potion_5 = FuncItem(2, func=health_add_func, price=10, add=5,
                           description='Восстанавливает здоровье на 5 единиц')
health_potion_25 = FuncItem(3,func=health_add_func, price=50, add=25,
                            description='Восстанавливает здоровье на 25 единиц')
health_potion_50 = FuncItem(4,func=health_add_func, price=100, add=50,
                            description='Восстанавливает здоровье на 50 единиц')
health_recovery = FuncItem(5,func=health_add_func, price=200, add=100,
                           description='Полностью восстанавливает здоровье')


# Реестр предметов
ITEM_REGISTRY = {'Зелья':
                     {'Малое зелье здоровья': health_potion_5,
                      'Среднее зелье здоровья': health_potion_25,
                      'Большое зелье здоровья': health_potion_50,
                      'Зелье воскрешения': health_recovery,},
                 'Предметы': {'Заморозка': freeze,
                              'Лотерейный билет': lottery_ticket,}}
