from datetime import date, timedelta
import math

import engine
import game_data


class DummyGamer:
    def __init__(self, coins):
        self.coins = coins
        self.bank_account = None
        self.saved = False
        self.health = 100

    @staticmethod
    def round_money(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0
        return round(math.ceil((value - 1e-9) * 10) / 10, 1)

    def get_coins(self):
        return self.coins

    def remove_coins(self, removed, process_bank_events=True, save=True):
        self.coins = self.round_money(self.coins - removed)

    def set_coins(self, coins, process_bank_events=True, save=True):
        self.coins = self.round_money(self.coins + coins)
        return coins

    def save(self):
        self.saved = True


def test_top_up_deposit_does_not_credit_interest_retroactively(monkeypatch):
    start = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: start)
    deposit = game_data.Deposit(100, 10, 1)

    monkeypatch.setattr(engine, 'today_for_test', lambda: start + timedelta(days=5))
    interest_before_topup = deposit.get_available_interest()
    deposit.top_up(100)

    assert deposit.get_sum() == 200
    assert deposit.get_available_interest() == interest_before_topup

    monkeypatch.setattr(engine, 'today_for_test', lambda: start + timedelta(days=6))
    assert deposit.get_available_interest() > interest_before_topup


def test_credit_full_repayment_sum_is_remaining_balance(monkeypatch):
    start = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: start)
    credit = game_data.Credit(100, 10, 1)
    credit.paid_amount = 25
    credit.accrued_penalty = 3

    assert credit.get_full_repayment_sum() == credit.get_remaining_sum()


def test_bank_account_top_up_deposit_spends_coins_and_saves(monkeypatch):
    today = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    gamer = DummyGamer(250)
    account = game_data.BankAccount(deposit=game_data.Deposit(100, 10, 1))

    message = account.top_up_deposit(gamer, 75)

    assert message == 'Вклад пополнен на 75.0 монет'
    assert gamer.get_coins() == 175
    assert account.deposit.get_sum() == 175
    assert account.deposit.topups == [{'date': today, 'amount': 75.0}]
    assert gamer.saved is True


def test_deposit_interest_accrues_for_skipped_days(monkeypatch):
    start = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: start)
    deposit = game_data.Deposit(100, 10, 1)

    monkeypatch.setattr(engine, 'today_for_test', lambda: start + timedelta(days=5))

    assert deposit.get_available_interest() == round(100 * ((1.01 ** 5) - 1), 1)


def test_deposit_without_interest_withdrawal_has_no_available_interest(monkeypatch):
    start = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: start)
    deposit = game_data.Deposit(100, 10, 1, allow_interest_withdrawal=False)
    account = game_data.BankAccount(deposit=deposit)
    gamer = DummyGamer(0)

    monkeypatch.setattr(engine, 'today_for_test', lambda: start + timedelta(days=5))

    assert deposit.get_available_interest() == 0
    assert deposit.can_withdraw_interest() == (False, 'По этому вкладу снятие процентов не предусмотрено')
    assert account.withdraw_deposit_interest(gamer) == 'По этому вкладу снятие процентов не предусмотрено'
    assert gamer.get_coins() == 0


def test_deposit_without_interest_withdrawal_preview_is_more_profitable(monkeypatch):
    account = game_data.BankAccount()
    gamer = DummyGamer(1000)
    monkeypatch.setattr(account, 'get_deposit_rate', lambda gamer: 1)

    with_withdrawal = account.preview_product(
        gamer,
        'deposit',
        100,
        10,
        allow_interest_withdrawal=True,
    )
    without_withdrawal = account.preview_product(
        gamer,
        'deposit',
        100,
        10,
        allow_interest_withdrawal=False,
    )

    assert without_withdrawal['rate'] > with_withdrawal['rate']
    assert without_withdrawal['interest'] > with_withdrawal['interest']
    assert without_withdrawal['total'] > with_withdrawal['total']


def test_deposit_auto_return_after_skipped_days_caps_interest_at_term(monkeypatch):
    start = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: start)
    account = game_data.BankAccount(deposit=game_data.Deposit(100, 10, 1))
    gamer = DummyGamer(0)
    monkeypatch.setattr(account, '_add_notification', lambda text: None)

    monkeypatch.setattr(engine, 'today_for_test', lambda: start + timedelta(days=15))
    messages = account.process_daily_events(gamer, auto_pay=True, notify=True, save=False)

    term_interest = round(100 * ((1.01 ** 10) - 1), 1)
    assert account.deposit is None
    assert gamer.get_coins() == round(100 + term_interest, 1)
    assert account.deposit_history == [{
        'sum': 100,
        'interest': term_interest,
        'status': 'auto_returned',
    }]
    assert messages == [f'Срок вклада завершен. На счет возвращено {round(100 + term_interest, 1)} монет.']


def test_credit_auto_pay_catches_up_missed_days(monkeypatch):
    start = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: start)
    credit = game_data.Credit(100, 10, 1)
    account = game_data.BankAccount(credit=credit)
    gamer = DummyGamer(1000)
    monkeypatch.setattr(account, '_add_notification', lambda text: None)

    monkeypatch.setattr(engine, 'today_for_test', lambda: start + timedelta(days=4))
    messages = account.process_daily_events(gamer, auto_pay=True, notify=True, save=False, include_deposit=False)

    daily_payment = credit.get_base_daily_payment()
    assert len(messages) == 4
    assert credit.paid_amount == round(daily_payment * 4, 1)
    assert credit.last_payment_date == start + timedelta(days=4)
    assert credit.last_daily_check_date == start + timedelta(days=4)
    assert credit.total_overdue_days == 0
    assert credit.accrued_penalty == 0
    assert gamer.get_coins() == 1000 - round(daily_payment * 4, 1)
    assert gamer.health == 100


def test_credit_auto_pay_stops_when_money_runs_out_then_penalizes_missed_days(monkeypatch):
    start = date(2026, 7, 1)
    monkeypatch.setattr(engine, 'today_for_test', lambda: start)
    credit = game_data.Credit(100, 10, 1)
    daily_payment = credit.get_base_daily_payment()
    account = game_data.BankAccount(credit=credit)
    gamer = DummyGamer(round(daily_payment * 2, 1))
    monkeypatch.setattr(account, '_add_notification', lambda text: None)

    monkeypatch.setattr(engine, 'today_for_test', lambda: start + timedelta(days=4))
    messages = account.process_daily_events(gamer, auto_pay=True, notify=True, save=False, include_deposit=False)

    assert credit.paid_amount == round(daily_payment * 2, 1)
    assert credit.last_payment_date == start + timedelta(days=2)
    assert credit.last_daily_check_date == start + timedelta(days=3)
    assert credit.total_overdue_days == 1
    assert account.overdue_days_total == 1
    assert credit.accrued_penalty > 0
    assert gamer.get_coins() == 0
    assert gamer.health == 90
    assert any('Просрочка платежа по кредиту за 04.07.2026' in message for message in messages)
    assert any('Сегодня платеж по кредиту' in message for message in messages)
