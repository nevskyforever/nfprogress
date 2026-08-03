from datetime import datetime, timedelta

import engine
import game


def make_gamer(monkeypatch):
    gamer = game.Gamer()
    monkeypatch.setattr(gamer, 'save', lambda: None)
    gamer.daily_challenge = {
        'date': engine.today_for_test().isoformat(),
        'target': 1000,
        'progress': 0,
        'completed': False,
    }
    return gamer


def test_daily_challenge_rewards_only_once(monkeypatch):
    gamer = make_gamer(monkeypatch)

    first_messages = gamer.record_motivation_progress(1000)
    coins_after_completion = gamer.coins
    exp_after_completion = gamer.exp
    second_messages = gamer.record_motivation_progress(500)

    assert first_messages
    assert second_messages == []
    assert gamer.daily_challenge['completed'] is True
    assert gamer.coins == coins_after_completion
    assert gamer.exp == exp_after_completion
    assert gamer.inspiration == 13


def test_successful_session_advances_session_challenge(monkeypatch):
    gamer = make_gamer(monkeypatch)
    ok, _ = gamer.select_weekly_challenge('sessions', save=False)
    assert ok is True
    ok, _ = gamer.start_writing_session(25, 600, 'Продолжить черновик', save=False)
    assert ok is True

    gamer.record_motivation_progress(600)
    ok, message = gamer.finish_writing_session(save=False)

    assert ok is True
    assert 'Сессия завершена' in message
    assert gamer.writing_session is None
    assert gamer.weekly_challenge['progress'] == 1


def test_session_modes_validate_duration_and_intention(monkeypatch):
    gamer = make_gamer(monkeypatch)

    sprint_ok, _ = gamer.start_writing_session(
        25, 100, 'Написать новую сцену', mode_key='sprint', save=False
    )
    deep_ok, _ = gamer.start_writing_session(
        25, 100, 'Написать новую сцену', mode_key='deep', save=False
    )
    editing_ok, _ = gamer.start_writing_session(
        25, 100, 'Написать новую сцену', mode_key='editing', save=False
    )

    assert sprint_ok is False
    assert deep_ok is False
    assert editing_ok is False


def test_gold_session_gets_grade_and_early_finish_bonus(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)
    gamer.record_motivation_progress(150)

    ok, message = gamer.finish_writing_session(save=False)

    assert ok is True
    assert 'Золото' in message
    assert 'досрочный' in message
    assert gamer.coins == 35.8
    assert gamer.exp == 357.5
    assert gamer.writing_session_history[-1]['grade'] == 'gold'


def test_sprint_mode_applies_mode_reward(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.start_writing_session(
        15, 100, 'Написать новую сцену', mode_key='sprint', save=False
    )
    gamer.record_motivation_progress(100)

    gamer.finish_writing_session(save=False)

    assert gamer.coins == 28.8
    assert gamer.exp == 287.5
    assert gamer.writing_session_history[-1]['mode'] == 'sprint'


def test_session_streak_and_history_track_results(monkeypatch):
    gamer = make_gamer(monkeypatch)
    for _ in range(2):
        gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)
        gamer.record_motivation_progress(100)
        gamer.finish_writing_session(save=False)

    gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)
    gamer.finish_writing_session(save=False)

    assert gamer.writing_session_streak == 0
    assert len(gamer.writing_session_history) == 3
    assert gamer.writing_session_history[-1]['successful'] is False


def test_session_history_keeps_last_twenty_entries(monkeypatch):
    gamer = make_gamer(monkeypatch)
    session = {
        'mode': 'flow', 'intention': 'Продолжить черновик',
        'duration_minutes': 25, 'target_symbols': 100, 'progress': 100,
    }

    for index in range(25):
        current = dict(session, progress=100 + index)
        gamer._record_writing_session_result(current, 'bronze', True)

    assert len(gamer.writing_session_history) == 20
    assert gamer.writing_session_history[0]['progress'] == 105


def test_ritualist_ability_preserves_session_streak_on_failure(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.level = 3
    gamer.specialization = 'ritualist'
    gamer.writing_session_streak = 4
    gamer.activate_specialization_ability(save=False)
    gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)

    ok, message = gamer.finish_writing_session(save=False)

    assert ok is False
    assert gamer.writing_session_streak == 4
    assert 'сохранила серию' in message


