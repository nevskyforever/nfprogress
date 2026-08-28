from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest

import engine
import game
import game_data
from nfprogress.core.errors import ConflictError, NotFoundError, ValidationError
from nfprogress.core.services.game import GameService
from nfprogress.core.storage import PickleRepository


@pytest.fixture
def game_context(tmp_path):
    repository = PickleRepository(tmp_path)
    project = engine.Project(name='Роман', goal=1000, total_symbols=250)
    stage = engine.Stage(
        name='Черновик',
        goal=500,
        total_symbols=100,
        parent_project_name=project.name,
    )
    project.enable_stages = True
    project.stages = [stage]
    data = repository.read_projects()
    data['projects'] = {project.name: project}
    repository.write_projects(data)
    settings = repository.read_settings()
    settings['game_mode'] = True
    repository.write_settings(settings)

    gamer = game.Gamer(coins=20_000, health=50)
    gamer.inspiration = 50
    repository.write_gamer(gamer)
    return repository, GameService(repository), project, stage


def _inventory_count(state, category, item_key):
    category_payload = next(
        item for item in state['inventory']['categories']
        if item['key'] == category
    )
    item = next(
        (item for item in category_payload['items'] if item['key'] == item_key),
        None,
    )
    return 0 if item is None else item['count']


def test_state_is_json_safe_and_contains_explicit_catalogs(game_context):
    _repository, service, _project, _stage = game_context

    state = service.get_state()

    json.dumps(state, ensure_ascii=False)
    assert state['profile']['level'] == 1
    assert state['enabled'] is True
    assert state['daily_challenge']['current']['option_id']
    assert len(state['daily_challenge']['options']) == 3
    assert state['weekly_challenge']['catalog']
    assert state['writing_session']['server_time']
    assert state['specializations']['items']
    assert state['manuscripts']['cabinet']['relics']
    assert state['bank']['credit'] is None
    assert state['shop']['categories']


def test_developer_mode_updates_profile_and_grants_registered_item(game_context):
    repository, _service, _project, _stage = game_context
    service = GameService(repository, developer_mode=True)
    profile = service.update_developer_profile(
        level=4,
        health=500,
        coins=123.4,
        exp=77.5,
        test_date_enabled=False,
        test_datetime=None,
    )
    granted = service.grant_developer_inventory_item(
        'Предметы', 'Компас рукописи', 3,
    )

    assert profile['state']['profile']['level'] == 4
    assert profile['state']['profile']['health'] == 100
    assert profile['state']['profile']['coins'] == 123.4
    assert repository.read_settings()['today_for_test_mode'] is False
    assert _inventory_count(granted['state'], 'Предметы', 'Компас рукописи') == 3


def test_developer_mode_endpoints_are_unavailable_in_regular_runtime(game_context):
    _repository, service, _project, _stage = game_context

    with pytest.raises(ConflictError, match='Режим разработчика недоступен'):
        service.get_developer_state()


def test_state_finishes_an_expired_writing_session(game_context):
    repository, service, _project, _stage = game_context
    gamer = repository.read_gamer()
    ok, _message = gamer.start_writing_session(
        25, 1_000, 'Продолжить черновик', save=False,
    )
    assert ok is True
    gamer.writing_session['started_at'] = game.get_session_now() - timedelta(minutes=26)
    repository.write_gamer(gamer)

    state = service.get_state()

    assert state['writing_session']['active'] is None
    assert state['writing_session']['history'][-1]['successful'] is False
    assert any(
        'Сессия завершена' in item['text']
        for item in state['notifications']['unread']
    )


