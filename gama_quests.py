"""Каталог и условия игровых квестов."""

from datetime import datetime, timedelta

import engine
import game_data
from game import Quest


QUEST_BUFF_META = {
    'exp': {
        'name': '⭐️ Квестовая специализация: опыт',
        'parameter_name': 'опыта',
        'description': 'Постоянный бонус к коэффициенту опыта за писательские и учебные квесты.',
    },
    'coins': {
        'name': '⭐️ Квестовая специализация: монеты',
        'parameter_name': 'монет',
        'description': 'Постоянный бонус к коэффициенту монет за экономические и коллекционные квесты.',
    },
    'health_recovery': {
        'name': '⭐️ Квестовая специализация: восстановление',
        'parameter_name': 'восстановления',
        'description': 'Постоянный бонус к восстановлению здоровья за квесты дисциплины и устойчивости.',
    },
}


QUEST_BUFF_TARGETS = {
    'save_100_coins': 'coins',
    'open_bank_deposit': 'coins',
    'keep_no_credit_with_500_coins': 'coins',
    'save_5000_coins_no_credit': 'coins',
    'collect_five_items': 'coins',
    'collect_ten_awards': 'coins',
    'keep_deposit_1000_coins': 'coins',
    'return_deposit_with_profit': 'coins',

    'keep_health_potion': 'health_recovery',
    'restore_full_health': 'health_recovery',
    'activate_positive_buff': 'health_recovery',
    'own_freeze_item': 'health_recovery',
    'no_freeze_7_days': 'health_recovery',
    'finish_text_with_no_freezes': 'health_recovery',
    'no_freeze_14_days': 'health_recovery',
    'global_streak_3_days': 'health_recovery',
    'global_streak_7_days': 'health_recovery',
    'global_streak_14_days': 'health_recovery',
    'global_streak_21_days': 'health_recovery',
    'global_streak_30_days': 'health_recovery',
    'global_streak_30_days_no_freezes': 'health_recovery',
    'global_streak_60_days': 'health_recovery',
    'global_streak_90_days': 'health_recovery',
    'global_streak_180_days': 'health_recovery',
    'global_streak_365_days': 'health_recovery',
}


def make_quest_buff(level, target_cf):
    value = round(0.01 + min(max(level, 1), 12) * 0.005, 3)
    meta = QUEST_BUFF_META[target_cf]
    return game_data.Buff(
        name=meta['name'],
        description=f"{meta['description']} +{value:g} к параметру за завершение квеста.",
        buff_type=game_data.Buff.POSITIVE,
        target_cf=target_cf,
        value=value,
        duration_minutes=None,
        source='Квест',
        stackable=True,
    )


def make_reward_buffs(level, quest_id=None, target=None):
    if target is None or target == 'both':
        target = QUEST_BUFF_TARGETS.get(quest_id, 'exp')
    targets = target if isinstance(target, (tuple, list)) else (target,)
    return [make_quest_buff(level, target_cf) for target_cf in targets]


def quest(*args, buff_target='both', reward_buffs=None, **kwargs):
    level = kwargs.get('level', 1)
    quest_id = kwargs.get('quest_id')
    reward_items = kwargs.get('reward_items') or []
    for reward_item in reward_items:
        if reward_item.get('category', 'Награды') != 'Награды':
            continue
        registry_key, _ = game_data.find_registry_item('Награды', reward_item.get('name'))
        if registry_key:
            reward_item['name'] = registry_key
    if reward_buffs is None:
        has_award_reward = any(item.get('category', 'Награды') == 'Награды' for item in reward_items)
        reward_buffs = [] if has_award_reward else make_reward_buffs(level, quest_id=quest_id, target=buff_target)
    return Quest(*args, reward_buffs=reward_buffs, **kwargs)


def get_projects():
    data = engine.load_data()
    projects = data.get('projects', {})
    if isinstance(projects, dict):
        return list(projects.values())
    return list(projects)


