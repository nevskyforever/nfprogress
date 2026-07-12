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

    def __init__(self, name, price, item_type=None, level=1, description='Нет описания', buff=None, credit_allowed=True):
        self.name = name
        self.item_type = item_type
        self._price = price
        self.level = level
        self.description = description
        self.buff = buff
        self.credit_allowed = credit_allowed

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
        self.interest_rate_on_loan = interest_rate_on_loan
        self.credit_sum = credit_sum
        self.interest = 0
        self.paid_amount = 0
        self.accrued_penalty = 0
        self.last_payment_date = None
        self.last_penalty_date = None
        self.total_overdue_days = 0
        self.last_daily_check_date = None
        self.last_payment_notice_date = None

    def normalize(self):
        if not hasattr(self, 'paid_amount'):
            self.paid_amount = 0
        if not hasattr(self, 'accrued_penalty'):
            self.accrued_penalty = 0
        if not hasattr(self, 'last_payment_date'):
            self.last_payment_date = None
        if not hasattr(self, 'last_penalty_date'):
            self.last_penalty_date = None
        if not hasattr(self, 'total_overdue_days'):
            self.total_overdue_days = 0
        if not hasattr(self, 'last_daily_check_date'):
            self.last_daily_check_date = None
        if not hasattr(self, 'last_payment_notice_date'):
            self.last_payment_notice_date = None
        return self

    def get_return_date(self):
        return self.take_date + timedelta(days=self.days_until_return)

    def get_first_payment_date(self):
        return self.take_date + timedelta(days=1)

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

    def get_base_daily_payment(self):
        self.normalize()
        days = max(1, self.days_until_return)
        daily_rate = self.interest_rate_on_loan / 100
        if daily_rate <= 0:
            return round(self.credit_sum / days, 1)
        growth = (1 + daily_rate) ** days
        payment = self.credit_sum * daily_rate * growth / (growth - 1)
        return round(payment, 1)

    def calculate_interest(self):
        self.normalize()
        total_without_penalty = self.get_base_daily_payment() * max(1, self.days_until_return)
        self.interest = max(0, round(total_without_penalty - self.credit_sum, 1))
        return self.interest

    def get_interest(self):
        return self.calculate_interest()

    def get_total_sum(self):
        self.normalize()
        return round(self.credit_sum + self.get_interest() + self.accrued_penalty, 1)

    def get_remaining_sum(self):
        self.normalize()
        return max(0, round(self.get_total_sum() - self.paid_amount, 1))

    def get_full_repayment_sum(self):
        return self.get_remaining_sum()

    def get_daily_payment(self):
        self.normalize()
        return round(min(self.get_remaining_sum(), self.get_base_daily_payment()), 1)

    def get_damage(self):
        today = engine.today_for_test()
        return_date = self.get_return_date()
        if today > return_date:
            return (today - return_date).days * 10
        return 0

    def repay(self, gamer):
        """Полное погашение с учётом уже внесенных платежей."""
        self.normalize()
        total_sum = self.get_remaining_sum()

        if gamer.get_coins() < total_sum:
            return f'Недостаточно монет. Нужно: {total_sum}'

        gamer.remove_coins(total_sum, process_bank_events=False, save=False)
        self.paid_amount = self.get_total_sum()

        return f'КРЕДИТ ПОГАШЕН\nСумма: {self.credit_sum}, проценты: {self.get_interest()}, штрафы: {round(self.accrued_penalty, 1)}'


class Deposit:
    def __init__(self, deposit_sum, days_until_return, interest_rate_on_deposit=1):
        self.give_date = engine.today_for_test()
        self.deposit_sum = deposit_sum
        self.days_until_return = days_until_return
        self.interest_rate_on_deposit = interest_rate_on_deposit
        self.interest = 0
        self.withdrawn_interest = 0
        self.interest_withdrawals = []
        self.topups = []
        self.last_interest_withdraw_date = None
        self.last_interest_notice_date = None

    def normalize(self):
        if not hasattr(self, 'withdrawn_interest'):
            self.withdrawn_interest = 0
        if not hasattr(self, 'interest_withdrawals'):
            self.interest_withdrawals = []
            if self.withdrawn_interest > 0:
                withdrawal_date = getattr(self, 'last_interest_withdraw_date', None) or self.give_date
                self.interest_withdrawals.append({
                    'date': withdrawal_date,
                    'amount': self.withdrawn_interest,
                })
        if not hasattr(self, 'topups'):
            self.topups = []
        if not hasattr(self, 'last_interest_withdraw_date'):
            self.last_interest_withdraw_date = None
        if not hasattr(self, 'last_interest_notice_date'):
            self.last_interest_notice_date = None
        return self

    def get_sum(self):
        return self.deposit_sum

    def get_return_date(self):
        return self.give_date + timedelta(days=self.days_until_return)

    def _remaining_interest_after_withdrawals(self, days):
        self.normalize()
        days = max(0, int(days))
        daily_rate = self.interest_rate_on_deposit / 100
        topups_total = sum(topup.get('amount', 0) for topup in self.topups)
        initial_principal = max(0, round(self.deposit_sum - topups_total, 1))
        balance = float(initial_principal)
        principal_floor = float(initial_principal)
        topups_by_day = {}
        for topup in self.topups:
            topup_date = topup.get('date')
            if not topup_date:
                continue
            topup_day = max(1, (topup_date - self.give_date).days + 1)
            if topup_day <= days:
                topups_by_day[topup_day] = topups_by_day.get(topup_day, 0) + topup.get('amount', 0)
        withdrawals_by_day = {}
        for withdrawal in self.interest_withdrawals:
            withdrawal_date = withdrawal.get('date')
            if not withdrawal_date:
                continue
            withdrawal_day = max(0, min((withdrawal_date - self.give_date).days, days))
            withdrawals_by_day[withdrawal_day] = withdrawals_by_day.get(withdrawal_day, 0) + withdrawal.get('amount', 0)

        for day in range(1, days + 1):
            if day in topups_by_day:
                balance += topups_by_day[day]
                principal_floor += topups_by_day[day]
            balance += balance * daily_rate
            if day in withdrawals_by_day:
                balance = max(principal_floor, balance - withdrawals_by_day[day])
        return max(0, round(balance - principal_floor, 1))

    def top_up(self, amount):
        self.normalize()
        amount = round(float(amount), 1)
        self.deposit_sum = round(self.deposit_sum + amount, 1)
        self.topups.append({'date': engine.today_for_test(), 'amount': amount})
        return amount

    def set_interest(self):
        self.normalize()
        self.interest = self._remaining_interest_after_withdrawals(self.days_until_return)

    def get_interest(self):
        self.set_interest()
        return self.interest

    def get_status(self):
        today = engine.today_for_test()
        return_date = self.get_return_date()
        if today < return_date:
            status = 'Можно снять досрочно с потерей процентов'
        elif today == return_date or today > return_date:
            status = 'Можно снять'
        return status

    def get_total_sum(self):
        return round(self.deposit_sum + self.get_interest(), 1)

    def get_available_interest(self):
        self.normalize()
        today = engine.today_for_test()
        passed_days = max(0, min((today - self.give_date).days, self.days_until_return))
        return self._remaining_interest_after_withdrawals(passed_days)


