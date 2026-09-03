from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

import engine
from backend.app.config import RuntimeConfig
from backend.app import __main__ as backend_cli
from backend.app.__main__ import main as backend_main
from backend.app.main import create_app
from nfprogress.core.sqlite.repository import SQLiteMirrorRepository


TOKEN = 'test-session-token'


@pytest.fixture
def client(tmp_path):
    app = create_app(RuntimeConfig(
        data_dir=tmp_path,
        session_token=TOKEN,
        allowed_origins=('http://localhost:5173',),
        platform='web',
    ))
    with TestClient(app, headers={'X-NFProgress-Token': TOKEN}) as value:
        yield value


def _create_project(client: TestClient, name: str = 'Роман') -> dict:
    response = client.post('/api/projects', json={
        'name': name,
        'goal': 10_000,
        'unit': 'symbols',
    })
    assert response.status_code == 201, response.text
    return response.json()


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_health_openapi_and_desktop_session_authentication(client):
    assert client.get('/health').json()['status'] == 'ok'
    assert client.get('/openapi.json').status_code == 200

    unauthorized = client.get(
        '/api/projects', headers={'X-NFProgress-Token': 'wrong'},
    )
    assert unauthorized.status_code == 401
    assert unauthorized.json()['detail']['code'] == 'invalid_session'

    invalid = client.post('/api/projects', json={})
    assert invalid.status_code == 422
    assert invalid.json()['detail']['code'] == 'invalid_request'
    assert invalid.json()['detail']['fields']