def get_note_dates(project, only_positive=True):
    dates = set()
    for note in getattr(project, 'notes', []):
        if only_positive and note.get_added_symbols() <= 0:
            continue
        dates.add(note.get_date_create())
    return dates


def get_symbols_by_date(projects):
    symbols_by_date = {}
    for project in projects:
        for note in getattr(project, 'notes', []):
            if note.get_added_symbols() <= 0:
                continue
            note_date = note.get_date_create()
            symbols_by_date[note_date] = symbols_by_date.get(note_date, 0) + note.get_added_symbols()
    return symbols_by_date


def get_completed_projects():
    return [project for project in get_projects() if getattr(project, 'status', None) == 'завершен']


def count_positive_notes(project):
    return sum(1 for note in getattr(project, 'notes', []) if note.get_added_symbols() > 0)


def has_consecutive_dates(dates, days_count):
    if len(dates) < days_count:
        return False

    sorted_dates = sorted(dates)
    current_len = 1
    for previous_date, current_date in zip(sorted_dates, sorted_dates[1:]):
        if current_date == previous_date + timedelta(days=1):
            current_len += 1
            if current_len >= days_count:
                return True
        elif current_date != previous_date:
            current_len = 1
    return current_len >= days_count


def quest_start_date(quest):
    start_date = getattr(quest, 'start_date', None)
    if isinstance(start_date, datetime):
        return start_date.date()
    return start_date


def reach_level_2(gamer, quest):
    return gamer.level >= 2


def save_100_coins(gamer, quest):
    return gamer.get_coins() >= 100


def keep_health_potion(gamer, quest):
    potions = gamer.items.get('Зелья', {})
    return any(count > 0 and 'здоровья' in str(name).casefold() for name, count in potions.items())


def restore_full_health(gamer, quest):
    return gamer.health >= 100


def activate_positive_buff(gamer, quest):
    return len(gamer.get_all_buffs(positive=True)) > 0


def own_freeze_item(gamer, quest):
    items = gamer.items.get('Предметы', {})
    return any(count > 0 and 'заморозка' in str(name).casefold() for name, count in items.items())


def open_bank_deposit(gamer, quest):
    bank_account = getattr(gamer, 'bank_account', None)
    return bool(bank_account and bank_account.deposit)


def keep_no_credit_with_500_coins(gamer, quest):
    bank_account = getattr(gamer, 'bank_account', None)
    has_credit = bool(bank_account and bank_account.credit)
    return gamer.get_coins() >= 500 and not has_credit


def collect_2000_exp(gamer, quest):
    return gamer.exp >= 2000


def collect_five_items(gamer, quest):
    total_count = 0
    for category_items in gamer.items.values():
        if not isinstance(category_items, dict):
            continue
        total_count += sum(count for count in category_items.values() if count > 0)
    return total_count >= 5


def write_notes_7_days_any_text(gamer, quest):
    return any(has_consecutive_dates(get_note_dates(project), 7) for project in get_projects())


def finish_text_in_14_days(gamer, quest):
    for project in get_projects():
        if getattr(project, 'status', None) != 'завершен':
            continue
        create_date = getattr(project, 'create_date', None)
        complete_date = getattr(project, 'complete_date', None)
        if create_date and complete_date and 0 <= (complete_date - create_date).days <= 13:
            return True
    return False


def no_freeze_7_days(gamer, quest):
    start_date = quest_start_date(quest)
    if not start_date:
        return False
    if engine.today_for_test() < start_date + timedelta(days=7):
        return False

    for project in get_projects():
        for entry, effective_day in engine.iter_streak_days(getattr(project, 'streaks', [])):
            if entry == engine.STREAK_FREEZE_MARKER and effective_day >= start_date:
                return False
    return True


def write_10000_symbols_in_text(gamer, quest):
    return any(project.get_total_symbols() >= 10000 for project in get_projects())