class BankAccount:
    def __init__(self, credit=None, deposit=None):
        self.credit = credit
        self.deposit = deposit
        self.credit_score = 600
        self.credit_history = []
        self.deposit_history = []
        self.overdue_days_total = 0

    def normalize(self):
        if not hasattr(self, 'credit_score'):
            self.credit_score = 600
        if not hasattr(self, 'credit_history'):
            self.credit_history = []
        if not hasattr(self, 'deposit_history'):
            self.deposit_history = []
        if not hasattr(self, 'overdue_days_total'):
            self.overdue_days_total = 0
        if self.credit and hasattr(self.credit, 'normalize'):
            self.credit.normalize()
        if self.deposit and hasattr(self.deposit, 'normalize'):
            self.deposit.normalize()
        return self

    def set_credit(self, credit):
        self.normalize()
        self.credit = credit

    def set_deposit(self, deposit):
        self.normalize()
        self.deposit = deposit

    def get_credit(self):
        self.normalize()
        return self.credit

    def get_deposit(self):
        self.normalize()
        return self.deposit

    def _attach_to_gamer(self, gamer):
        if gamer is not None:
            gamer.bank_account = self

    def _inventory_value(self, gamer):
        total = 0
        items = getattr(gamer, 'items', {})
        if not isinstance(items, dict):
            return total
        custom_award_names = {
            award.name
            for award in getattr(gamer, 'custom_awards', [])
            if hasattr(award, 'name')
        }

        for category, category_items in items.items():
            if not isinstance(category_items, dict):
                continue
            for item_name, count in category_items.items():
                if count <= 0:
                    continue
                _, item = find_registry_item(category, item_name)
                if not item:
                    continue
                if category == 'Награды' and item_name in custom_award_names:
                    continue
                total += item.price * count
        return round(total, 1)

    def estimate_daily_income(self, gamer):
        details = self.estimate_daily_income_details(gamer)
        return details['total']

    def _deposit_value_for_bank_scoring(self):
        self.normalize()
        active_deposit = self.deposit.get_sum() if self.deposit else 0
        historical_principal = sum(item.get('sum', 0) for item in self.deposit_history)
        historical_interest = sum(item.get('interest', 0) for item in self.deposit_history)
        return round(active_deposit + historical_principal * 0.35 + historical_interest * 2, 1)

    def get_level_reliability_label(self, gamer):
        level = getattr(gamer, 'level', 1)
        if level >= 50:
            return 'идеальная'
        if level >= 30:
            return 'прекрасная'
        if level >= 20:
            return 'отличная'
        if level >= 10:
            return 'хорошая'
        if level >= 5:
            return 'средняя'
        return 'начальная'

    def _iter_loaded_projects(self):
        data = engine.load_data()
        projects = data.get('projects', [])
        if isinstance(projects, dict):
            return list(projects.values())
        return list(projects)

    def _estimate_streak_income(self, gamer):
        coins_cf = max(0.1, gamer.get_cf_value('coins', 1.0))
        inflation = gamer.calculate_inflation()
        data = engine.load_data()
        settings = engine.load_settings()
        streak_candidates = []

        if settings.get('global_streak', False):
            global_streak_len = engine.streak_length(data.get('global_streaks', []))
            if global_streak_len > 0:
                streak_candidates.append(10 * coins_cf * global_streak_len * inflation)

        for project in self._iter_loaded_projects():
            streaks = getattr(project, 'streaks', [])
            streak_len = engine.streak_length(streaks)
            if streak_len > 0:
                streak_candidates.append(10 * coins_cf * streak_len * inflation)

        if streak_candidates:
            return gamer.round_money(max(streak_candidates))
        return gamer.round_money(10 * coins_cf * inflation)

    def _estimate_daily_writing_symbols(self):
        symbol_candidates = []
        for project in self._iter_loaded_projects():
            if getattr(project, 'status', 'активен') != 'активен':
                continue
            try:
                today_goal = project.get_today_goal_value()
            except Exception:
                today_goal = getattr(project, 'personal_goal_for_the_day', 0)
                try:
                    today_goal = engine.unit_converter(getattr(project, 'unit', 'symbols'), today_goal, 'symbols')
                except Exception:
                    today_goal = 0

            if today_goal and today_goal != float('inf'):
                symbol_candidates.append(max(0, today_goal))

        if symbol_candidates:
            return max(symbol_candidates)
        return 1000

    def estimate_daily_income_details(self, gamer):
        coins_cf = max(0.1, gamer.get_cf_value('coins', 1.0))
        symbol_income = gamer.round_money(self._estimate_daily_writing_symbols() / 100 * coins_cf)
        streak_income = self._estimate_streak_income(gamer)
        level_income = min(12, max(0, gamer.level - 1) * 0.75)
        total = gamer.round_money(symbol_income + streak_income + level_income)
        return {
            'symbols': gamer.round_money(symbol_income),
            'streaks': gamer.round_money(streak_income),
            'reliability': self.get_level_reliability_label(gamer),
            'total': total,
        }

    def calculate_credit_score(self, gamer):
        self.normalize()
        deposit_value = self._deposit_value_for_bank_scoring()
        inventory_value = self._inventory_value(gamer)
        daily_income = self.estimate_daily_income(gamer)
        score = 420
        score += min(120, gamer.level * 8)
        score += min(110, daily_income * 2)
        score += min(90, deposit_value / 8)
        score += min(70, inventory_value / 20)
        score += min(55, max(0, gamer.get_cf_value('coins', 1.0) - 1) * 35)
        score += min(60, len(self.deposit_history) * 10)
        score += min(50, sum(item.get('interest', 0) for item in self.deposit_history) / 5)
        late_credits = [item for item in self.credit_history if item.get('overdue_days', 0) > 0]
        history_overdue_days = sum(item.get('overdue_days', 0) for item in late_credits)
        total_overdue_days = max(self.overdue_days_total, history_overdue_days)
        worst_overdue_days = max([item.get('overdue_days', 0) for item in late_credits] + [0])
        successful_credits = len([
            item for item in self.credit_history
            if item.get('status') == 'paid' and item.get('overdue_days', 0) == 0
        ])
        score += min(65, successful_credits * 13)
        active_debt = self.credit.get_remaining_sum() if self.credit else 0
        score -= min(150, active_debt / max(1, daily_income * 3) * 40)
        score -= min(360, total_overdue_days * 32 + len(late_credits) * 45 + max(0, worst_overdue_days - 3) * 10)
        if self.credit and self.credit.get_status() == 'Просрочен':
            score -= 120
            worst_overdue_days = max(worst_overdue_days, self.credit.total_overdue_days)

        if worst_overdue_days >= 14:
            score = min(score, 500)
        elif worst_overdue_days >= 7:
            score = min(score, 560)
        elif worst_overdue_days >= 3:
            score = min(score, 630)
        elif worst_overdue_days >= 1:
            score = min(score, 700)
        self.credit_score = int(max(300, min(850, round(score))))
        return self.credit_score

    def get_credit_limit(self, gamer):
        score = self.calculate_credit_score(gamer)
        daily_income = self.estimate_daily_income(gamer)
        inventory_value = self._inventory_value(gamer)
        deposit_value = self._deposit_value_for_bank_scoring()
        multiplier = 7 + max(0, score - 300) / 55
        base_limit = daily_income * multiplier
        asset_limit = inventory_value * 0.2 + deposit_value * 0.55
        return gamer.round_money(max(250, base_limit + asset_limit))

    def get_max_credit_days(self):
        max_days = 30
        settings = engine.load_settings()
        if settings.get('global_streak', False):
            data = engine.load_data()
            current_streak_len = len(data.get('global_streaks', []))
            if current_streak_len > 0:
                max_days += current_streak_len
        return max(1, max_days)

    def get_credit_rate(self, gamer, amount=None, days=None):
        rate = self._calculate_credit_rate_base(gamer, amount, days)
        deposit_rate = self.get_deposit_rate(gamer)
        return round(max(deposit_rate + 0.18, min(1.85, rate)), 3)

    def _calculate_credit_rate_base(self, gamer, amount=None, days=None):
        score = self.calculate_credit_score(gamer)
        daily_income = self.estimate_daily_income(gamer)
        inflation = gamer.calculate_inflation()

        # Игровая дневная ставка. Кредит должен быть заметной нагрузкой:
        # 14 дней при хорошем рейтинге стоят около 7-9%, при плохом - до 18-22%.
        score_discount = (score - 300) / 550
        rate = 1.45 - score_discount * 0.85
        rate += min(0.25, max(0, inflation - 1) * 0.015)

        if days is not None:
            rate += min(0.30, max(0, int(days) - 14) * 0.006)

        if amount is not None and days is not None:
            payment_capacity = max(1, daily_income * max(1, int(days)) * 0.65)
            burden = max(0, float(amount) - payment_capacity) / payment_capacity
            rate += min(0.35, burden * 0.18)

        return round(max(0.55, min(1.85, rate)), 3)

    def get_deposit_rate(self, gamer):
        credit_rate = self._calculate_credit_rate_base(gamer)
        score = self.calculate_credit_score(gamer)
        spread = 0.26 - (score - 300) / 550 * 0.12
        spread = max(0.14, min(0.26, spread))
        return round(max(0.25, min(1.55, credit_rate - spread)), 3)

    def _preview_credit_interest(self, amount, rate, days):
        daily_rate = rate / 100
        if daily_rate <= 0:
            total = amount
        else:
            growth = (1 + daily_rate) ** days
            daily_payment = round(amount * daily_rate * growth / (growth - 1), 1)
            total = daily_payment * days
        return max(0, round(total - amount, 1))

    def _preview_deposit_interest(self, amount, rate, days):
        return round(amount * ((1 + rate / 100) ** days - 1), 1)

    def preview_product(self, gamer, product_type, amount, days):
        self.normalize()
        amount = max(0, float(amount))
        days = max(1, int(days))
        if product_type == 'credit':
            days = min(days, self.get_max_credit_days())
            rate = self.get_credit_rate(gamer, amount, days)
            limit = self.get_credit_limit(gamer)
            interest = self._preview_credit_interest(amount, rate, days)
        else:
            rate = self.get_deposit_rate(gamer)
            limit = None
            interest = self._preview_deposit_interest(amount, rate, days)
        return {'rate': rate, 'interest': interest, 'total': round(amount + interest, 1), 'limit': limit}

    def open_credit(self, gamer, amount, days):
        self.normalize()
        self._attach_to_gamer(gamer)
        amount = gamer.round_money(amount)
        if self.credit:
            return False, 'У вас уже есть активный кредит'
        if gamer.level < 3:
            return False, 'Кредиты доступны с 3 уровня'
        limit = self.get_credit_limit(gamer)
        if amount > limit:
            return False, f'Сумма выше кредитного лимита: {limit} монет'
        max_days = self.get_max_credit_days()
        if days > max_days:
            return False, f'Максимальный срок кредита: {max_days} дн.'
        preview = self.preview_product(gamer, 'credit', amount, days)
        self.credit = Credit(amount, days, preview['rate'])
        gamer.set_coins(amount, process_bank_events=False, save=False)
        message = f'Кредит открыт. На счет зачислено {amount} монет'
        self._add_notification(
            f'{message}. Первый платеж {self.credit.get_first_payment_date().strftime("%d.%m.%Y")}: '
            f'{self.credit.get_daily_payment()} монет.'
        )
        gamer.save()
        return True, message

    def open_deposit(self, gamer, amount, days):
        self.normalize()
        self._attach_to_gamer(gamer)
        amount = gamer.round_money(amount)
        if self.deposit:
            return False, 'У вас уже есть активный вклад'
        if gamer.get_coins() < amount:
            return False, f'Недостаточно монет. Нужно: {amount}'
        preview = self.preview_product(gamer, 'deposit', amount, days)
        gamer.remove_coins(amount, process_bank_events=False, save=False)
        self.deposit = Deposit(amount, days, preview['rate'])
        message = f'Вклад открыт. Списано {amount} монет'
        self._add_notification(f'{message}. Ожидаемый доход: {preview["interest"]} монет.')
        gamer.save()
        return True, message

    def process_credit_penalty(self, gamer):
        messages = self.process_daily_events(gamer, auto_pay=False, notify=True, save=True, include_deposit=False)
        return '\n'.join(messages) if messages else None

    def make_loan_payment(self, gamer):
        self.normalize()
        self._attach_to_gamer(gamer)
        if not self.credit:
            return 'Нет активного кредита'
        today = engine.today_for_test()
        if today < self.credit.get_first_payment_date():
            return f'Первый платеж будет доступен {self.credit.get_first_payment_date().strftime("%d.%m.%Y")}'

        self._process_overdue_credit_days(gamer, today)
        if not self.credit:
            gamer.save()
            return 'Кредит закрыт'

        if self.credit.last_payment_date == today:
            return 'Платеж по кредиту сегодня уже внесен'

        message = self._try_pay_credit_today(gamer, today, notify_if_not_enough=True, automatic=False)
        self._add_notification(message)
        gamer.save()
        return message

    def partial_repay_credit(self, gamer, amount):
        self.normalize()
        self._attach_to_gamer(gamer)
        if not self.credit:
            return 'Нет активного кредита'

        try:
            amount = gamer.round_money(float(amount))
        except (TypeError, ValueError):
            return 'Сумма погашения должна быть числом'

        if amount <= 0:
            return 'Сумма погашения должна быть больше 0'
        if gamer.get_coins() < amount:
            return f'Недостаточно монет. Нужно: {amount}'

        self.process_daily_events(gamer, auto_pay=False, notify=False, save=False, include_deposit=False)
        if not self.credit:
            gamer.save()
            return 'Кредит закрыт'

        amount = min(amount, self.credit.get_remaining_sum())
        old_daily_payment = self.credit.get_daily_payment()
        old_interest = self.credit.get_interest()

        gamer.remove_coins(amount, process_bank_events=False, save=False)
        principal_payment = min(amount, self.credit.credit_sum)
        extra_payment = round(amount - principal_payment, 1)
        self.credit.credit_sum = round(max(0, self.credit.credit_sum - principal_payment), 1)
        if extra_payment > 0:
            self.credit.paid_amount += extra_payment

        if self.credit.get_remaining_sum() <= 0:
            self.credit_history.append({
                'sum': self.credit.credit_sum,
                'interest': round(self.credit.get_interest(), 1),
                'overdue_days': self.credit.total_overdue_days,
                'status': 'paid',
                'paid_date': engine.today_for_test(),
            })
            self.credit = None
            message = f'Частичное погашение: {amount} монет. Кредит полностью погашен.'
        else:
            new_interest = self.credit.get_interest()
            new_daily_payment = self.credit.get_daily_payment()
            message = (
                f'Частичное погашение: {amount} монет.\n'
                f'Осталось: {self.credit.get_remaining_sum()} монет.\n'
                f'Платеж: {old_daily_payment} -> {new_daily_payment} монет.\n'
                f'Проценты: {old_interest} -> {new_interest} монет.'
            )

        self._add_notification(message)
        gamer.save()
        return message

    def return_deposit(self, gamer=None, early=False):
        self.normalize()
        gamer = gamer or game.load_game()
        self._attach_to_gamer(gamer)
        if not self.deposit:
            return 'Нет вклада'
        if self.deposit.get_return_date() > engine.today_for_test() and not early:
            return 'Срок вклада еще не наступил'

        principal = self.deposit.deposit_sum
        interest = self.deposit.get_interest()
        if early:
            total_sum = principal
            lost_interest = interest
            status = 'early_returned'
            notification = (
                f'Депозит снят досрочно. Возвращено {total_sum} монет. '
                f'Проценты {lost_interest} монет сгорели.'
            )
            message = (f'\nДЕПОЗИТ СНЯТ ДОСРОЧНО\n'
                       f'Вы получили {total_sum} монет\n'
                       f'Проценты сгорели: {lost_interest} монет')
        else:
            total_sum = self.deposit.get_total_sum()
            lost_interest = 0
            status = 'returned'
            notification = f'Депозит снят. Вы получили {total_sum} монет.'
            message = (f'\nДЕПОЗИТ СНЯТ\n'
                       f'Вы получили {total_sum} монет')

        gamer.set_coins(total_sum, process_bank_events=False, save=False)
        self.deposit_history.append({
            'sum': principal,
            'interest': 0 if early else interest,
            'lost_interest': lost_interest,
            'status': status,
            'returned_date': engine.today_for_test(),
        })
        self.deposit = None
        self._add_notification(notification)
        gamer.save()

        return message

    def withdraw_deposit_interest(self, gamer):
        self.normalize()
        self._attach_to_gamer(gamer)
        if not self.deposit:
            return 'Нет активного вклада'
        today = engine.today_for_test()
        if self.deposit.last_interest_withdraw_date == today:
            return 'Проценты сегодня уже сняты'
        interest = self.deposit.get_available_interest()
        if interest <= 0:
            return 'Пока нет доступных процентов'
        gamer.set_coins(interest, process_bank_events=False, save=False)
        self.deposit.withdrawn_interest += interest
        self.deposit.interest_withdrawals.append({'date': today, 'amount': interest})
        self.deposit.last_interest_withdraw_date = today
        message = f'Сняты проценты по вкладу: {interest} монет'
        self._add_notification(message)
        gamer.save()
        return message

    def top_up_deposit(self, gamer, amount):
        self.normalize()
        self._attach_to_gamer(gamer)
        if not self.deposit:
            return 'Нет активного вклада'

        try:
            amount = gamer.round_money(float(amount))
        except (TypeError, ValueError):
            return 'Сумма пополнения должна быть числом'

        if amount <= 0:
            return 'Сумма пополнения должна быть больше 0'
        if gamer.get_coins() < amount:
            return f'Недостаточно монет. Нужно: {amount}'

        gamer.remove_coins(amount, process_bank_events=False, save=False)
        self.deposit.top_up(amount)
        message = f'Вклад пополнен на {amount} монет'
        self._add_notification(message)
        gamer.save()
        return message

    def process_deposit_maturity(self, gamer):
        self.normalize()
        self._attach_to_gamer(gamer)
        if not self.deposit or self.deposit.get_return_date() > engine.today_for_test():
            return None
        total_sum = self.deposit.get_total_sum()
        interest = self.deposit.get_interest()
        gamer.set_coins(total_sum, process_bank_events=False, save=False)
        self.deposit_history.append({'sum': self.deposit.deposit_sum, 'interest': interest, 'status': 'auto_returned'})
        self.deposit = None
        message = f'Срок вклада завершен. На счет возвращено {total_sum} монет.'
        self._add_notification(message)
        gamer.save()
        return message

    def return_credit(self, gamer=None):
        self.normalize()
        gamer = gamer or game.load_game()
        self._attach_to_gamer(gamer)
        if not self.credit:
            return 'Нет кредита'

        self.process_daily_events(gamer, auto_pay=False, notify=False, save=False, include_deposit=False)
        result = self.credit.repay(gamer)
        if self.credit.get_remaining_sum() <= 0:
            self.credit_history.append({
                'sum': self.credit.credit_sum,
                'interest': round(self.credit.get_interest(), 1),
                'overdue_days': self.credit.total_overdue_days,
                'status': 'paid',
                'paid_date': engine.today_for_test(),
            })
            self.credit = None
            self._add_notification(result)
        gamer.save()
        return result

    def process_daily_events(self, gamer, auto_pay=True, notify=True, save=True, include_deposit=True):
        self.normalize()
        self._attach_to_gamer(gamer)
        messages = []

        if include_deposit:
            deposit_message = self.process_deposit_maturity(gamer)
            if deposit_message:
                messages.append(deposit_message)
            elif self.deposit:
                interest_message = self._notify_available_deposit_interest()
                if interest_message:
                    messages.append(interest_message)

        if self.credit:
            messages.extend(self._process_credit_day(gamer, auto_pay=auto_pay, notify=notify))

        if messages and save:
            gamer.save()
        return messages

    def _process_credit_day(self, gamer, auto_pay=True, notify=True):
        today = engine.today_for_test()
        messages = []
        if not self.credit:
            return messages
        if today < self.credit.get_first_payment_date():
            return messages

        start_date = self.credit.get_first_payment_date()
        if self.credit.last_daily_check_date is not None:
            start_date = max(start_date, self.credit.last_daily_check_date + timedelta(days=1))

        current_date = start_date
        while self.credit and current_date <= today:
            if self.credit.last_payment_date == current_date:
                self.credit.last_daily_check_date = current_date
                current_date += timedelta(days=1)
                continue

            if auto_pay:
                message = self._try_pay_credit_today(
                    gamer,
                    current_date,
                    notify_if_not_enough=notify and current_date == today,
                    automatic=True,
                )
                if message:
                    messages.append(message)
                if not self.credit:
                    return messages
                if self.credit.last_payment_date == current_date:
                    current_date += timedelta(days=1)
                    continue

            if current_date == today:
                if not auto_pay and notify:
                    message = self._notify_credit_payment_due(today)
                    if message:
                        messages.append(message)
                break

            message = self._apply_credit_overdue_for_date(gamer, current_date)
            if message:
                messages.append(message)
            current_date += timedelta(days=1)

        return messages

    def _apply_credit_overdue_for_date(self, gamer, overdue_date):
        if not self.credit:
            return None
        credit = self.credit
        if credit.last_payment_date == overdue_date:
            credit.last_daily_check_date = overdue_date
            return None

        penalty = max(5, round(credit.get_remaining_sum() * 0.015, 1))
        damage = 10
        credit.accrued_penalty += penalty
        credit.last_penalty_date = overdue_date
        credit.total_overdue_days += 1
        credit.last_daily_check_date = overdue_date
        self.overdue_days_total += 1
        gamer.health = max(0, gamer.health - damage)
        message = (
            f'Просрочка платежа по кредиту за {overdue_date.strftime("%d.%m.%Y")}: '
            f'штраф {penalty} монет, урон здоровью {damage}.'
        )
        self._add_notification(message)
        return message

    def _process_overdue_credit_days(self, gamer, today, messages=None):
        if not self.credit:
            return
        credit = self.credit
        first_payment_date = credit.get_first_payment_date()
        if today <= first_payment_date:
            return

        start_date = first_payment_date
        if credit.last_daily_check_date is not None:
            start_date = max(start_date, credit.last_daily_check_date + timedelta(days=1))

        current_date = start_date
        while self.credit and current_date < today:
            message = self._apply_credit_overdue_for_date(gamer, current_date)
            if message and messages is not None:
                messages.append(message)
            current_date += timedelta(days=1)

    def _try_pay_credit_today(self, gamer, today, notify_if_not_enough=True, automatic=True):
        if not self.credit:
            return None
        payment = self.credit.get_daily_payment()
        if gamer.get_coins() < payment:
            if notify_if_not_enough:
                return self._notify_credit_payment_due(today)
            return None

        gamer.remove_coins(payment, process_bank_events=False, save=False)
        self.credit.paid_amount += payment
        self.credit.last_payment_date = today
        self.credit.last_daily_check_date = today
        if self.credit.get_remaining_sum() <= 0:
            self.credit_history.append({
                'sum': self.credit.credit_sum,
                'interest': round(self.credit.get_interest(), 1),
                'overdue_days': self.credit.total_overdue_days,
                'status': 'paid',
                'paid_date': engine.today_for_test(),
            })
            self.credit = None
            prefix = 'Автоплатеж' if automatic else 'Платеж'
            return f'{prefix} по кредиту: {payment} монет. Кредит полностью погашен.'
        prefix = 'Автоплатеж' if automatic else 'Платеж'
        return f'{prefix} по кредиту: {payment} монет. Осталось: {self.credit.get_remaining_sum()} монет.'

    def _notify_credit_payment_due(self, today):
        if not self.credit or self.credit.last_payment_notice_date == today:
            return None
        payment = self.credit.get_daily_payment()
        self.credit.last_payment_notice_date = today
        message = f'Сегодня платеж по кредиту: {payment} монет. На балансе недостаточно средств для автоплатежа.'
        self._add_notification(message)
        return message

    def _notify_available_deposit_interest(self):
        if not self.deposit:
            return None
        today = engine.today_for_test()
        if today <= self.deposit.give_date:
            return None
        if self.deposit.last_interest_withdraw_date == today:
            return None
        if self.deposit.last_interest_notice_date == today:
            return None
        interest = self.deposit.get_available_interest()
        if interest <= 0:
            return None
        self.deposit.last_interest_notice_date = today
        message = f'По вкладу доступны проценты к снятию: {interest} монет.'
        self._add_notification(message)
        return message

    def _add_notification(self, text):
        data = engine.load_data()
        notifications = data.get('notifications', {'new': [], 'read': []})
        if not isinstance(notifications, dict):
            notifications = {'new': [], 'read': []}
        notifications.setdefault('new', [])
        notifications.setdefault('read', [])
        notifications['new'].append(engine.Notification(text, tag='bank'))
        data['notifications'] = notifications
        engine.save_data(data)