def test_notification_history_migrates_legacy_events_with_backup(game_context):
    repository, service, _project, _stage = game_context
    created_at = datetime(2026, 8, 15, 9, 30)
    data = repository.read_projects()
    data['notifications'] = {
        'new': [
            engine.Notification('Стрик сохранён.', tag='streak', date_create=created_at),
            engine.Notification('Банк начислил проценты.', tag='bank', date_create=created_at),
        ],
        'read': [
            engine.Notification('Старая запись.', tag='bank', date_create=created_at, status='Read'),
        ],
    }
    repository.write_projects(data)
    source_bytes = (repository.base_dir / 'data.pkl').read_bytes()

    history = service.get_notifications()

    assert history['unread_count'] == 2
    assert [item['tag'] for item in history['unread']] == ['streak', 'bank']
    assert history['read'][0]['status'] == 'read'
    assert all(len(item['id']) == 32 for item in [*history['unread'], *history['read']])
    backups = list((repository.base_dir / 'backups').glob('*/data.pkl'))
    assert len(backups) == 1
    assert backups[0].read_bytes() == source_bytes

    repeated = service.get_notifications()
    assert [item['id'] for item in repeated['unread']] == [
        item['id'] for item in history['unread']
    ]
    marked = service.mark_notification_read(history['unread'][0]['id'])
    assert marked['unread_count'] == 1
    assert marked['read'][0]['id'] == history['unread'][0]['id']
    complete = service.mark_all_notifications_read()
    assert complete['unread'] == []
    assert all(item['status'] == 'read' for item in complete['read'])
    saved = repository.read_projects()['notifications']
    assert all(item.get_status() == 'Read' for item in saved['read'])


def test_notification_history_upgrades_flat_legacy_list(game_context):
    repository, service, _project, _stage = game_context
    data = repository.read_projects()
    data['notifications'] = ['Событие из старой версии.']
    repository.write_projects(data)

    history = service.get_notifications()

    assert history['unread_count'] == 1
    assert history['unread'][0]['text'] == 'Событие из старой версии.'
    saved = repository.read_projects()['notifications']
    assert isinstance(saved, dict)
    assert isinstance(saved['new'][0], engine.Notification)
    assert saved['new'][0].notification_id == history['unread'][0]['id']


def test_game_command_returns_buffered_bank_notifications(game_context):
    _repository, service, _project, _stage = game_context

    def mutate(gamer, _projects):
        gamer.bank_account._add_notification('Банковское событие.')
        return {'message': None}

    response = service._command(mutate)

    assert response['messages'] == ['Банковское событие.']
    assert [
        item['text'] for item in response['state']['notifications']['unread']
    ] == ['Банковское событие.']


def test_writing_session_uses_server_progress_and_rewards(game_context):
    _repository, service, project, _stage = game_context
    project_key = f'project:{project.project_id}'

    started = service.start_writing_session(
        15, 100, 'Написать текст', mode_key='sprint',
    )
    starting_coins = started['state']['profile']['coins']
    active = started['state']['writing_session']['active']
    assert 0 < active['remaining_seconds'] <= 15 * 60
    assert datetime.fromisoformat(started['state']['writing_session']['server_time'])

    progress = service.record_project_progress(
        added_symbols=100,
        project_key=project_key,
        project_progress=999_999,  # Ignored in favour of repository state.
    )
    assert progress['result']['rewarded'] is True
    assert progress['state']['writing_session']['active']['progress'] == 100

    finished = service.finish_writing_session()
    assert finished['result']['successful'] is True
    assert finished['state']['writing_session']['active'] is None
    assert finished['state']['writing_session']['history'][-1]['successful'] is True
    assert finished['state']['profile']['coins'] > starting_coins


def test_negative_progress_only_counts_active_editing_session(game_context):
    _repository, service, project, _stage = game_context
    project_key = f'project:{project.project_id}'
    service.start_writing_session(
        25, 100, 'Отредактировать текст', mode_key='editing',
    )
    before = service.get_state()['profile']

    result = service.record_project_progress(
        added_symbols=-30,
        project_key=project_key,
        project_progress=25,
    )

    assert result['result'] == {
        'added_symbols': -30,
        'processed_symbols': 30,
        'rewarded': False,
        'streak_rewards': 0,
    }
    assert result['state']['writing_session']['active']['progress'] == 30
    assert result['state']['profile']['coins'] == before['coins']
    assert result['state']['profile']['inspiration'] == before['inspiration']


def test_zero_progress_is_noop_without_resolving_project(game_context):
    _repository, service, _project, _stage = game_context

    result = service.record_project_progress(
        added_symbols=0,
        project_key='project:does-not-exist',
        project_progress=100,
    )

    assert result['result']['processed_symbols'] == 0
    assert result['result']['rewarded'] is False