def finish_text_with_no_freezes(gamer, quest):
    for project in get_projects():
        if getattr(project, 'status', None) != 'завершен':
            continue
        if getattr(project, 'freezes', 0) == 0 and project.get_total_symbols() > 0:
            return True
    return False


def write_notes_14_days_any_text(gamer, quest):
    return any(has_consecutive_dates(get_note_dates(project), 14) for project in get_projects())


def no_freeze_14_days(gamer, quest):
    start_date = quest_start_date(quest)
    if not start_date:
        return False
    if engine.today_for_test() < start_date + timedelta(days=14):
        return False

    for project in get_projects():
        for entry, effective_day in engine.iter_streak_days(getattr(project, 'streaks', [])):
            if entry == engine.STREAK_FREEZE_MARKER and effective_day >= start_date:
                return False
    return True


def write_30000_symbols_total(gamer, quest):
    return sum(project.get_total_symbols() for project in get_projects()) >= 30000


def write_2000_symbols_on_3_days(gamer, quest):
    symbols_by_date = get_symbols_by_date(get_projects())
    productive_days = [day for day, symbols in symbols_by_date.items() if symbols >= 2000]
    return len(productive_days) >= 3


def finish_three_texts(gamer, quest):
    completed_count = sum(1 for project in get_projects() if getattr(project, 'status', None) == 'завершен')
    return completed_count >= 3


def finish_long_text_50000(gamer, quest):
    return any(
        getattr(project, 'status', None) == 'завершен' and project.get_total_symbols() >= 50000
        for project in get_projects()
    )


def complete_text_with_21_day_streak(gamer, quest):
    return any(
        getattr(project, 'status', None) == 'завершен'
        and engine.streak_length(getattr(project, 'streaks', [])) >= 21
        for project in get_projects()
    )


def two_texts_with_7_day_streaks(gamer, quest):
    streaked_projects = [
        project for project in get_projects()
        if engine.streak_length(getattr(project, 'streaks', [])) >= 7
    ]
    return len(streaked_projects) >= 2


def save_5000_coins_no_credit(gamer, quest):
    bank_account = getattr(gamer, 'bank_account', None)
    has_credit = bool(bank_account and bank_account.credit)
    return gamer.get_coins() >= 5000 and not has_credit


def collect_ten_awards(gamer, quest):
    awards = gamer.items.get('Награды', {})
    return sum(count for count in awards.values() if count > 0) >= 10


def write_1000_symbols_today(gamer, quest):
    return any(project.get_added_symbols_today_value() >= 1000 for project in get_projects())


def keep_three_active_projects(gamer, quest):
    active_statuses = {'активен', 'в работе'}
    return sum(1 for project in get_projects() if getattr(project, 'status', None) in active_statuses) >= 3


def finish_short_text_5000(gamer, quest):
    return any(5000 <= project.get_total_symbols() <= 15000 for project in get_completed_projects())


def write_5000_symbols_in_week(gamer, quest):
    today = engine.today_for_test()
    week_start = today - timedelta(days=6)
    total = 0
    for symbols_date, symbols in get_symbols_by_date(get_projects()).items():
        if week_start <= symbols_date <= today:
            total += symbols
    return total >= 5000


def write_1000_symbols_on_5_days(gamer, quest):
    symbols_by_date = get_symbols_by_date(get_projects())
    productive_days = [day for day, symbols in symbols_by_date.items() if symbols >= 1000]
    return len(productive_days) >= 5


def write_30_notes_in_one_text(gamer, quest):
    return any(count_positive_notes(project) >= 30 for project in get_projects())


def write_100000_symbols_total(gamer, quest):
    return sum(project.get_total_symbols() for project in get_projects()) >= 100000


def finish_five_texts(gamer, quest):
    return len(get_completed_projects()) >= 5


def keep_deposit_1000_coins(gamer, quest):
    bank_account = getattr(gamer, 'bank_account', None)
    deposit = getattr(bank_account, 'deposit', None) if bank_account else None
    return bool(deposit and deposit.get_sum() >= 1000)


