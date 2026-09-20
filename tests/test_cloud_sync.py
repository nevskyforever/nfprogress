from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.cloud.models import SyncEvent
from backend.app.cloud.schemas import SyncEventEnvelope
from backend.app.cloud.services import SyncService
from test_cloud_auth import cloud_client, create_user, login, migrated_database


def _headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _device(client, token: str, value=None):
    device_id = value or uuid4()
    response = client.put(f'/api/v1/sync/devices/{device_id}', headers=_headers(token))
    assert response.status_code == 200
    return str(device_id)


def _event(project_id: str, **extra):
    value = {
        'event_id': str(uuid4()), 'project_id': project_id, 'entity_id': 'entity-1',
        'entity_type': 'note', 'operation': 'upsert', 'revision': 1,
        'updated_at': datetime.now(timezone.utc).isoformat(), 'deleted_at': None,
    }
    value.update(extra)
    return value


def _enable(client, token: str, project_id='project-1'):
    assert client.post(f'/api/v1/cloud/projects/{project_id}', headers=_headers(token)).status_code == 200


def test_c9_device_push_pull_ack_metadata_only(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    token = login(client).json()['access_token']
    assert client.get('/api/v1/sync/pull', params={'device_id': str(uuid4()), 'since': 0}).status_code == 401
    device = _device(client, token)
    _enable(client, token)
    event = _event('project-1')
    rejected = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [{**event, 'payload': 'plaintext'}],
    })
    assert rejected.status_code == 422
    pushed = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [event],
    })
    assert pushed.status_code == 200
    assert pushed.json()['results'] == [{'event_id': event['event_id'], 'server_sequence': 1, 'duplicate': False}]
    duplicate = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [event],
    })
    assert duplicate.json()['results'][0]['duplicate'] is True
    conflict = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [{**event, 'revision': 2}],
    })
    assert conflict.status_code == 409 and conflict.json()['detail']['code'] == 'sync_event_id_conflict'
    pull = client.get('/api/v1/sync/pull', headers=_headers(token), params={'device_id': device, 'since': 0})
    assert [item['event_id'] for item in pull.json()['events']] == [event['event_id']]
    assert client.post('/api/v1/sync/ack', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'cursor': 1,
    }).status_code == 204
    invalid_ack = client.post('/api/v1/sync/ack', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'cursor': 2,
    })
    assert invalid_ack.status_code == 422 and invalid_ack.json()['detail']['code'] == 'sync_cursor_invalid'
    with Session(engine) as session:
        columns = {column.name for column in SyncEvent.__table__.columns}
        assert 'payload' not in columns and 'ciphertext' not in columns and 'content' not in columns


def test_c9_project_device_and_user_isolation(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    create_user(engine, username='Other', email='other@example.test')
    first = login(client).json()['access_token']
    second = login(client, 'Other').json()['access_token']
    device = _device(client, first)
    unregistered = client.post('/api/v1/sync/push', headers=_headers(second), json={
        'protocol_version': 1, 'device_id': device, 'events': [],
    })
    assert unregistered.status_code == 409 and unregistered.json()['detail']['code'] == 'sync_device_not_registered'
    assert client.put(f'/api/v1/sync/devices/{device}', headers=_headers(second)).status_code == 200
    disabled = client.post('/api/v1/sync/push', headers=_headers(first), json={
        'protocol_version': 1, 'device_id': device, 'events': [_event('not-enabled')],
    })
    assert disabled.status_code == 409 and disabled.json()['detail']['code'] == 'cloud_project_not_enabled'
    unsupported = client.post('/api/v1/sync/push', headers=_headers(first), json={
        'protocol_version': 99, 'device_id': device, 'events': [],
    })
    assert unsupported.status_code == 422 and unsupported.json()['detail']['code'] == 'sync_protocol_version_unsupported'


def test_c9_duplicate_push_race_has_one_event_and_one_sequence(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event('project-1')
    barrier = Barrier(2)

    def push_once():
        barrier.wait()
        with Session(engine) as session:
            return SyncService().push(session, user_id, UUID(device), [SyncEventEnvelope.model_validate(event)])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: push_once(), range(2)))
    assert {result[0][0].server_sequence for result in results} == {1}
    with Session(engine) as session:
        assert session.query(SyncEvent).filter_by(user_id=user_id, event_id=event['event_id']).count() == 1


def test_c9_sequence_race_serializes_two_devices_per_user(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    first, second = _device(client, token), _device(client, token)
    _enable(client, token)
    barrier = Barrier(2)

    def push_once(device, event):
        barrier.wait()
        with Session(engine) as session:
            return SyncService().push(session, user_id, UUID(device), [SyncEventEnvelope.model_validate(event)])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: push_once(*pair), [(first, _event('project-1')), (second, _event('project-1'))]))
    assert {result[0][0].server_sequence for result in results} == {1, 2}
    with Session(engine) as session:
        assert session.execute(text('SELECT current_sequence FROM sync_user_state WHERE user_id=:user_id'), {'user_id': user_id}).scalar_one() == 2