def test_daily_rewards_are_rebuilt_from_server_catalog(game_context):
    repository, service, _project, _stage = game_context
    state = service.get_state()
    current_id = state['daily_challenge']['current']['option_id']
    gamer = repository.read_gamer()
    gamer.daily_challenge['reward_coins'] = 9_999_999
    gamer.daily_challenge['reward_exp'] = 9_999_999
    for option in gamer.daily_challenge_options:
        if option['option_id'] == current_id:
            option['reward_coins'] = 9_999_999
            option['reward_exp'] = 9_999_999
    repository.write_gamer(gamer)

    normalized = service.get_state()['daily_challenge']

    assert normalized['current']['reward']['coins'] < 9_999_999
    assert normalized['current']['reward']['experience'] < 9_999_999
    replacement = next(
        item for item in normalized['options']
        if item['option_id'] != current_id
    )
    changed = service.select_daily_challenge(replacement['option_id'])
    assert changed['state']['daily_challenge']['current']['option_id'] == replacement['option_id']
    assert changed['state']['profile']['inspiration'] == 35


def test_weekly_specialization_and_creative_event_commands(game_context):
    repository, service, _project, _stage = game_context

    weekly = service.start_weekly_challenge('symbols')
    assert weekly['state']['weekly_challenge']['current']['key'] == 'symbols'
    with pytest.raises(ConflictError):
        service.start_weekly_challenge('days')

    gamer = repository.read_gamer()
    gamer.level = game.SPECIALIZATION_LEVEL
    gamer.pending_creative_event = 'unexpected_idea'
    repository.write_gamer(gamer)
    selected = service.select_specialization('marathoner')
    assert selected['state']['specializations']['selected'] == 'marathoner'
    resolved = service.resolve_creative_event('safe')
    assert resolved['state']['inspiration']['creative_event'] is None


def test_registry_buy_sell_and_use_are_repository_atomic(game_context):
    repository, service, _project, _stage = game_context
    category = 'Зелья'
    item_key = 'Микро зелье здоровья'

    bought = service.buy_item(category, item_key, 2)
    assert _inventory_count(bought['state'], category, item_key) == 2

    used = service.use_item(category, item_key, 1)
    assert used['state']['profile']['health'] == 55
    assert _inventory_count(used['state'], category, item_key) == 1

    sold = service.sell_item(category, item_key, 1)
    assert _inventory_count(sold['state'], category, item_key) == 0

    medal_key = 'Медаль качества'
    gamer = repository.read_gamer()
    gamer.items.setdefault('Предметы', {})[medal_key] = 1
    gamer.session_grade_boosts = 1
    repository.write_gamer(gamer)
    with pytest.raises(ConflictError):
        service.use_item('Предметы', medal_key, 1)
    unchanged = repository.read_gamer()
    assert unchanged.items['Предметы'][medal_key] == 1
    assert unchanged.session_grade_boosts == 1


def test_streak_freeze_uses_stable_project_id_and_shared_inventory(
        game_context, monkeypatch,
):
    repository, service, project, _stage = game_context
    today = date(2026, 8, 15)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    data = repository.read_projects()
    saved_project = data['projects'][project.name]
    saved_project.enable_stages = False
    saved_project.personal_goal_for_the_day = 100
    saved_project.project_plan = {}
    saved_project.streaks = [today - timedelta(days=1)]
    saved_project.streak_status = 'Active'
    data['global_streaks'] = [today - timedelta(days=1)]
    repository.write_projects(data)
    gamer = repository.read_gamer()
    gamer.items.setdefault('Предметы', {})['Заморозка'] = 2
    repository.write_gamer(gamer)

    state = service.get_state()
    assert state['streak_freezes']['global_available'] is False
    assert state['streak_freezes']['inventory_count'] == 2
    assert state['streak_freezes']['projects'][0]['project_id'] == project.project_id

    frozen = service.apply_streak_freeze(
        'project', project_id=project.project_id,
    )
    assert frozen['result']['source_count'] == 1
    assert frozen['state']['streak_freezes']['inventory_count'] == 1
    saved = repository.read_projects()
    assert engine.streak_is_freeze_for_day(
        saved['projects'][project.name].streaks, today,
    )
    assert engine.streak_is_freeze_for_day(saved['global_streaks'], today)

    saved_project = saved['projects'][project.name]
    saved_project.streaks = []
    saved_project.streak_status = 'No'
    saved['global_streaks'] = [today - timedelta(days=1)]
    saved['global_streak_status'] = 'Active'
    repository.write_projects(saved)

    global_state = service.get_state()
    assert global_state['streak_freezes']['global_available'] is True
    globally_frozen = service.apply_streak_freeze('global')
    assert globally_frozen['state']['streak_freezes']['inventory_count'] == 0
    global_data = repository.read_projects()
    assert engine.streak_is_freeze_for_day(global_data['global_streaks'], today)
    assert global_data['global_streak_status'] == 'Freeze'