# Функции для объектов-функций
def health_potion_func(do, add=None):
    """Функция для зелий здоровья"""
    # Загружаем объект игрока
    gamer = game.load_game()

    if do == 'use':
        max_health = gamer.get_max_health()
        # Проверка: не лечим, если здоровье уже полное
        if gamer.health >= max_health:
            # Возвращаем False или строку, чтобы FuncItem мог понять (опционально)
            # Но так как предмет уже списан в FuncItem.use, просто лечим "в пустоту"
            # или можно восстановить предмет, если здоровье полное (сложная логика).
            # Пока просто восстанавливаем до максимума.
            pass

        old_health = gamer.health
        gamer.health += add

        # Ограничиваем максимумом здоровья игрока.
        if gamer.health > max_health:
            gamer.health = max_health

        gamer.last_health_recovery_at = game.get_effective_now()
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
            gamer.set_coins(win_prize)
            gamer.save()

        return message

    if do == '?':
        return 'Усугубляет лудоманию'

    return 'Неизвестное действие'

def calculate_item_price(price):
    """Считает стоимость предмета с мягким ростом по уровню игрока.

    Доход монет растет через cf_coins примерно на 6.25% за уровень, поэтому
    прежний рост цены на 15% за уровень делал предметы все менее доступными.
    """
    gamer = game.load_game()
    level = max(gamer.level, 1)
    level_multiplier = 1 + (level - 1) * 0.05

    return round(price * level_multiplier, 1)

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

