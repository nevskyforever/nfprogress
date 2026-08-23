from datetime import timedelta

from fastapi.testclient import TestClient

import engine
import game_data
from backend.app.config import RuntimeConfig
from backend.app.main import create_app


def _response_schema(openapi: dict, path: str, method: str = 'get') -> dict:
    return openapi['paths'][path][method]['responses']['200'][
        'content'
    ]['application/json']['schema']


def test_openapi_exposes_game_state_catalog_and_command_models(tmp_path):
    app = create_app(RuntimeConfig(
        data_dir=tmp_path,
        session_token='game-contract-token',
        platform='web',
    ))
    openapi = app.openapi()
    schemas = openapi['components']['schemas']

    assert _response_schema(openapi, '/api/game/state')['$ref'].endswith(
        '/GameStateResponse',
    )
    assert _response_schema(openapi, '/api/game/catalog')['$ref'].endswith(
        '/GameCatalogResponse',
    )
    assert _response_schema(openapi, '/api/game/notifications')['$ref'].endswith(
        '/GameNotificationsResponse',
    )
    assert _response_schema(
        openapi,
        '/api/game/notifications/{notification_id}/read',
        'post',
    )['$ref'].endswith('/GameNotificationsResponse')
    assert _response_schema(
        openapi,
        '/api/game/notifications/read-all',
        'post',
    )['$ref'].endswith('/GameNotificationsResponse')

    command_paths = {
        path: methods
        for path, methods in openapi['paths'].items()
        if path.startswith('/api/game/')
        and path not in {
            '/api/game/state',
            '/api/game/catalog',
            '/api/game/notifications',
            '/api/game/notifications/{notification_id}/read',
            '/api/game/notifications/read-all',
        }
    }
    assert command_paths
    for methods in command_paths.values():
        for method, operation in methods.items():
            if method == 'parameters':
                continue
            response = operation['responses']['200']['content'][
                'application/json'
            ]['schema']
            assert response['$ref'].endswith('/GameCommandResponse')

    state_properties = schemas['GameStateResponse']['properties']
    assert set(state_properties) == {
        'enabled',
        'server_time',
        'profile',
        'skills',
        'buffs',
        'inventory',
        'notifications',
        'streak_freezes',
        'quests',
        'daily_challenge',
        'weekly_challenge',
        'writing_session',
        'inspiration',
        'specializations',
        'manuscripts',
        'bank',
        'custom_awards',
        'shop',
    }
    assert schemas['GameCommandResponse']['properties']['state'][
        '$ref'
    ].endswith('/GameStateResponse')
    assert schemas['GameItemResponse']['additionalProperties'][
        '$ref'
    ].endswith('/JsonValue')
    assert schemas['GameQuestsResponse']['properties']['by_status'][
        'additionalProperties'
    ]['items']['$ref'].endswith('/GameQuestResponse')