def test_streak_freeze_rejects_missing_inventory_without_writes(
        game_context, monkeypatch,
):
    repository, service, project, _stage = game_context
    today = date(2026, 8, 15)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    before = repository.read_projects()

    with pytest.raises(ConflictError) as error:
        service.apply_streak_freeze('project', project_id=project.project_id)

    assert error.value.code == 'streak_freeze_not_in_inventory'
    assert repository.read_projects()['global_streaks'] == before['global_streaks']


def test_legacy_manuscript_names_migrate_to_stable_ids_without_reward(game_context):
    repository, service, project, stage = game_context
    gamer = repository.read_gamer()
    gamer.manuscript_journeys = {
        project.name: [10, 25],
        f'stage:{project.name}:{stage.stage_id}': [10],
    }
    repository.write_gamer(gamer)

    state = service.get_state()
    journeys = {
        item['owner_key']: item['received_milestones']
        for item in state['manuscripts']['journeys']
    }

    assert journeys[f'project:{project.project_id}'] == [10, 25]
    assert journeys[f'stage:{project.project_id}:{stage.stage_id}'] == [10]
    saved = repository.read_gamer().manuscript_journeys
    assert project.name not in saved
    assert f'stage:{project.name}:{stage.stage_id}' not in saved


def test_skill_and_quest_commands_use_catalog_keys(game_context):
    repository, service, _project, _stage = game_context
    gamer = repository.read_gamer()
    gamer.available_skill_points = 2
    repository.write_gamer(gamer)

    skilled = service.increase_skill('productivity', 2)
    productivity = next(
        item for item in skilled['state']['skills']['items']
        if item['key'] == 'productivity'
    )
    assert productivity['points'] == 2

    available = skilled['state']['quests']['by_status'][game.Quest.AVAILABLE]
    if available:
        quest_id = available[0]['id']
        started = service.start_quest(quest_id)
        assert any(
            quest['id'] == quest_id
            for quest in started['state']['quests']['by_status'][game.Quest.ACTIVE]
        )
        abandoned = service.abandon_quest(quest_id)
        assert any(
            quest['id'] == quest_id
            for quest in abandoned['state']['quests']['by_status'][game.Quest.AVAILABLE]
        )


def test_disabled_game_mode_gates_commands_and_progress_is_noop(game_context):
    repository, service, project, _stage = game_context
    baseline = service.get_state()['profile']['coins']
    settings = repository.read_settings()
    settings['game_mode'] = False
    repository.write_settings(settings)

    state = service.get_state()
    assert state['enabled'] is False
    with pytest.raises(ConflictError) as error:
        service.start_writing_session(15, 100, 'Написать текст', 'sprint')
    assert error.value.code == 'game_mode_disabled'

    result = service.record_project_progress(
        added_symbols=100,
        project_key=f'project:{project.project_id}',
        project_progress=25,
        streak_events=[{
            'status': 'Start',
            'type': 'Local',
            'length': 1,
            'key': f'project:{project.project_id}',
            'date': '1900-01-01',
        }, {
            'status': 'Start',
            'type': 'Global',
            'length': 1,
            'date': '2999-01-01',
        }],
    )
    assert result['result']['skipped'] == 'game_mode_disabled'
    assert repository.read_gamer().coins == baseline
    unchanged = repository.read_projects()
    assert unchanged['projects'][project.name].last_streak_bonus is None
    assert unchanged['last_global_streak_bonus'] is None