def return_deposit_with_profit(gamer, quest):
    bank_account = getattr(gamer, 'bank_account', None)
    if not bank_account:
        return False
    for deposit_record in getattr(bank_account, 'deposit_history', []):
        if deposit_record.get('status') == 'returned' and deposit_record.get('interest', 0) > 0:
            return True
    return False


def get_global_streaks():
    data = engine.load_data()
    return data.get('global_streaks', [])


def global_streak_at_least(days_count):
    return engine.streak_length(get_global_streaks()) >= days_count


def global_streak_3_days(gamer, quest):
    return global_streak_at_least(3)


def global_streak_7_days(gamer, quest):
    return global_streak_at_least(7)


def global_streak_14_days(gamer, quest):
    return global_streak_at_least(14)


def global_streak_21_days(gamer, quest):
    return global_streak_at_least(21)


def global_streak_30_days(gamer, quest):
    return global_streak_at_least(30)


def global_streak_60_days(gamer, quest):
    return global_streak_at_least(60)


def global_streak_90_days(gamer, quest):
    return global_streak_at_least(90)


def global_streak_180_days(gamer, quest):
    return global_streak_at_least(180)


def global_streak_365_days(gamer, quest):
    return global_streak_at_least(365)


def global_streak_30_days_no_freezes(gamer, quest):
    streaks = get_global_streaks()
    if engine.streak_length(streaks) < 30:
        return False
    return not any(entry == engine.STREAK_FREEZE_MARKER for entry in streaks)