freeze = FuncItem('❄️Заморозка', price=calculate_freeze_price, item_type='Предметы', level=3,
                  description='Заморозка позволяет пропустить один день стрика в проекте с дедлайном и активным стриком'
                              '️\n⚠️ Важно: чем больше заморозок вы используете, тем дороже они становятся.'
                              '\nМожно иметь не более 2 заморозок в инвентаре и купить только 1 за раз.')
lottery_ticket = FuncItem("🎟️ Лотерейный билет", price=lambda: calculate_item_price(10), item_type='Предметы', level=3, func=lottery_ticket_func,
                          credit_allowed=False,
                          description=f'Лотерейный билет "5 из 30". Угадайте числа и сорвите джекпот!')
health_potion_5 = FuncItem('🧪  Микро зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(10), add=5,
                           description='🧪  Восстанавливает здоровье на 5 единиц')
health_potion_10 = FuncItem('🧪  Малое зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(20), add=10,
                           description='🧪  Восстанавливает здоровье на 10 единиц')
health_potion_25 = FuncItem('🧪  Среднее зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(50), add=25,
                            description='🧪  Восстанавливает здоровье на 25 единиц')
health_potion_50 = FuncItem('🧪  Большое зелье здоровья', item_type='Зелья', level=1, func=health_potion_func, price=lambda: calculate_item_price(100), add=50,
                            description='🧪  Восстанавливает здоровье на 50 единиц')