def test_progress_streak_events_are_idempotent_per_server_day(game_context):
    repository, service, project, _stage = game_context
    before = service.get_state()['profile']['coins']
    key = f'project:{project.project_id}'
    events = [{
        'status': 'Start',
        'type': 'Local',
        'length': 1,
        'key': key,
        'date': '1900-01-01',
    }, {
        'status': 'Start',
        'type': 'Global',
        'length': 1,
        'date': '2999-01-01',
    }]

    result = service.record_project_progress(
        added_symbols=100,
        project_key=key,
        project_progress=25,
        streak_events=events,
    )

    assert result['state']['profile']['coins'] > before + 100
    assert result['result']['streak_rewards'] == 2
    assert 'стрик' in result['message'].casefold()
    saved = repository.read_projects()
    today = engine.today_for_test()
    assert saved['projects'][project.name].last_streak_bonus == today
    assert saved['last_global_streak_bonus'] == today

    before_repeat = result['state']['profile']['coins']
    repeated = service.record_project_progress(
        added_symbols=100,
        project_key=key,
        project_progress=25,
        streak_events=events,
    )

    assert repeated['result']['streak_rewards'] == 0
    assert 'стрик' not in repeated['message'].casefold()
    assert repeated['state']['profile']['coins'] - before_repeat < 20
    repeated_data = repository.read_projects()
    assert repeated_data['projects'][project.name].last_streak_bonus == today
    assert repeated_data['last_global_streak_bonus'] == today


def test_streak_marker_is_not_set_when_no_reward_message(game_context):
    repository, service, project, _stage = game_context
    key = f'project:{project.project_id}'

    result = service.record_project_progress(
        added_symbols=100,
        project_key=key,
        project_progress=25,
        streak_events=[{
            'status': 'No',
            'type': 'Local',
            'length': 0,
            'key': key,
        }],
    )

    assert result['result']['streak_rewards'] == 0
    saved = repository.read_projects()
    assert saved['projects'][project.name].last_streak_bonus is None


def test_completion_rewards_use_stable_key_and_authoritative_stage_data(game_context):
    repository, service, project, stage = game_context
    data = repository.read_projects()
    saved_project = data['projects'][project.name]
    saved_stage = saved_project.stages[0]
    saved_stage.status = 'завершен'
    repository.write_projects(data)
    key = f'stage:{project.project_id}:{stage.stage_id}'
    before = service.get_state()['profile']['coins']

    result = service.record_completions([{
        'key': key,
        'total_symbols': 999_999_999,
        'is_stage': False,
        'streak_status': 'Complete',
        'streak_length': 2,
    }])

    completion = result['result']['completions'][0]
    assert completion['key'] == key
    assert completion['is_stage'] is True
    assert completion['total_symbols'] == saved_stage.get_total_symbols()
    assert completion['rewarded'] is True
    assert result['state']['profile']['coins'] > before

    repeated = service.record_completions([{
        'key': key,
        'streak_status': 'Complete',
        'streak_length': 2,
    }])
    assert repeated['result']['completions'][0]['rewarded'] is False
    assert repeated['state']['profile']['coins'] == result['state']['profile']['coins']


def test_custom_award_legacy_inventory_migrates_to_stable_id(game_context):
    repository, service, _project, _stage = game_context
    legacy_award = game_data.Item(
        'Выходной', 75, item_type='Награды', description='',
    )
    legacy_award.count = 2
    gamer = repository.read_gamer()
    gamer.custom_awards = [legacy_award]
    gamer.custom_awards_inventory = {'Выходной': 1}
    gamer.items.setdefault('Награды', {})['Выходной'] = 3
    repository.write_gamer(gamer)

    state = service.get_state()
    award = state['custom_awards']['items'][0]

    assert award['id']
    assert award['count'] == 6
    assert award['description'] == 'Кастомная награда без эффекта'
    saved = repository.read_gamer()
    assert saved.custom_awards[0].award_id == award['id']
    assert saved.custom_awards[0].count == 0
    assert saved.custom_awards_inventory['Выходной'] == 6
    assert 'Выходной' not in saved.items['Награды']

    updated = service.update_custom_award(
        award['id'], name='День отдыха', price=90,
    )
    migrated = updated['result']['award']
    assert migrated['id'] == award['id']
    assert migrated['name'] == 'День отдыха'
    assert migrated['count'] == 6
    assert 'Выходной' not in repository.read_gamer().custom_awards_inventory


