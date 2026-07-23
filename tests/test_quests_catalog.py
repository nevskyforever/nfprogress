from datetime import datetime, timedelta

import engine
import gama_quests
import game
import game_data


NEW_QUEST_IDS = {
    'write_1000_symbols_today',
    'keep_three_active_projects',
    'finish_short_text_5000',
    'write_5000_symbols_in_week',
    'write_1000_symbols_on_5_days',
    'write_30_notes_in_one_text',
    'keep_deposit_1000_coins',
    'return_deposit_with_profit',
    'finish_five_texts',
    'write_100000_symbols_total',
}


def test_quest_catalog_has_unique_ids_and_valid_functions():
    quests = gama_quests.get_quests()
    quest_ids = [quest.quest_id for quest in quests]

    assert NEW_QUEST_IDS.issubset(set(quest_ids))
    assert len(quest_ids) == len(set(quest_ids))
    for quest in quests:
        assert callable(getattr(gama_quests, quest.quest_func))


def test_week_symbol_quest_counts_last_seven_days(monkeypatch):
    today = engine.today_for_test()
    project = engine.Project(name='Book')
    project.notes = [
        engine.Note(1200, 1200, 0, datetime.combine(today - timedelta(days=6), datetime.min.time())),
        engine.Note(2600, 1400, 0, datetime.combine(today - timedelta(days=3), datetime.min.time())),
        engine.Note(5100, 2500, 0, datetime.combine(today, datetime.min.time())),
        engine.Note(7100, 2000, 0, datetime.combine(today - timedelta(days=8), datetime.min.time())),
    ]

    monkeypatch.setattr(gama_quests.engine, 'load_data', lambda: {'projects': {'Book': project}})

    assert gama_quests.write_5000_symbols_in_week(game.Gamer(), None) is True


def test_bank_quests_check_active_and_returned_deposits():
    gamer = game.Gamer(level=8)
    gamer.bank_account = game_data.BankAccount()

    gamer.bank_account.deposit = game_data.Deposit(1000, 10, 1)
    assert gama_quests.keep_deposit_1000_coins(gamer, None) is True

    gamer.bank_account.deposit_history = [
        {'sum': 1000, 'interest': 30, 'status': 'returned'},
    ]
    assert gama_quests.return_deposit_with_profit(gamer, None) is True


def test_quest_reward_buffs_are_permanent_universal_and_thematic():
    quests = {quest.quest_id: quest for quest in gama_quests.get_quests()}

    assert quests['save_100_coins'].reward_buffs[0].target_cf == 'coins'
    assert quests['write_10000_symbols_in_text'].reward_buffs[0].target_cf == 'exp'
    assert quests['restore_full_health'].reward_buffs[0].target_cf == 'health_recovery'
    assert quests['no_freeze_7_days'].reward_buffs == []

    buff_names = set()
    for quest in quests.values():
        for buff in quest.reward_buffs:
            assert buff.duration_minutes is None
            assert buff.stackable is True
            buff_names.add(buff.name)

    assert buff_names == {
        '⭐️ Квестовая специализация: опыт',
        '⭐️ Квестовая специализация: монеты',
        '⭐️ Квестовая специализация: восстановление',
    }


def test_quest_reward_buffs_merge_instead_of_duplicating(monkeypatch):
    monkeypatch.setattr(game.Gamer, 'save', lambda self: None)
    gamer = game.Gamer(level=3)
    quests = {quest.quest_id: quest for quest in gama_quests.get_quests()}
    first = quests['save_100_coins']
    second = quests['keep_no_credit_with_500_coins']
    expected_value = first.reward_buffs[0].value + second.reward_buffs[0].value

    first.complete(gamer)
    second.complete(gamer)

    quest_coin_buffs = [
        buff for buff in gamer.buffs
        if buff.name == '⭐️ Квестовая специализация: монеты'
    ]
    assert len(quest_coin_buffs) == 1
    assert quest_coin_buffs[0].duration_minutes is None
    assert quest_coin_buffs[0].value == expected_value


def test_existing_quest_awards_in_inventory_provide_merged_buffs(monkeypatch):
    monkeypatch.setattr(game.Gamer, 'save', lambda self: None)
    gamer = game.Gamer(level=3)
    gamer.update_cf()
    gamer.items = {
        'Предметы': {},
        'Зелья': {},
        'Награды': {
            'Знак недельной практики': 3,
            'Знак быстрого финала': 1,
            'Банковский жетон': 1,
            'Знак теплого стрика': 1,
            'Знак глобальной недели': 1,
        },
    }

    inventory_buffs = {
        buff.target_cf: (buff, stacks)
        for buff, stacks in gamer.get_inventory_buffs()
        if buff.name.startswith('⭐️ Квестовая специализация:')
    }

    assert set(inventory_buffs) == {'exp', 'coins', 'health_recovery'}
    assert inventory_buffs['exp'][0].value == 0.025
    assert inventory_buffs['exp'][1] == 4
    assert inventory_buffs['coins'][0].value == 0.025
    assert inventory_buffs['coins'][1] == 1
    assert inventory_buffs['health_recovery'][0].value == 0.025
    assert inventory_buffs['health_recovery'][1] == 2

    gamer.apply_buffs_to_cf(save=False)
    assert gamer.get_cf_value('exp') == game.game_data.cf_exp[3] + 0.1
    assert gamer.get_cf_value('coins') == game.game_data.cf_coins[3] + 0.025
    assert gamer.get_cf_value('health_recovery') == 0.05


def test_item_buffs_start_with_item_emoji():
    items_with_buffs = {
        game_data.crown_of_the_first_era: '👑 ',
        game_data.millionaires_pen: '💎 ',
        game_data.exp_potion_1hrs: '🧪⚡️ ',
        game_data.super_exp_potion_1hrs: '🧪⚡️ ',
        game_data.coin_potion_1hrs: '🧪⚡️ ',
        game_data.health_care_badge: '⭐️ ',
    }

    for item, emoji in items_with_buffs.items():
        assert all(buff.name.startswith(emoji) for buff in item.get_buffs())


def test_legacy_active_buff_names_receive_item_emoji():
    gamer = game.Gamer()
    gamer.buffs = [
        game_data.Buff('Квестовая специализация: опыт', '', game_data.Buff.POSITIVE, 'exp', 0.1),
        game_data.Buff('Бустер опыта', '', game_data.Buff.POSITIVE, 'exp', 1),
    ]

    assert gamer.normalize_buff_names() is True
    assert [buff.name for buff in gamer.buffs] == [
        '⭐️ Квестовая специализация: опыт',
        '🧪⚡️ Бустер опыта',
    ]