health_recovery = FuncItem('🧪  Зелье воскрешения', item_type='Зелья', level=3, func=health_potion_func, price=lambda: calculate_item_price(200), add=100,
                           description='🧪  Полностью восстанавливает здоровье')
crown_of_the_first_era = Item(name='👑  Корона Первой Эпохи', item_type='Награды', price=0,
                              description='Корона выдается игрокам, которые прошли первую экономическую реформу в игре',
                              buff=Buff(name='Опыт миллионера',
                                        description='+1 к коэффициенту опыта',
                                        buff_type=Buff.POSITIVE,
                                        target_cf='exp',
                                        value=1.0)
                              )
millionaires_pen = Item(name='💎  Перо Миллионера', item_type='Награды', price=0,
                        description='Перо выдается игрокам, которые заработали больше миллиона монет до первой экономической реформы в игре',
                        buff=Buff(name='Удача миллионера',
                                  description='+1 к коэффициенту заработка',
                                  buff_type=Buff.POSITIVE,
                                  target_cf='coins',
                                  value= 1.0))
health_care_badge = Item(name='Знак заботы о здоровье', item_type='Награды', price=0,
                         description='Награда за подготовку аптечки автора.')
discipline_badge = Item(name='Знак дисциплины', item_type='Награды', price=0,
                        description='Награда за запасной день и заботу о стрике.')