def test_custom_award_lifecycle_uses_saved_price_and_id(game_context):
    _repository, service, _project, _stage = game_context
    created = service.create_custom_award('Чашка кофе', 40)
    award_id = created['result']['award']['id']
    coins_before = created['state']['profile']['coins']

    bought = service.buy_custom_award(award_id, 2)
    assert bought['result']['unit_price'] == 40
    assert bought['result']['total_price'] == 80
    assert bought['state']['profile']['coins'] == coins_before - 80
    assert bought['result']['award']['count'] == 2

    updated = service.update_custom_award(
        award_id, name='Большая чашка кофе', price=80,
    )
    assert updated['result']['award']['id'] == award_id
    assert updated['result']['award']['count'] == 2

    deleted = service.delete_custom_award(award_id)
    assert deleted['result']['definition_removed'] is False
    hidden = next(
        item for item in deleted['state']['custom_awards']['items']
        if item['id'] == award_id
    )
    assert hidden['available_in_shop'] is False
    with pytest.raises(ConflictError) as unavailable:
        service.buy_custom_award(award_id)
    assert unavailable.value.code == 'custom_award_not_available'

    sold = service.sell_custom_award(award_id)
    assert sold['result']['unit_price'] == 60
    assert sold['result']['remaining'] == 1
    used = service.use_custom_award(award_id)
    assert used['result']['remaining'] == 0
    assert used['result']['definition_removed'] is True
    assert all(
        item['id'] != award_id
        for item in used['state']['custom_awards']['items']
    )
    with pytest.raises(NotFoundError):
        service.use_custom_award(award_id)


def test_custom_award_validation_and_name_conflicts(game_context):
    _repository, service, _project, _stage = game_context

    with pytest.raises(ValidationError):
        service.create_custom_award('   ', 10)
    with pytest.raises(ValidationError):
        service.create_custom_award('Награда', float('nan'))

    created = service.create_custom_award('Своя награда', 10)
    with pytest.raises(ConflictError) as duplicate:
        service.create_custom_award('Своя награда', 20)
    assert duplicate.value.code == 'custom_award_name_conflict'

    built_in_name = next(iter(game_data.ITEM_REGISTRY['Награды']))
    with pytest.raises(ConflictError):
        service.update_custom_award(
            created['result']['award']['id'], name=built_in_name,
        )


def test_bank_deposit_commands_are_authoritative_and_notification_is_buffered(
        game_context, monkeypatch,
):
    repository, service, _project, _stage = game_context
    starting_coins = service.get_state()['profile']['coins']
    write_projects = repository.write_projects
    project_writes = 0

    def count_project_write(data):
        nonlocal project_writes
        project_writes += 1
        write_projects(data)

    monkeypatch.setattr(repository, 'write_projects', count_project_write)
    monkeypatch.setattr(
        engine,
        'save_data',
        lambda *_args, **_kwargs: pytest.fail(
            'bank notification bypassed the repository transaction',
        ),
    )

    preview = service.preview_bank_product(
        'deposit', 100, 7, allow_interest_withdrawal=False,
    )
    assert preview['result']['amount'] == 100
    assert preview['result']['rate'] == round(
        preview['state']['bank']['deposit_rate'] * 1.15, 3,
    )

    opened = service.open_bank_deposit(
        100, 7, allow_interest_withdrawal=False,
    )
    assert opened['state']['profile']['coins'] == starting_coins - 100
    assert opened['state']['bank']['deposit']['principal'] == 100
    assert opened['state']['bank']['deposit']['allow_interest_withdrawal'] is False
    assert project_writes == 1
    notifications = repository.read_projects()['notifications']
    assert notifications['new'][-1].tag == 'bank'

    topped_up = service.top_up_bank_deposit(50)
    assert topped_up['state']['bank']['deposit']['principal'] == 150
    with pytest.raises(ConflictError) as not_mature:
        service.withdraw_bank_deposit()
    assert not_mature.value.code == 'bank_deposit_not_mature'

    returned = service.withdraw_bank_deposit(allow_early=True)
    assert returned['result'] == {'early': True, 'received': 150}
    assert returned['state']['bank']['deposit'] is None
    assert returned['state']['profile']['coins'] == starting_coins