def test_project_cover_is_created_updated_and_returned_by_api(client):
    cover = 'data:image/jpeg;base64,/9j/2Q=='
    created = client.post('/api/projects', json={
        'name': 'Роман с обложкой', 'goal': 10_000, 'cover_image': cover,
    })

    assert created.status_code == 201, created.text
    project = created.json()
    assert project['cover_image'] == cover

    updated = client.patch(
        f"/api/projects/{project['id']}", json={'cover_image': None},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()['cover_image'] is None


def test_project_folders_and_manual_order_are_exposed_by_api(client):
    first = _create_project(client, 'Первый')
    second = _create_project(client, 'Второй')
    folder_response = client.post('/api/projects/folders', json={'name': 'Романы'})
    assert folder_response.status_code == 201, folder_response.text
    folder = folder_response.json()

    moved = client.patch(
        f"/api/projects/{first['id']}", json={'folder_id': folder['id']},
    )
    ordered = client.put('/api/projects/order', json={
        'project_ids': [second['id'], first['id']],
    })

    assert moved.json()['folder_id'] == folder['id']
    assert client.get('/api/projects/folders').json() == [folder]
    assert [project['id'] for project in ordered.json()] == [second['id'], first['id']]
    assert [project['id'] for project in client.get('/api/projects', params={'sort': 'manual'}).json()] == [second['id'], first['id']]


def test_project_metadata_boundary_is_allow_listed_and_uses_authoritative_service(client):
    project = _create_project(client)
    updated = client.patch(
        f"/api/projects/{project['id']}/metadata",
        json={'name': 'Новое имя', 'deadline': None, 'unit': 'A4'},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()['name'] == 'Новое имя'
    assert updated.json()['unit'] == 'A4'
    rejected = client.patch(
        f"/api/projects/{project['id']}/metadata", json={'total': 10},
    )
    assert rejected.status_code == 422


def test_project_metadata_boundary_preserves_non_metadata_state(client):
    project = _create_project(client)
    repository = client.app.state.services.repository

    def seed(data):
        stored = next(iter(data['projects'].values()))
        stored.mindmap_data = {
            'nodeData': {'id': 'root', 'topic': 'Keep', 'children': []},
        }
        stored.synch = {'type': 'word', 'path': '/tmp/keep.docx'}

    repository.update_projects(seed)
    updated = client.patch(
        f"/api/projects/{project['id']}/metadata", json={'name': 'Без потерь'},
    )
    assert updated.status_code == 200, updated.text
    stored = next(iter(repository.read_projects()['projects'].values()))
    assert stored.mindmap_data['nodeData']['id'] == 'root'
    assert stored.synch == {'type': 'word', 'path': '/tmp/keep.docx'}


def test_project_metadata_success_survives_mirror_failure(client, monkeypatch):
    project = _create_project(client)

    def fail(*args, **kwargs):
        raise OSError('disk full')

    monkeypatch.setattr(SQLiteMirrorRepository, 'rebuild', fail)
    updated = client.patch(
        f"/api/projects/{project['id']}/metadata", json={'name': 'PKL сохранён'},
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()['name'] == 'PKL сохранён'
    database = client.app.state.services.repository.base_dir / 'nfprogress.db'
    import sqlite3
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT sync_status FROM mirror_state').fetchone()[0] == 'dirty'


def test_api_accepts_existing_cover_larger_than_compact_export(client):
    # Covers produced by older frontend builds can be larger than the compact
    # 1.35 MB export used now.  They must reach the service instead of failing
    # Pydantic's generic request validation first.
    cover = 'data:image/jpeg;base64,' + ('AAAA' * 450_000)
    created = client.post('/api/projects', json={
        'name': 'Старая большая обложка', 'goal': 10_000, 'cover_image': cover,
    })

    assert created.status_code == 201, created.text
    assert created.json()['cover_image'] == cover


def test_timed_potion_uses_timezone_safe_developer_clock(client, monkeypatch):
    monkeypatch.setattr(
        engine,
        'now_for_test',
        lambda: datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
    )
    enabled = client.patch('/api/settings', json={
        'values': {'game_mode': True},
    })
    assert enabled.status_code == 200, enabled.text

    repository = client.app.state.services.repository
    gamer = repository.read_gamer()
    gamer.level = 99
    gamer.items.setdefault('Зелья', {})['Часовое зелье просвещения'] = 1
    repository.write_gamer(gamer)

    used = client.post('/api/game/inventory/use', json={
        'category': 'Зелья',
        'item_id': 'Часовое зелье просвещения',
        'count': 1,
    })

    assert used.status_code == 200, used.text
    assert used.json()['state']['buffs']['positive'][0]['remaining_seconds'] == 3600


def test_lottery_ticket_use_returns_draw_for_client_animation(client):
    enabled = client.patch('/api/settings', json={
        'values': {'game_mode': True},
    })
    assert enabled.status_code == 200, enabled.text

    repository = client.app.state.services.repository
    gamer = repository.read_gamer()
    gamer.level = 3
    gamer.items.setdefault('Предметы', {})['Лотерейный билет'] = 1
    repository.write_gamer(gamer)

    used = client.post('/api/game/inventory/use', json={
        'category': 'Предметы',
        'item_id': 'Лотерейный билет',
        'count': 1,
    })

    assert used.status_code == 200, used.text
    draw = used.json()['result']['lottery_draws'][0]
    assert len(draw['player_numbers']) == 5
    assert len(draw['winning_numbers']) == 5
    assert draw['matches'] == len(
        set(draw['player_numbers']).intersection(draw['winning_numbers'])
    )


def test_backend_cli_requires_explicit_remote_bind(monkeypatch):
    monkeypatch.delenv('NFPROGRESS_SESSION_TOKEN', raising=False)
    monkeypatch.delenv('NFPROGRESS_PLATFORM', raising=False)

    with pytest.raises(SystemExit, match='--allow-remote'):
        backend_main(['--host', '0.0.0.0'])


def test_parent_process_watchdog_observes_owner_lifecycle(monkeypatch):
    assert backend_cli._process_is_running(os.getpid()) is True
    states = iter((True, False))
    exits = []
    monkeypatch.setattr(backend_cli, '_process_is_running', lambda _pid: next(states))
    monkeypatch.setattr(backend_cli.time, 'sleep', lambda _interval: None)

    backend_cli._watch_parent_process(123, exit_process=exits.append)

    assert exits == [0]


def test_backend_cli_starts_parent_watchdog(monkeypatch, tmp_path):
    started = []
    monkeypatch.setattr(backend_cli, '_start_parent_watchdog', started.append)
    monkeypatch.setattr(backend_cli.uvicorn, 'run', lambda *args, **kwargs: None)

    assert backend_main([
        '--data-dir', str(tmp_path),
        '--parent-pid', str(os.getpid()),
    ]) == 0
    assert started == [os.getpid()]


def test_project_stage_progress_statistics_and_status_workflow(client):
    project = _create_project(client)
    stage_response = client.post(
        f"/api/projects/{project['id']}/stages",
        json={'name': 'Черновик', 'goal': 5_000},
    )
    assert stage_response.status_code == 201, stage_response.text
    stage = stage_response.json()

    progress_response = client.post(
        f"/api/projects/{project['id']}/progress",
        json={'stage_id': stage['id'], 'new_total': 1_500},
    )
    assert progress_response.status_code == 200, progress_response.text
    progress = progress_response.json()
    assert progress['added_symbols'] == 1_500
    assert progress['project']['stages'][0]['total'] == 1_500

    stats = client.get(
        f"/api/projects/{project['id']}/statistics",
        params={'stage_id': stage['id']},
    )
    assert stats.status_code == 200, stats.text
    assert stats.json()['metrics']['entries_count'] == 1

    today = client.get('/api/projects/today')
    assert today.status_code == 200, today.text
    assert today.json()['symbols'] == 1_500
    assert today.json()['projects'][0]['id'] == project['id']

    streak_disabled = client.get('/api/projects/streaks/global')
    assert streak_disabled.status_code == 200, streak_disabled.text
    assert streak_disabled.json() == {
        'enabled': False,
        'status': 'Off',
        'length': 0,
        'max_length': 0,
    }

    projects = client.get('/api/projects', params={
        'status': 'активен', 'search': 'черн', 'sort': 'name',
    })
    assert [item['id'] for item in projects.json()] == [project['id']]

    archived = client.post(
        f"/api/projects/{project['id']}/archive", json={'archived': True},
    )
    assert archived.status_code == 200
    assert archived.json()['status'] == 'в архиве'


def test_huge_finite_values_cannot_persist_as_infinity(client):
    rejected = client.post('/api/projects', json={
        'name': 'Overflow',
        'goal': 1e308,
        'unit': 'A4',
    })
    assert rejected.status_code == 422, rejected.text

    created = client.post('/api/projects', json={
        'name': 'Safe',
        'goal': 100,
        'unit': 'A4',
    })
    assert created.status_code == 201, created.text
    project = created.json()

    progress = client.post(
        f"/api/projects/{project['id']}/progress",
        json={'new_total': 1e308},
    )
    assert progress.status_code == 422, progress.text
    assert client.get(f"/api/projects/{project['id']}").json()['total'] == 0


def test_notes_and_mindmap_use_real_project_storage(client):
    project = _create_project(client, 'Карта')
    created = client.post(f"/api/projects/{project['id']}/notes")
    assert created.status_code == 201, created.text
    note_id = created.json()['id']

    updated = client.patch(
        f"/api/projects/{project['id']}/notes/{note_id}",
        json={
            'title': 'Герои',
            'content': '<b>Анна</b><script>bad()</script>',
            'tags': ['персонажи'],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()['title'] == 'Герои'
    assert '<script>' not in updated.json()['content']

    map_payload = {
        'nodeData': {'id': 'root', 'topic': 'Карта', 'children': []},
        'freeNodes': [{
            'id': 'note-on-map',
            'topic': 'Связано с картой',
            'children': [],
            'position': {'x': 100, 'y': 120},
            'nfprogressNote': True,
        }],
    }
    saved_map = client.put(
        f"/api/projects/{project['id']}/mindmap", json={'data': map_payload},
    )
    assert saved_map.status_code == 200, saved_map.text
    assert saved_map.json()['data']['nodeData']['id'] == 'root'

    notes = client.get(f"/api/projects/{project['id']}/notes").json()['notes']
    assert {item['source_type'] for item in notes} == {'project', 'mindmap'}


def test_settings_help_locales_and_word_upload(client):
    settings = client.patch('/api/settings', json={
        'values': {'language': 'fr', 'frontend_theme': 'dark'},
    })
    assert settings.status_code == 200, settings.text
    assert settings.json()['values']['language'] == 'fr'

    help_response = client.get('/api/content/help', params={'language': 'en'})
    assert help_response.status_code == 200
    assert help_response.json()[0]['key'] == 'quick_start'
    assert client.get('/api/content/locales/pt_BR').status_code == 200

    agreement = client.get('/api/content/agreement', params={'language': 'fr'})
    assert agreement.status_code == 200, agreement.text
    assert agreement.json()['language'] == 'fr'
    assert 'ADDITIONAL TERMS OF USE' in agreement.json()['html']
    accepted = client.post(
        '/api/settings/user-agreement/accept',
        json={'agreement_id': agreement.json()['id']},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['values']['user_agreement'] is True

    upload = client.post(
        '/api/integrations/word/count',
        files={
            'file': (
                'chapter.docx', _docx_bytes('1234567890'),
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ),
        },
    )
    assert upload.status_code == 200, upload.text
    assert upload.json() == {'symbols': 10}

    project = _create_project(client, 'Импорт Word')
    applied = client.post(
        f"/api/projects/{project['id']}/imports/word",
        files={
            'file': (
                'chapter.docx', _docx_bytes('1234567890'),
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ),
        },
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()['changed'] is True
    assert applied.json()['project']['total'] == 10
    assert applied.json()['progress']['added_symbols'] == 10


def test_game_state_and_writing_session_are_server_authoritative(client):
    enabled = client.patch('/api/settings', json={
        'values': {'game_mode': True},
    })
    assert enabled.status_code == 200, enabled.text

    state = client.get('/api/game/state')
    assert state.status_code == 200, state.text
    assert state.json()['profile']['level'] == 1

    started = client.post('/api/game/writing-sessions/start', json={
        'duration_minutes': 15,
        'target_symbols': 100,
        'intention': 'Продолжить черновик',
        'mode': 'flow',
    })
    assert started.status_code == 200, started.text
    assert started.json()['state']['writing_session']['active']['target_symbols'] == 100

    cancelled = client.post('/api/game/writing-sessions/cancel')
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()['state']['writing_session']['active'] is None


def test_streak_freeze_api_uses_server_project_state(client, monkeypatch):
    today = date(2026, 8, 15)
    monkeypatch.setattr(engine, 'today_for_test', lambda: today)
    client.patch('/api/settings', json={'values': {'game_mode': True}})
    project_payload = _create_project(client, 'Серия')
    repository = client.app.state.services.repository
    data = repository.read_projects()
    project = data['projects']['Серия']
    project.personal_goal_for_the_day = 100
    project.project_plan = {}
    project.streaks = [today - timedelta(days=1)]
    project.streak_status = 'Active'
    data['global_streaks'] = [today - timedelta(days=1)]
    repository.write_projects(data)
    gamer = repository.read_gamer()
    gamer.items.setdefault('Предметы', {})['Заморозка'] = 1
    repository.write_gamer(gamer)

    state = client.get('/api/game/state')
    assert state.status_code == 200, state.text
    option = state.json()['streak_freezes']['projects'][0]
    assert option['project_id'] == project_payload['id']

    response = client.post('/api/game/streak-freezes/apply', json={
        'target': 'project',
        'project_id': project_payload['id'],
    })
    assert response.status_code == 200, response.text
    assert response.json()['result']['project_id'] == project_payload['id']
    assert response.json()['state']['streak_freezes']['inventory_count'] == 0


def test_custom_awards_and_bank_commands_use_server_state(client):
    client.patch('/api/settings', json={'values': {'game_mode': True}})
    repository = client.app.state.services.repository
    gamer = repository.read_gamer()
    gamer.level = 3
    gamer.coins = 5_000
    repository.write_gamer(gamer)

    created = client.post('/api/game/custom-awards', json={
        'name': 'Выходной',
        'price': 250,
    })
    assert created.status_code == 200, created.text
    award = created.json()['result']['award']
    assert award['id']

    bought = client.post(
        f"/api/game/custom-awards/{award['id']}/buy",
        json={'count': 2},
    )
    assert bought.status_code == 200, bought.text
    custom_items = bought.json()['state']['shop']['custom_awards']['items']
    assert custom_items[0]['count'] == 2

    preview = client.post('/api/game/bank/preview', json={
        'product_type': 'deposit',
        'amount': 500,
        'days': 10,
        'allow_interest_withdrawal': False,
    })
    assert preview.status_code == 200, preview.text
    assert preview.json()['result']['amount'] == 500