def get_quests():
    return [
        quest(
            quest_id='reach_level_2',
            name='Первые шаги',
            description='Достигните 2 уровня.',
            reward_coins=50,
            reward_exp=500,
            reward_items=[],
            level=1,
            quest_func='reach_level_2',
        ),
        quest(
            quest_id='save_100_coins',
            name='Финансовая подушка',
            description='Накопите 100 монет на балансе.',
            reward_coins=25,
            reward_exp=300,
            reward_items=[],
            level=1,
            quest_func='save_100_coins',
        ),
        quest(
            quest_id='keep_health_potion',
            name='Аптечка автора',
            description='Получите или купите любое зелье здоровья и держите его в инвентаре.',
            reward_coins=75,
            reward_exp=750,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак заботы о здоровье', 'count': 1},
            ],
            level=2,
            quest_func='keep_health_potion',
        ),
        quest(
            quest_id='restore_full_health',
            name='Полное восстановление',
            description='Восстановите здоровье до 100.',
            reward_coins=60,
            reward_exp=600,
            reward_items=[],
            level=2,
            quest_func='restore_full_health',
        ),
        quest(
            quest_id='activate_positive_buff',
            name='Подготовка к рывку',
            description='Получите любой положительный эффект от предмета или зелья.',
            reward_coins=120,
            reward_exp=1200,
            reward_items=[],
            level=2,
            quest_func='activate_positive_buff',
        ),
        quest(
            quest_id='own_freeze_item',
            name='Запасной день',
            description='Получите предмет "Заморозка" в инвентарь.',
            reward_coins=150,
            reward_exp=1500,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак дисциплины', 'count': 1},
            ],
            level=3,
            quest_func='own_freeze_item',
        ),
        quest(
            quest_id='open_bank_deposit',
            name='Первые инвестиции',
            description='Откройте вклад в банке.',
            reward_coins=200,
            reward_exp=2000,
            reward_items=[
                {'category': 'Награды', 'name': 'Банковский жетон', 'count': 1},
            ],
            level=3,
            quest_func='open_bank_deposit',
        ),
        quest(
            quest_id='keep_no_credit_with_500_coins',
            name='Без долгов',
            description='Накопите 500 монет и не имейте активного кредита.',
            reward_coins=250,
            reward_exp=2500,
            reward_items=[],
            level=4,
            quest_func='keep_no_credit_with_500_coins',
        ),
        quest(
            quest_id='collect_2000_exp',
            name='Стабильная практика',
            description='Накопите 2000 опыта на текущем уровне.',
            reward_coins=300,
            reward_exp=3000,
            reward_items=[],
            level=5,
            quest_func='collect_2000_exp',
        ),
        quest(
            quest_id='collect_five_items',
            name='Коллекционер',
            description='Соберите в инвентаре суммарно 5 предметов, зелий или наград.',
            reward_coins=400,
            reward_exp=4000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак коллекционера', 'count': 1},
            ],
            level=6,
            quest_func='collect_five_items',
        ),
        quest(
            quest_id='write_notes_7_days_any_text',
            name='Неделя записей',
            description='Добавляйте записи не меньше 7 дней подряд в любой текст.',
            reward_coins=500,
            reward_exp=5000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак недельной практики', 'count': 1},
            ],
            level=2,
            quest_func='write_notes_7_days_any_text',
        ),
        quest(
            quest_id='finish_text_in_14_days',
            name='Спринт за две недели',
            description='Завершите любой текст не позже чем через 14 дней после его создания.',
            reward_coins=700,
            reward_exp=7000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак быстрого финала', 'count': 1},
            ],
            level=3,
            quest_func='finish_text_in_14_days',
        ),
        quest(
            quest_id='no_freeze_7_days',
            name='Неделя без заморозки',
            description='После старта квеста продержитесь 7 дней без использования заморозки в проектах.',
            reward_coins=450,
            reward_exp=4500,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак теплого стрика', 'count': 1},
            ],
            level=3,
            quest_func='no_freeze_7_days',
        ),
        quest(
            quest_id='write_10000_symbols_in_text',
            name='Десять тысяч',
            description='Напишите 10000 символов в любом тексте.',
            reward_coins=800,
            reward_exp=8000,
            reward_items=[],
            level=4,
            quest_func='write_10000_symbols_in_text',
        ),
        quest(
            quest_id='finish_text_with_no_freezes',
            name='Чистый финиш',
            description='Завершите любой текст, не использовав в нем ни одной заморозки.',
            reward_coins=900,
            reward_exp=9000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак чистого финиша', 'count': 1},
            ],
            level=5,
            quest_func='finish_text_with_no_freezes',
        ),
        quest(
            quest_id='write_notes_14_days_any_text',
            name='Две недели без провала',
            description='Добавляйте записи 14 дней подряд в любой текст.',
            reward_coins=1200,
            reward_exp=12000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак двух недель', 'count': 1},
            ],
            level=6,
            quest_func='write_notes_14_days_any_text',
        ),
        quest(
            quest_id='no_freeze_14_days',
            name='Без льда',
            description='После старта квеста продержитесь 14 дней без использования заморозки в проектах.',
            reward_coins=1100,
            reward_exp=11000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак без льда', 'count': 1},
            ],
            level=6,
            quest_func='no_freeze_14_days',
        ),
        quest(
            quest_id='write_30000_symbols_total',
            name='Большой объём',
            description='Накопите 30000 написанных символов суммарно по всем текстам.',
            reward_coins=1500,
            reward_exp=15000,
            reward_items=[],
            level=7,
            quest_func='write_30000_symbols_total',
        ),
        quest(
            quest_id='write_2000_symbols_on_3_days',
            name='Три глубоких дня',
            description='Напишите не меньше 2000 символов в каждый из 3 разных дней.',
            reward_coins=1600,
            reward_exp=16000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глубоких дней', 'count': 1},
            ],
            level=7,
            quest_func='write_2000_symbols_on_3_days',
        ),
        quest(
            quest_id='finish_three_texts',
            name='Три финала',
            description='Завершите 3 разных текста.',
            reward_coins=2200,
            reward_exp=22000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак трех финалов', 'count': 1},
            ],
            level=8,
            quest_func='finish_three_texts',
        ),
        quest(
            quest_id='finish_long_text_50000',
            name='Большая форма',
            description='Завершите текст объёмом не меньше 50000 символов.',
            reward_coins=2600,
            reward_exp=26000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак большой формы', 'count': 1},
            ],
            level=8,
            quest_func='finish_long_text_50000',
        ),
        quest(
            quest_id='complete_text_with_21_day_streak',
            name='Финиш марафонца',
            description='Завершите текст со стриком не меньше 21 дня.',
            reward_coins=3200,
            reward_exp=32000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак марафонца', 'count': 1},
            ],
            level=9,
            quest_func='complete_text_with_21_day_streak',
        ),
        quest(
            quest_id='two_texts_with_7_day_streaks',
            name='Две линии огня',
            description='Доведите стрик до 7 дней минимум в двух разных текстах.',
            reward_coins=3000,
            reward_exp=30000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак двух линий', 'count': 1},
            ],
            level=9,
            quest_func='two_texts_with_7_day_streaks',
        ),
        quest(
            quest_id='save_5000_coins_no_credit',
            name='Крепкая экономика',
            description='Накопите 5000 монет и не имейте активного кредита.',
            reward_coins=3500,
            reward_exp=35000,
            reward_items=[],
            level=10,
            quest_func='save_5000_coins_no_credit',
        ),
        quest(
            quest_id='collect_ten_awards',
            name='Зал славы',
            description='Соберите суммарно 10 наград в инвентаре.',
            reward_coins=4000,
            reward_exp=40000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак зала славы', 'count': 1},
            ],
            level=10,
            quest_func='collect_ten_awards',
        ),
        quest(
            quest_id='write_1000_symbols_today',
            name='Тысяча за день',
            description='Напишите не меньше 1000 символов за один день в любом тексте.',
            reward_coins=180,
            reward_exp=1800,
            reward_items=[],
            level=2,
            quest_func='write_1000_symbols_today',
        ),
        quest(
            quest_id='keep_three_active_projects',
            name='Три фронта',
            description='Держите 3 активных текста одновременно.',
            reward_coins=350,
            reward_exp=3500,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак трех фронтов', 'count': 1},
            ],
            level=3,
            quest_func='keep_three_active_projects',
        ),
        quest(
            quest_id='finish_short_text_5000',
            name='Короткая победа',
            description='Завершите текст объёмом от 5000 до 15000 символов.',
            reward_coins=650,
            reward_exp=6500,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак короткой победы', 'count': 1},
            ],
            level=4,
            quest_func='finish_short_text_5000',
        ),
        quest(
            quest_id='write_5000_symbols_in_week',
            name='Плотная неделя',
            description='Напишите суммарно 5000 символов за последние 7 дней.',
            reward_coins=900,
            reward_exp=9000,
            reward_items=[],
            level=5,
            quest_func='write_5000_symbols_in_week',
        ),
        quest(
            quest_id='write_1000_symbols_on_5_days',
            name='Пять сильных дней',
            description='Напишите не меньше 1000 символов в каждый из 5 разных дней.',
            reward_coins=1400,
            reward_exp=14000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак пяти сильных дней', 'count': 1},
            ],
            level=6,
            quest_func='write_1000_symbols_on_5_days',
        ),
        quest(
            quest_id='write_30_notes_in_one_text',
            name='Дневник рукописи',
            description='Добавьте 30 записей с положительным приростом в один текст.',
            reward_coins=1800,
            reward_exp=18000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак дневника рукописи', 'count': 1},
            ],
            level=7,
            quest_func='write_30_notes_in_one_text',
        ),
        quest(
            quest_id='keep_deposit_1000_coins',
            name='Серьёзный вклад',
            description='Держите активный банковский вклад на сумму не меньше 1000 монет.',
            reward_coins=2000,
            reward_exp=20000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак серьезного вклада', 'count': 1},
            ],
            level=7,
            quest_func='keep_deposit_1000_coins',
        ),
        quest(
            quest_id='return_deposit_with_profit',
            name='Проценты получены',
            description='Закройте вклад в срок и получите проценты.',
            reward_coins=2800,
            reward_exp=28000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак умного вклада', 'count': 1},
            ],
            level=8,
            quest_func='return_deposit_with_profit',
        ),
        quest(
            quest_id='finish_five_texts',
            name='Пять завершений',
            description='Завершите 5 разных текстов.',
            reward_coins=5200,
            reward_exp=52000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак пяти завершений', 'count': 1},
            ],
            level=11,
            quest_func='finish_five_texts',
        ),
        quest(
            quest_id='write_100000_symbols_total',
            name='Сто тысяч',
            description='Накопите 100000 написанных символов суммарно по всем текстам.',
            reward_coins=7000,
            reward_exp=70000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак ста тысяч', 'count': 1},
            ],
            level=12,
            quest_func='write_100000_symbols_total',
        ),
        quest(
            quest_id='global_streak_3_days',
            name='Глобальный старт',
            description='Продержите глобальный стрик 3 дня.',
            reward_coins=300,
            reward_exp=3000,
            reward_items=[],
            level=2,
            quest_func='global_streak_3_days',
        ),
        quest(
            quest_id='global_streak_7_days',
            name='Глобальная неделя',
            description='Продержите глобальный стрик 7 дней.',
            reward_coins=700,
            reward_exp=7000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобальной недели', 'count': 1},
            ],
            level=3,
            quest_func='global_streak_7_days',
        ),
        quest(
            quest_id='global_streak_14_days',
            name='Две глобальные недели',
            description='Продержите глобальный стрик 14 дней.',
            reward_coins=1400,
            reward_exp=14000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобальных двух недель', 'count': 1},
            ],
            level=4,
            quest_func='global_streak_14_days',
        ),
        quest(
            quest_id='global_streak_21_days',
            name='Глобальная привычка',
            description='Продержите глобальный стрик 21 день.',
            reward_coins=2100,
            reward_exp=21000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобальной привычки', 'count': 1},
            ],
            level=5,
            quest_func='global_streak_21_days',
        ),
        quest(
            quest_id='global_streak_30_days',
            name='Глобальный месяц',
            description='Продержите глобальный стрик 30 дней.',
            reward_coins=3000,
            reward_exp=30000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобального месяца', 'count': 1},
            ],
            level=6,
            quest_func='global_streak_30_days',
        ),
        quest(
            quest_id='global_streak_30_days_no_freezes',
            name='Чистый глобальный месяц',
            description='Продержите глобальный стрик 30 дней без заморозок.',
            reward_coins=4500,
            reward_exp=45000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак чистого глобального месяца', 'count': 1},
            ],
            level=7,
            quest_func='global_streak_30_days_no_freezes',
        ),
        quest(
            quest_id='global_streak_60_days',
            name='Глобальный сезон',
            description='Продержите глобальный стрик 60 дней.',
            reward_coins=6000,
            reward_exp=60000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобального сезона', 'count': 1},
            ],
            level=8,
            quest_func='global_streak_60_days',
        ),
        quest(
            quest_id='global_streak_90_days',
            name='Глобальный квартал',
            description='Продержите глобальный стрик 90 дней.',
            reward_coins=9000,
            reward_exp=90000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобального квартала', 'count': 1},
            ],
            level=9,
            quest_func='global_streak_90_days',
        ),
        quest(
            quest_id='global_streak_180_days',
            name='Глобальное полугодие',
            description='Продержите глобальный стрик 180 дней.',
            reward_coins=18000,
            reward_exp=180000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобального полугодия', 'count': 1},
            ],
            level=10,
            quest_func='global_streak_180_days',
        ),
        quest(
            quest_id='global_streak_365_days',
            name='Глобальный год',
            description='Продержите глобальный стрик 365 дней.',
            reward_coins=36500,
            reward_exp=365000,
            reward_items=[
                {'category': 'Награды', 'name': 'Знак глобального года', 'count': 1},
            ],
            level=12,
            quest_func='global_streak_365_days',
        ),
    ]