def test_bank_credit_and_interest_commands_use_legacy_calculations(
        game_context, monkeypatch,
):
    repository, service, _project, _stage = game_context
    today = date(2026, 8, 15)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    service.get_state()
    gamer = repository.read_gamer()
    gamer.level = 3
    gamer.coins = 1_000
    gamer.economy_rebalanced_v1 = True
    repository.write_gamer(gamer)

    preview = service.preview_bank_product('credit', 100, 7)
    opened = service.open_bank_credit(100, 7)
    assert opened['result']['rate'] == preview['result']['rate']
    assert opened['state']['profile']['coins'] == 1_100
    assert opened['state']['bank']['credit']['principal'] == 100
    with pytest.raises(ConflictError):
        service.open_bank_credit(100, 7)

    partially_paid = service.partially_repay_bank_credit(30)
    assert partially_paid['result']['paid_amount'] == 30
    assert partially_paid['state']['bank']['credit']['remaining'] < opened['state']['bank']['credit']['remaining']
    repaid = service.repay_bank_credit()
    assert repaid['result']['repaid'] is True
    assert repaid['state']['bank']['credit'] is None

    deposit = service.open_bank_deposit(
        100, 7, allow_interest_withdrawal=True,
    )
    assert deposit['state']['bank']['deposit']['available_interest'] == 0
    today += timedelta(days=1)
    interest = service.withdraw_bank_deposit_interest()
    assert interest['result']['amount'] > 0
    with pytest.raises(ConflictError) as repeated:
        service.withdraw_bank_deposit_interest()
    assert repeated.value.code == 'bank_interest_not_available'


def test_bank_credit_level_limit_and_payment_date_are_server_validated(
        game_context, monkeypatch,
):
    repository, service, _project, _stage = game_context
    current_day = date(2026, 8, 15)
    monkeypatch.setattr(engine, 'today_for_test', lambda: current_day)
    with pytest.raises(ConflictError) as level_error:
        service.open_bank_credit(100, 7)
    assert level_error.value.code == 'bank_credit_level_too_low'

    service.get_state()
    gamer = repository.read_gamer()
    gamer.level = 3
    gamer.coins = 1_000
    gamer.economy_rebalanced_v1 = True
    repository.write_gamer(gamer)
    limit = service.get_state()['bank']['credit_limit']
    with pytest.raises(ConflictError) as limit_error:
        service.open_bank_credit(limit + 0.1, 7)
    assert limit_error.value.code == 'bank_credit_limit_exceeded'

    opened = service.open_bank_credit(100, 7)
    with pytest.raises(ConflictError) as early_payment:
        service.make_bank_loan_payment()
    assert early_payment.value.code == 'bank_payment_not_due'
    current_day += timedelta(days=1)
    payment = service.make_bank_loan_payment()
    assert payment['result']['paid'] is True
    assert payment['state']['bank']['credit']['paid_amount'] > 0


def test_bank_and_custom_award_commands_respect_game_mode_gate(game_context):
    repository, service, _project, _stage = game_context
    settings = repository.read_settings()
    settings['game_mode'] = False
    repository.write_settings(settings)

    with pytest.raises(ConflictError) as bank_error:
        service.open_bank_deposit(100, 7)
    assert bank_error.value.code == 'game_mode_disabled'
    with pytest.raises(ConflictError) as award_error:
        service.create_custom_award('Неразрешённая награда', 10)
    assert award_error.value.code == 'game_mode_disabled'
    gamer = repository.read_gamer()
    assert gamer.bank_account.get_deposit() is None
    assert gamer.custom_awards == []


def test_streak_recovery_repairs_project_marker_without_duplicate_reward(
        game_context, monkeypatch,
):
    repository, service, project, _stage = game_context
    key = f'project:{project.project_id}'
    event = [{
        'status': 'Start',
        'type': 'Local',
        'length': 1,
        'key': key,
    }]
    original_write_projects = repository.write_projects

    def fail_project_write(_data):
        raise OSError('simulated data.pkl write failure')

    monkeypatch.setattr(repository, 'write_projects', fail_project_write)
    with pytest.raises(OSError):
        service.record_project_progress(
            added_symbols=100,
            project_key=key,
            project_progress=25,
            streak_events=event,
        )

    gamer_after_failure = repository.read_gamer()
    today = engine.today_for_test()
    assert gamer_after_failure.api_streak_reward_days[f'local:{key}'] == today
    assert repository.read_projects()['projects'][project.name].last_streak_bonus is None

    monkeypatch.setattr(repository, 'write_projects', original_write_projects)
    retried = service.record_project_progress(
        added_symbols=100,
        project_key=key,
        project_progress=25,
        streak_events=event,
    )

    assert retried['result']['streak_rewards'] == 0
    assert repository.read_projects()['projects'][project.name].last_streak_bonus == today
