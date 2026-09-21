from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.cloud.models import SyncDevice, SyncEvent, SyncUserState, User
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
    assert client.put(f'/api/v1/sync/devices/{device}', headers=_headers(token)).json()['last_ack_cursor'] == 0
    _enable(client, token)
    event = _event('project-1')
    rejected = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [{**event, 'payload': 'plaintext'}],
    })
    assert rejected.status_code == 422
    for field in ('content', 'unexpected'):
        response = client.post('/api/v1/sync/push', headers=_headers(token), json={
            'protocol_version': 1, 'device_id': device, 'events': [{**event, field: 'forbidden'}],
        })
        assert response.status_code == 422
    pushed = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [event],
    })
    assert pushed.status_code == 200
    assert pushed.json()['results'] == [{'event_id': event['event_id'], 'server_sequence': 1, 'duplicate': False}]
    duplicate = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [event],
    })
    assert duplicate.json()['results'][0]['duplicate'] is True
    assert duplicate.json()['current_cursor'] == 1
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
    assert client.post('/api/v1/sync/ack', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'cursor': 0,
    }).status_code == 204
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
    for endpoint, request in (
        ('/api/v1/sync/pull', None),
        ('/api/v1/sync/ack', {'protocol_version': 99, 'device_id': device, 'cursor': 0}),
    ):
        response = (client.get(endpoint, headers=_headers(first), params={'device_id': device, 'since': 0, 'protocol_version': 99})
                    if request is None else client.post(endpoint, headers=_headers(first), json=request))
        assert response.status_code == 422 and response.json()['detail']['code'] == 'sync_protocol_version_unsupported'


def test_c9_batch_pull_tombstone_ack_and_disabled_duplicate_regressions(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    first, second = _device(client, token), _device(client, token)
    _enable(client, token)
    earliest = _event('project-1', updated_at='2030-01-01T00:00:00+00:00')
    later = _event('project-1', updated_at='2020-01-01T00:00:00+00:00')
    tombstone = _event('project-1', operation='delete', deleted_at='2026-09-21T01:00:00+00:00')
    response = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': first, 'events': [earliest, later, tombstone],
    })
    assert [item['server_sequence'] for item in response.json()['results']] == [1, 2, 3]
    with Session(engine) as session:
        assert session.execute(text('SELECT count(*) FROM cloud_projects WHERE user_id=:id'), {'id': user_id}).scalar_one() == 1
    assert client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': first, 'events': [later, later],
    }).json()['results'][1]['duplicate'] is True
    conflict = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': first, 'events': [later, {**later, 'revision': 2}],
    })
    assert conflict.status_code == 409 and conflict.json()['detail']['code'] == 'sync_event_id_conflict'
    atomic = client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': first, 'events': [_event('project-1'), _event('disabled')],
    })
    assert atomic.status_code == 409
    assert client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': first, 'events': [],
    }).json()['current_cursor'] == 3
    assert client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': first, 'events': [_event('project-1') for _ in range(101)],
    }).status_code == 422
    page = client.get('/api/v1/sync/pull', headers=_headers(token), params={'device_id': second, 'since': 0, 'limit': 2}).json()
    assert [event['server_sequence'] for event in page['events']] == [1, 2] and page['has_more'] is True
    final = client.get('/api/v1/sync/pull', headers=_headers(token), params={'device_id': second, 'since': page['next_cursor']}).json()
    assert final['events'][0]['operation'] == 'delete' and final['events'][0]['deleted_at'] is not None
    assert client.get('/api/v1/sync/pull', headers=_headers(token), params={'device_id': second, 'since': 3}).json()['events'] == []
    future = client.get('/api/v1/sync/pull', headers=_headers(token), params={'device_id': second, 'since': 4})
    assert future.status_code == 422 and future.json()['detail']['code'] == 'sync_cursor_invalid'
    assert client.post('/api/v1/sync/ack', headers=_headers(token), json={'protocol_version': 1, 'device_id': first, 'cursor': 3}).status_code == 204
    assert client.post('/api/v1/sync/ack', headers=_headers(token), json={'protocol_version': 1, 'device_id': second, 'cursor': 1}).status_code == 204
    assert client.delete('/api/v1/cloud/projects/project-1', headers=_headers(token)).status_code == 204
    retry = client.post('/api/v1/sync/push', headers=_headers(token), json={'protocol_version': 1, 'device_id': first, 'events': [earliest]})
    assert retry.json()['results'][0] == {'event_id': earliest['event_id'], 'server_sequence': 1, 'duplicate': True}
    disabled_new = client.post('/api/v1/sync/push', headers=_headers(token), json={'protocol_version': 1, 'device_id': first, 'events': [_event('project-1')]})
    assert disabled_new.status_code == 409 and disabled_new.json()['detail']['code'] == 'cloud_project_not_enabled'
    with Session(engine) as session:
        assert session.execute(text('SELECT count(*) FROM cloud_projects WHERE user_id=:id'), {'id': user_id}).scalar_one() == 0


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


def test_c9_device_registration_races_are_idempotent_on_a_fresh_account(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)

    def register_concurrently(device_ids):
        barrier = Barrier(2)
        def register(device_id):
            barrier.wait()
            with Session(engine) as session:
                return SyncService().register_device(session, user_id, device_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(register, device_ids))

    same = uuid4()
    register_concurrently([same, same])
    with Session(engine) as session:
        assert session.execute(text('SELECT count(*) FROM sync_devices WHERE user_id=:user_id'), {'user_id': user_id}).scalar_one() == 1
        assert session.execute(text('SELECT count(*) FROM sync_user_state WHERE user_id=:user_id'), {'user_id': user_id}).scalar_one() == 1

    # A second fresh user proves two different device inserts share only that
    # user's state row; accounts still have independent transaction lanes.
    second_user = create_user(engine, username='Fresh Other', email='fresh-other@example.test')
    user_id = second_user
    register_concurrently([uuid4(), uuid4()])
    with Session(engine) as session:
        assert session.execute(text('SELECT count(*) FROM sync_devices WHERE user_id=:user_id'), {'user_id': second_user}).scalar_one() == 2
        assert session.execute(text('SELECT current_sequence FROM sync_user_state WHERE user_id=:user_id'), {'user_id': second_user}).scalar_one() == 0


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


def test_c9_user_deletion_cascades_only_that_users_sync_metadata(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    assert client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [_event('project-1')],
    }).status_code == 200
    with Session(engine) as session:
        session.delete(session.get(User, user_id))
        session.commit()
    with Session(engine) as session:
        assert session.query(SyncDevice).filter_by(user_id=user_id).count() == 0
        assert session.query(SyncUserState).filter_by(user_id=user_id).count() == 0
        assert session.query(SyncEvent).filter_by(user_id=user_id).count() == 0