bank_token = Item(name='Банковский жетон', item_type='Награды', price=0,
                  description='Награда за первый вклад в банке.')
collector_badge = Item(name='Знак коллекционера', item_type='Награды', price=0,
                       description='Награда за собранную коллекцию предметов.')
weekly_practice_badge = Item(name='Знак недельной практики', item_type='Награды', price=0,
                             description='Награда за семь дней записей подряд.')
fast_finish_badge = Item(name='Знак быстрого финала', item_type='Награды', price=0,
                         description='Награда за завершение текста за две недели.')
warm_streak_badge = Item(name='Знак теплого стрика', item_type='Награды', price=0,
                         description='Награда за неделю без заморозки.')
clean_finish_badge = Item(name='Знак чистого финиша', item_type='Награды', price=0,
                          description='Награда за завершение текста без заморозок.')
two_weeks_badge = Item(name='Знак двух недель', item_type='Награды', price=0,
                       description='Награда за четырнадцать дней записей подряд.')
no_ice_badge = Item(name='Знак без льда', item_type='Награды', price=0,
                    description='Награда за длительную серию без заморозок.')
deep_days_badge = Item(name='Знак глубоких дней', item_type='Награды', price=0,
                       description='Награда за несколько продуктивных дней.')
three_finishes_badge = Item(name='Знак трех финалов', item_type='Награды', price=0,
                            description='Награда за три завершенных текста.')