def test_representative_full_game_state_and_commands_validate(tmp_path):
    app = create_app(RuntimeConfig(
        data_dir=tmp_path,
        session_token='game-contract-token',
        platform='web',
    ))
    headers = {'X-NFProgress-Token': 'game-contract-token'}

    with TestClient(app, headers=headers) as client:
        enabled = client.patch('/api/settings', json={
            'values': {'game_mode': True},
        })
        assert enabled.status_code == 200, enabled.text

        project_response = client.post('/api/projects', json={
            'name': 'Contract project',
            'goal': 10_000,
            'unit': 'symbols',
        })
        assert project_response.status_code == 201, project_response.text
        project_id = project_response.json()['id']

        repository = app.state.services.repository
        gamer = repository.read_gamer()
        gamer.level = 3
        gamer.coins = 2_000
        gamer.inspiration = 50
        gamer.items.setdefault('Предметы', {})['Заморозка'] = 1
        gamer.items['Future category'] = {'Unknown item': 2}
        gamer.buffs = [game_data.Buff(
            'Contract buff',
            'Positive contract fixture',
            game_data.Buff.POSITIVE,
            'coins',
            0.25,
            source='contract',
        )]
        gamer.debuffs = [game_data.Buff(
            'Contract debuff',
            'Negative contract fixture',
            game_data.Buff.NEGATIVE,
            'exp',
            0.1,
            source='contract',
        )]
        gamer.pending_creative_event = 'unexpected_idea'
        gamer.writing_session_history = [{
            'future_metadata': {'nested': [1, True, None]},
        }]
        gamer.creative_event_history = [{
            'event': 'unexpected_idea',
            'success': True,
        }]
        repository.write_gamer(gamer)

        projects = repository.read_projects()
        project = projects['projects']['Contract project']
        today = engine.today_for_test()
        project.personal_goal_for_the_day = 100
        project.project_plan = {}
        project.streaks = [today - timedelta(days=1)]
        project.streak_status = 'Active'
        projects['notifications'] = {
            'new': [engine.Notification('Contract streak event', tag='streak')],
            'read': [engine.Notification(
                'Contract bank event', tag='bank', status='Read',
            )],
        }
        repository.write_projects(projects)

        state_response = client.get('/api/game/state')
        assert state_response.status_code == 200, state_response.text
        state = state_response.json()
        assert state['enabled'] is True
        assert state['buffs']['positive'][0]['name'] == 'Contract buff'
        assert state['buffs']['negative'][0]['name'] == 'Contract debuff'
        assert state['inspiration']['creative_event']['key'] == 'unexpected_idea'
        assert state['writing_session']['history'][0]['future_metadata'] == {
            'nested': [1, True, None],
        }
        assert state['streak_freezes']['projects'][0]['project_id'] == project_id
        assert state['notifications']['unread_count'] == 1
        assert state['notifications']['unread'][0]['tag'] == 'streak'
        future_category = next(
            category for category in state['inventory']['categories']
            if category['key'] == 'Future category'
        )
        assert future_category['items'][0]['known'] is False

        catalog_response = client.get('/api/game/catalog')
        assert catalog_response.status_code == 200, catalog_response.text
        catalog_item = catalog_response.json()['categories'][0]['items'][0]
        assert 'price' in catalog_item
        assert 'buffs' in catalog_item
        assert 'known' not in catalog_item

        notifications = client.get('/api/game/notifications')
        assert notifications.status_code == 200, notifications.text
        unread = notifications.json()['unread']
        assert len(unread) == 1
        marked = client.post(
            f"/api/game/notifications/{unread[0]['id']}/read",
        )
        assert marked.status_code == 200, marked.text
        assert marked.json()['unread_count'] == 0
        assert len(marked.json()['read']) == 2
        marked_all = client.post('/api/game/notifications/read-all')
        assert marked_all.status_code == 200, marked_all.text
        assert marked_all.json()['unread'] == []

        weekly = client.post('/api/game/weekly-challenge/start', json={
            'challenge_id': 'symbols',
        })
        assert weekly.status_code == 200, weekly.text
        assert weekly.json()['state']['weekly_challenge']['current'][
            'key'
        ] == 'symbols'

        specialization = client.post('/api/game/specialization/select', json={
            'specialization_id': 'marathoner',
        })
        assert specialization.status_code == 200, specialization.text
        assert specialization.json()['state']['specializations'][
            'selected'
        ] == 'marathoner'

        session = client.post('/api/game/writing-sessions/start', json={
            'duration_minutes': 15,
            'target_symbols': 100,
            'intention': 'Contract session',
            'mode': 'flow',
        })
        assert session.status_code == 200, session.text
        assert session.json()['state']['writing_session']['active'][
            'target_symbols'
        ] == 100

        award = client.post('/api/game/custom-awards', json={
            'name': 'Contract award',
            'price': 25,
        })
        assert award.status_code == 200, award.text
        assert award.json()['state']['custom_awards']['items'][0][
            'name'
        ] == 'Contract award'

        credit = client.post('/api/game/bank/credit', json={
            'amount': 100,
            'days': 7,
        })
        assert credit.status_code == 200, credit.text
        assert credit.json()['state']['bank']['credit']['principal'] == 100