def test_unsuccessful_session_has_no_penalty(monkeypatch):
    gamer = make_gamer(monkeypatch)
    initial_health = gamer.health
    initial_coins = gamer.coins
    gamer.start_writing_session(15, 1000, 'Составить план', save=False)

    ok, message = gamer.finish_writing_session(save=False)

    assert ok is False
    assert 'штрафа нет' in message
    assert gamer.health == initial_health
    assert gamer.coins == initial_coins


def test_flow_ink_bonus_is_spent_by_successful_session(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.session_reward_bonus = 0.25
    gamer.start_writing_session(15, 100, 'Написать новую сцену', save=False)
    gamer.record_motivation_progress(100)

    ok, _ = gamer.finish_writing_session(save=False)

    assert ok is True
    assert gamer.session_reward_bonus == 0
    assert gamer.exp == 312.5


def test_inspiration_increases_writing_rewards(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.inspiration = 50

    gamer.give_symbol_bonus(100)

    assert gamer.coins == 10.5
    assert gamer.exp == 525


def test_creative_surge_spends_inspiration_on_next_text(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.inspiration = 30

    ok, _ = gamer.activate_inspiration_ability('creative_surge', save=False)
    gamer.give_symbol_bonus(100)

    assert ok is True
    assert gamer.writing_reward_bonus == 0
    assert gamer.inspiration == 0.2
    assert gamer.coins == 12.5
    assert gamer.exp == 625


def test_session_spark_rewards_next_successful_session(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.inspiration = 25
    gamer.activate_inspiration_ability('session_spark', save=False)
    gamer.start_writing_session(15, 100, 'Продолжить черновик', save=False)
    gamer.record_motivation_progress(100)

    ok, _ = gamer.finish_writing_session(save=False)

    assert ok is True
    assert gamer.session_reward_bonus == 0
    assert gamer.coins == 31.3
    assert gamer.exp == 312.5


def test_challenge_focus_rewards_next_completed_challenge(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.inspiration = 40
    gamer.daily_challenge['target'] = 100
    gamer.activate_inspiration_ability('challenge_focus', save=False)

    messages = gamer.record_motivation_progress(100)

    assert messages
    assert gamer.challenge_reward_bonus == 0
    assert gamer.coins == 6.3
    assert gamer.exp == 62.5


def test_inspiration_ability_requires_resource_and_free_effect_slot(monkeypatch):
    gamer = make_gamer(monkeypatch)

    ok, message = gamer.activate_inspiration_ability('creative_surge', save=False)
    assert ok is False
    assert 'Недостаточно вдохновения' in message

    gamer.inspiration = 100
    gamer.writing_reward_bonus = 0.25
    ok, message = gamer.activate_inspiration_ability('creative_surge', save=False)
    assert ok is False
    assert 'уже активен' in message
    assert gamer.inspiration == 100


def test_adaptive_target_uses_recent_productive_days(monkeypatch):
    class Note:
        def __init__(self, day, symbols):
            self.day = day
            self.symbols = symbols

        def get_date_create(self):
            return self.day

        def get_added_symbols(self):
            return self.symbols

    today = datetime(2026, 8, 3).date()
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    project = type('Project', (), {
        'enable_stages': False,
        'notes': [Note(today.replace(day=1), 2000), Note(today.replace(day=2), 3000)],
    })()

    target = game.Gamer.calculate_adaptive_daily_target({'projects': {'Роман': project}})

    assert target == 2000


def test_migration_adds_motivation_state_to_old_gamer(monkeypatch):
    gamer = make_gamer(monkeypatch)
    for attribute in (
        'inspiration', 'daily_challenge', 'weekly_challenge',
        'daily_challenge_options', 'daily_challenge_history',
        'productive_actions_since_event', 'pending_creative_event',
        'creative_event_history',
        'writing_session', 'writing_session_streak', 'writing_session_history',
        'session_streak_shields', 'session_grade_boosts',
        'writing_reward_bonus', 'session_reward_bonus',
        'challenge_reward_bonus', 'specialization',
        'manuscript_reward_bonus',
        'specialization_changed_at', 'specialization_mastery', 'manuscript_journeys',
        'specialization_ability_ready_at', 'specialization_ability_effects',
        'cabinet_relics',
    ):
        delattr(gamer, attribute)

    gamer.migrate()

    assert gamer.inspiration == 0
    assert gamer.daily_challenge is None
    assert gamer.daily_challenge_options == []
    assert gamer.daily_challenge_history == []
    assert gamer.productive_actions_since_event == 0
    assert gamer.pending_creative_event is None
    assert gamer.creative_event_history == []
    assert gamer.weekly_challenge is None
    assert gamer.writing_session is None
    assert gamer.writing_session_streak == 0
    assert gamer.writing_session_history == []
    assert gamer.session_streak_shields == 0
    assert gamer.session_grade_boosts == 0
    assert gamer.writing_reward_bonus == 0
    assert gamer.session_reward_bonus == 0
    assert gamer.challenge_reward_bonus == 0
    assert gamer.manuscript_reward_bonus == 0
    assert gamer.specialization is None
    assert gamer.specialization_changed_at is None
    assert gamer.specialization_mastery == {}
    assert gamer.specialization_ability_ready_at == {}
    assert gamer.specialization_ability_effects == {}
    assert gamer.manuscript_journeys == {}
    assert gamer.cabinet_relics == []


def test_specialization_unlock_and_change_cooldown(monkeypatch):
    gamer = make_gamer(monkeypatch)
    ok, message = gamer.select_specialization('marathoner', save=False)
    assert ok is False
    assert '3 уровне' in message

    gamer.level = 3
    ok, _ = gamer.select_specialization('marathoner', save=False)
    assert ok is True
    ok, message = gamer.select_specialization('ritualist', save=False)
    assert ok is False
    assert '14 дн.' in message

    changed_at = engine.today_for_test()
    monkeypatch.setattr(
        engine,
        'today_for_test',
        lambda: changed_at + timedelta(days=14),
    )
    ok, _ = gamer.select_specialization('ritualist', save=False)
    assert ok is True


def test_specialization_mastery_increases_rank_and_bonus(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'marathoner'
    gamer.daily_challenge['target'] = 100000

    for _ in range(3):
        gamer.give_symbol_bonus(3000)

    assert gamer.specialization_mastery['marathoner'] == 3
    assert gamer.specialization_mastery_rank() == 2
    assert gamer.get_specialization_bonus() == 0.175


def test_profile_actions_advance_matching_mastery(monkeypatch):
    ritualist = make_gamer(monkeypatch)
    ritualist.specialization = 'ritualist'
    ritualist.start_writing_session(15, 100, 'Продолжить черновик', save=False)
    ritualist.record_motivation_progress(100)
    ritualist.finish_writing_session(save=False)

    explorer = make_gamer(monkeypatch)
    explorer.specialization = 'explorer'
    explorer.daily_challenge['target'] = 100
    explorer.record_motivation_progress(100)

    assert ritualist.specialization_mastery['ritualist'] == 1
    assert explorer.specialization_mastery['explorer'] == 1


def test_marathoner_active_ability_boosts_matching_entry(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.level = 3
    gamer.specialization = 'marathoner'
    gamer.daily_challenge['target'] = 100000

    ok, _ = gamer.activate_specialization_ability(save=False)
    gamer.give_symbol_bonus(3000)

    assert ok is True
    assert gamer.coins == 448.5
    assert gamer.exp == 22425
    assert 'marathoner' not in gamer.specialization_ability_effects
    assert gamer.specialization_ability_remaining_seconds() > 0


def test_finisher_active_ability_boosts_next_milestones(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.level = 3
    gamer.specialization = 'finisher'
    gamer.activate_specialization_ability(save=False)

    gamer.advance_manuscript_journey('novel', 10)

    assert gamer.coins == 42.3
    assert gamer.exp == 325
    assert 'finisher' not in gamer.specialization_ability_effects


def test_explorer_active_ability_replaces_weekly_challenge(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.level = 3
    gamer.specialization = 'explorer'
    gamer.select_weekly_challenge('symbols', save=False)
    gamer.weekly_challenge['progress'] = 500

    ok, _ = gamer.activate_specialization_ability(save=False)

    assert ok is True
    assert gamer.weekly_challenge['key'] == 'days'
    assert gamer.weekly_challenge['progress'] == 0
    assert gamer.specialization_ability_remaining_seconds() > 0


def test_specialization_ability_rejects_use_during_cooldown(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.level = 3
    gamer.specialization = 'ritualist'
    gamer.activate_specialization_ability(save=False)
    gamer.start_writing_session(15, 100, 'Продолжить черновик', save=False)
    gamer.record_motivation_progress(100)
    gamer.finish_writing_session(save=False)

    ok, message = gamer.activate_specialization_ability(save=False)

    assert ok is False
    assert 'восстанавливается' in message


def test_marathoner_rewards_large_entries(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'marathoner'
    gamer.daily_challenge['target'] = 100000

    gamer.give_symbol_bonus(3000)

    assert gamer.coins == 345
    assert gamer.exp == 17250


def test_editor_rewards_editorial_session(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'editor'
    gamer.start_writing_session(15, 100, 'Отредактировать текст', save=False)
    gamer.record_motivation_progress(100)

    ok, _ = gamer.finish_writing_session(save=False)

    assert ok is True
    assert gamer.coins == 31.3
    assert gamer.exp == 312.5
    assert gamer.specialization_mastery['editor'] == 1


def test_editorial_session_advances_editorial_week(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.select_weekly_challenge('editing', save=False)
    gamer.start_writing_session(15, 100, 'Отредактировать текст', save=False)
    gamer.record_motivation_progress(100)

    ok, _ = gamer.finish_writing_session(save=False)

    assert ok is True
    assert gamer.weekly_challenge['progress'] == 1


def test_manuscript_bonus_is_spent_on_next_milestones(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.manuscript_reward_bonus = 0.25

    messages = gamer.advance_manuscript_journey('novel', 25)

    assert len(messages) >= 2
    assert gamer.manuscript_reward_bonus == 0
    assert gamer.exp == 937.5
    assert gamer.coins == 93.8


def test_extended_cabinet_unlocks_multi_project_relics(monkeypatch):
    gamer = make_gamer(monkeypatch)

    for project_key in ('one', 'two', 'three'):
        gamer.advance_manuscript_journey(project_key, 100)

    assert 'triple_map' in gamer.cabinet_relics
    assert 'finished_shelf' in gamer.cabinet_relics


def test_finisher_increases_completion_reward(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'finisher'

    gamer.give_complete_bonus('Complete', 1000, project_name='Роман')

    assert gamer.coins == 240
    assert gamer.exp == 24000
    assert gamer.specialization_mastery['finisher'] == 3


def test_explorer_increases_daily_challenge_reward(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.specialization = 'explorer'

    gamer.record_motivation_progress(1000)

    assert gamer.coins == 60
    assert gamer.exp == 600


def test_session_countdown_uses_wall_clock(monkeypatch):
    gamer = make_gamer(monkeypatch)
    current_time = [datetime(2026, 8, 3, 12, 0, 0)]
    monkeypatch.setattr(game, 'get_session_now', lambda: current_time[0])
    gamer.start_writing_session(15, 1000, 'Продолжить черновик', save=False)

    assert gamer.writing_session_remaining_seconds() == 900
    current_time[0] += timedelta(seconds=1)
    assert gamer.writing_session_remaining_seconds() == 899


def test_legacy_session_switches_from_frozen_test_time(monkeypatch):
    gamer = make_gamer(monkeypatch)
    wall_time = datetime(2026, 8, 3, 15, 30, 0)
    monkeypatch.setattr(game, 'get_session_now', lambda: wall_time)
    gamer.writing_session = {
        'started_at': datetime(2026, 8, 3, 10, 0, 0),
        'duration_minutes': 25,
        'target_symbols': 1000,
        'progress': 300,
        'intention': 'Продолжить черновик',
    }

    gamer.normalize_motivation()

    assert gamer.writing_session['clock_source'] == 'wall'
    assert gamer.writing_session['started_at'] == wall_time
    assert gamer.writing_session['progress'] == 300


def test_ui_session_timer_refreshes_label_every_second():
    from types import SimpleNamespace

    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    from game_UI import GameMenuController

    class StatusLabel:
        def __init__(self):
            self.values = []

        def setText(self, value):
            self.values.append(value)

    class SessionGamer:
        writing_session = {
            'progress': 0,
            'target_symbols': 1000,
            'intention': 'Продолжить черновик',
        }

        def __init__(self):
            self.calls = 0

        def writing_session_remaining_seconds(self):
            self.calls += 1
            return 901 - self.calls

    app = QCoreApplication.instance() or QCoreApplication([])
    label = StatusLabel()
    controller = GameMenuController.__new__(GameMenuController)
    controller.ui = SimpleNamespace(
        centralwidget=None,
        writing_session_status=label,
    )
    controller.gamer = SessionGamer()
    controller.update_writing_session_clock()
    controller.setup_writing_session_timer()

    loop = QEventLoop()
    QTimer.singleShot(1150, loop.quit)
    loop.exec()
    controller.writing_session_timer.stop()

    assert app is not None
    assert len(label.values) >= 2
    assert '15:00' in label.values[0]
    assert '14:59' in label.values[-1]


def test_manuscript_journey_rewards_crossed_milestones_once(monkeypatch):
    gamer = make_gamer(monkeypatch)

    messages = gamer.advance_manuscript_journey('Роман', 52)
    coins_after_first_award = gamer.coins
    exp_after_first_award = gamer.exp
    repeated_messages = gamer.advance_manuscript_journey('Роман', 52)

    assert len(messages) == 5
    assert repeated_messages == []
    assert gamer.manuscript_journeys['Роман'] == [10, 25, 50]
    assert coins_after_first_award == 175
    assert exp_after_first_award == 1750
    assert gamer.coins == coins_after_first_award
    assert gamer.exp == exp_after_first_award
    assert gamer.cabinet_relics == ['ink_candle', 'plot_map']


def test_manuscript_journey_status_and_rename(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.advance_manuscript_journey('Черновик', 26)

    reached, upcoming = gamer.get_manuscript_journey_status(26)
    renamed = gamer.rename_manuscript_journey(
        'Черновик', 'Новая рукопись', save=False
    )

    assert reached['name'] == 'Первые главы'
    assert upcoming['progress'] == 50
    assert renamed is True
    assert 'Черновик' not in gamer.manuscript_journeys
    assert gamer.manuscript_journeys['Новая рукопись'] == [10, 25]


def test_cabinet_relics_unlock_from_manuscript_achievements(monkeypatch):
    gamer = make_gamer(monkeypatch)

    gamer.advance_manuscript_journey('Роман', 100)
    gamer.advance_manuscript_journey('Повесть', 25)
    messages = gamer.advance_manuscript_journey('Рассказ', 25)

    assert gamer.cabinet_relics == [
        'ink_candle', 'plot_map', 'first_binding', 'turning_quill',
        'final_lamp', 'chapter_shelf',
    ]
    assert any('Полка первых глав' in message for message in messages)


def test_cabinet_relics_define_card_text():
    for relic in game.CABINET_RELICS.values():
        assert relic['name']
        assert relic['description']
        assert relic['condition']
        assert relic['effect_description']
        assert relic['bonus'] > 0


def test_cabinet_relics_apply_writing_bonus(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.daily_challenge['target'] = 100000
    gamer.cabinet_relics = ['ink_candle', 'triple_map']

    gamer.give_symbol_bonus(100)

    assert gamer.coins == 10.3
    assert gamer.exp == 515


def test_cabinet_sets_unlock_and_apply_bonus(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.cabinet_relics = list(game.CABINET_RELICS)

    unlocked_sets = gamer.get_unlocked_cabinet_sets()
    inspiration = gamer.add_inspiration(10)

    assert unlocked_sets == ['manuscript_path', 'authors_library']
    assert gamer.get_cabinet_bonus('writing') == 0.06
    assert inspiration == 13


def test_cabinet_relic_progress_counts_qualifying_projects(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.manuscript_journeys = {
        'one': [10, 25, 50],
        'two': [10, 25],
    }

    assert gamer.cabinet_relic_progress('chapter_shelf') == (2, 3)


def test_daily_challenge_offers_three_different_options(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.daily_challenge = None

    daily = gamer.ensure_daily_challenge(target=1200)

    assert len(gamer.daily_challenge_options) == 3
    assert len({option['type'] for option in gamer.daily_challenge_options}) == 3
    assert {option['difficulty'] for option in gamer.daily_challenge_options} == {
        'easy', 'normal', 'hard'
    }
    assert daily == gamer.daily_challenge_options[0]


def test_malformed_daily_challenge_is_rebuilt(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.daily_challenge['target'] = 'не число'
    gamer.daily_challenge_options = [{'type': 'unknown', 'target': -1}]

    daily = gamer.ensure_daily_challenge(target=900)

    assert daily['target'] > 0
    assert daily['type'] in game.DAILY_CHALLENGE_TYPES
    assert len(gamer.daily_challenge_options) == 3


def test_daily_challenge_can_be_changed_for_inspiration(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.daily_challenge = None
    gamer.inspiration = 30
    gamer.ensure_daily_challenge(target=1000)

    ok, message = gamer.select_daily_challenge_option(1, save=False)

    assert ok is True
    assert 'новая цель' in message
    assert gamer.inspiration == 15
    assert gamer.daily_challenge == gamer.daily_challenge_options[1]


def test_session_daily_challenge_advances_on_success(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.daily_challenge = {
        'date': engine.today_for_test().isoformat(),
        'option_id': 'sessions:normal',
        'type': 'sessions',
        'difficulty': 'normal',
        'target': 1,
        'progress': 0,
        'completed': False,
        'reward_coins': 100,
        'reward_exp': 400,
    }
    gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)
    gamer.record_motivation_progress(100)

    ok, message = gamer.finish_writing_session(save=False)

    assert ok is True
    assert 'Цель дня выполнена' in message
    assert gamer.daily_challenge['completed'] is True


def test_creative_event_appears_after_five_productive_actions(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.daily_challenge['target'] = 100000

    for _ in range(5):
        gamer.record_motivation_progress(1000)

    assert gamer.pending_creative_event == 'unexpected_idea'
    assert gamer.productive_actions_since_event == 0


def test_safe_creative_event_grants_reward(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.pending_creative_event = 'unexpected_idea'

    ok, message = gamer.resolve_creative_event('safe', save=False)

    assert ok is True
    assert 'Получено 6 вдохновения' in message
    assert gamer.inspiration == 6
    assert gamer.pending_creative_event is None
    assert gamer.creative_event_history[-1]['success'] is True


def test_failed_risky_creative_event_records_result(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.inspiration = 20
    gamer.pending_creative_event = 'second_wind'
    monkeypatch.setattr(game.random, 'random', lambda: 1.0)

    ok, message = gamer.resolve_creative_event('risk', save=False)

    assert ok is True
    assert 'Потеряно 8 вдохновения' in message
    assert gamer.inspiration == 12
    assert gamer.creative_event_history[-1]['success'] is False


def test_session_streak_shield_is_consumed_on_failure(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.writing_session_streak = 4
    gamer.session_streak_shields = 1
    gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)

    ok, message = gamer.finish_writing_session(save=False)

    assert ok is False
    assert gamer.writing_session_streak == 4
    assert gamer.session_streak_shields == 0
    assert 'Нить ритуала' in message


def test_quality_medal_upgrades_successful_session_grade(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.session_grade_boosts = 1
    gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)
    gamer.record_motivation_progress(100)

    ok, message = gamer.finish_writing_session(save=False)

    assert ok is True
    assert gamer.writing_session_history[-1]['grade'] == 'silver'
    assert gamer.session_grade_boosts == 0
    assert 'Медаль качества' in message


def test_quality_medal_waits_when_session_is_already_gold(monkeypatch):
    gamer = make_gamer(monkeypatch)
    gamer.session_grade_boosts = 1
    gamer.start_writing_session(25, 100, 'Продолжить черновик', save=False)
    gamer.record_motivation_progress(150)

    gamer.finish_writing_session(save=False)

    assert gamer.writing_session_history[-1]['grade'] == 'gold'
    assert gamer.session_grade_boosts == 1