long_form_badge = Item(name='Знак большой формы', item_type='Награды', price=0,
                       description='Награда за завершение крупного текста.')
marathon_badge = Item(name='Знак марафонца', item_type='Награды', price=0,
                      description='Награда за длинный стрик до финиша.')
two_lines_badge = Item(name='Знак двух линий', item_type='Награды', price=0,
                       description='Награда за параллельную дисциплину в двух текстах.')
hall_of_fame_badge = Item(name='Знак зала славы', item_type='Награды', price=0,
                          description='Награда за большую коллекцию наград.')
global_week_badge = Item(name='Знак глобальной недели', item_type='Награды', price=0,
                         description='Награда за семь дней глобального стрика.')
global_two_weeks_badge = Item(name='Знак глобальных двух недель', item_type='Награды', price=0,
                              description='Награда за четырнадцать дней глобального стрика.')
global_habit_badge = Item(name='Знак глобальной привычки', item_type='Награды', price=0,
                          description='Награда за двадцать один день глобального стрика.')
global_month_badge = Item(name='Знак глобального месяца', item_type='Награды', price=0,
                          description='Награда за тридцать дней глобального стрика.')
clean_global_month_badge = Item(name='Знак чистого глобального месяца', item_type='Награды', price=0,
                                description='Награда за тридцать дней глобального стрика без заморозок.')
global_season_badge = Item(name='Знак глобального сезона', item_type='Награды', price=0,
                           description='Награда за шестьдесят дней глобального стрика.')
global_quarter_badge = Item(name='Знак глобального квартала', item_type='Награды', price=0,
                            description='Награда за девяносто дней глобального стрика.')
global_half_year_badge = Item(name='Знак глобального полугодия', item_type='Награды', price=0,
                              description='Награда за сто восемьдесят дней глобального стрика.')
global_year_badge = Item(name='Знак глобального года', item_type='Награды', price=0,
                         description='Награда за год глобального стрика.')
exp_potion_1hrs = FuncItem(name='🧪⚡️  Часовое зелье познания',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(50),
                           description='Увеличивает коэффициент опыта на 1 на один час',
                           buff=Buff(name='Бустер опыта',
                                     description='Применено зелье познания',
                                     target_cf='exp',
                                     value=1.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60))
exp_potion_24hrs = FuncItem(name='🧪⚡️  Суточное зелье познания',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(600),
                           description='Увеличивает коэффициент опыта на 1 на один день',
                           buff=Buff(name='Бустер опыта',
                                     description='Применен зелье познания',
                                     target_cf='exp',
                                     value=1.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60*24))
super_exp_potion_1hrs = FuncItem(name='🧪⚡️  Часовое зелье просвещения',
                           item_type='Зелья',
                           level=8,
                           price=lambda: calculate_item_price(300),
                           description='Увеличивает коэффициент опыта на 10 на один час',
                           buff=Buff(name='Супер бустер опыта',
                                     description='Применено зелье познания',
                                     target_cf='exp',
                                     value=10.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60))
super_exp_potion_24hrs = FuncItem(name='🧪⚡️  Суточное зелье просвещения',
                           item_type='Зелья',
                           level=8,
                           price=lambda: calculate_item_price(3600),
                           description='Увеличивает коэффициент опыта на 10 на один день',
                           buff=Buff(name='Супер бустер опыта',
                                     description='Применен зелье познания',
                                     target_cf='exp',
                                     value=10.0,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60*24))

coin_potion_1hrs = FuncItem(name='🧪⚡️  Часовое зелье доходности',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(25),
                           description='Увеличивает коэффициент монет на 0.5 на один час',
                           buff=Buff(name='Минибустер прибыли',
                                     description='Применено зелье прибыли',
                                     target_cf='coins',
                                     value=0.5,
                                     buff_type=Buff.POSITIVE,
                                     duration_minutes=60))
coin_potion_24hrs = FuncItem(name='🧪⚡️  Суточное зелье доходности',
                           item_type='Зелья',
                           level=2,
                           price=lambda: calculate_item_price(300),
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
                      'Суточное зелье просвещения': super_exp_potion_24hrs,},
                 'Предметы': {'Заморозка': freeze,
                              'Лотерейный билет': lottery_ticket,},
                 'Награды': {'👑 Корона Первой Эпохи': crown_of_the_first_era,
                             '💎 Перо Миллионера': millionaires_pen,
                             'Знак заботы о здоровье': health_care_badge,
                             'Знак дисциплины': discipline_badge,
                             'Банковский жетон': bank_token,
                             'Знак коллекционера': collector_badge,
                             'Знак недельной практики': weekly_practice_badge,
                             'Знак быстрого финала': fast_finish_badge,
                             'Знак теплого стрика': warm_streak_badge,
                             'Знак чистого финиша': clean_finish_badge,
                             'Знак двух недель': two_weeks_badge,
                             'Знак без льда': no_ice_badge,
                             'Знак глубоких дней': deep_days_badge,
                             'Знак трех финалов': three_finishes_badge,
                             'Знак большой формы': long_form_badge,
                             'Знак марафонца': marathon_badge,
                             'Знак двух линий': two_lines_badge,
                             'Знак зала славы': hall_of_fame_badge,
                             'Знак глобальной недели': global_week_badge,
                             'Знак глобальных двух недель': global_two_weeks_badge,
                             'Знак глобальной привычки': global_habit_badge,
                             'Знак глобального месяца': global_month_badge,
                             'Знак чистого глобального месяца': clean_global_month_badge,
                             'Знак глобального сезона': global_season_badge,
                             'Знак глобального квартала': global_quarter_badge,
                             'Знак глобального полугодия': global_half_year_badge,
                             'Знак глобального года': global_year_badge,},}


def _normalize_item_identifier(value):
    return (
        str(value)
        .replace('👑', '')
        .replace('💎', '')
        .replace('❄️', '')
        .replace('💸', '')
        .replace('🧪', '')
        .casefold()
        .strip()
    )


def find_registry_item(category, item_identifier):
    """Возвращает (ключ_реестра, объект) по ключу, имени или старому отображаемому имени."""
    registry = ITEM_REGISTRY.get(category, {})
    if not isinstance(registry, dict):
        return None, None

    item = registry.get(item_identifier)
    if item is not None:
        return item_identifier, item

    for registry_key, registry_item in registry.items():
        if getattr(registry_item, 'name', None) == item_identifier:
            return registry_key, registry_item

    normalized_identifier = _normalize_item_identifier(item_identifier)
    for registry_key, registry_item in registry.items():
        if _normalize_item_identifier(registry_key) == normalized_identifier:
            return registry_key, registry_item
        if _normalize_item_identifier(getattr(registry_item, 'name', '')) == normalized_identifier:
            return registry_key, registry_item

    return None, None
