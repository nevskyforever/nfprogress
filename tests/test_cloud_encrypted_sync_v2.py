from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.cloud.models import CloudProject, EncryptedObject, SyncDevice, SyncEvent, SyncUserState
from backend.app.cloud.schemas import EncryptedSyncPushRequest
from backend.app.cloud.services import SyncProtocolError, SyncService
from test_cloud_auth import cloud_client, create_user, login, migrated_database


def _headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _device(client, token: str) -> str:
    device = str(uuid4())
    assert client.put(f'/api/v1/sync/devices/{device}', headers=_headers(token)).status_code == 200
    return device


def _enable(client, token: str, project_id: str = 'project-1') -> None:
    assert client.post(f'/api/v1/cloud/projects/{project_id}', headers=_headers(token)).status_code == 200


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def _event(**extra) -> dict[str, object]:
    value: dict[str, object] = {
        'event_id': str(uuid4()), 'project_id': 'project-1', 'entity_id': 'note-1',
        'entity_type': 'note', 'operation': 'upsert', 'revision': 1,
        'updated_at': datetime.now(timezone.utc).isoformat(), 'deleted_at': None,
    }
    value.update(extra)
    return value


def _object(nonce: bytes = b'n' * 24, ciphertext: bytes = b'opaque encrypted object') -> dict[str, object]:
    return {'crypto_version': 1, 'aad_version': 1, 'nonce': _b64(nonce), 'ciphertext': _b64(ciphertext)}


def _v1_request(device_id: str, event: dict[str, object], envelope: dict[str, object]) -> dict[str, object]:
    return {'protocol_version': 1, 'encrypted_sync_version': 1, 'device_id': device_id, 'items': [{'event': event, 'object': envelope}]}


def _v2_request(device_id: str, *items: tuple[dict[str, object], dict[str, object]]) -> dict[str, object]:
    return {'protocol_version': 2, 'encrypted_sync_version': 2, 'device_id': device_id,
            'items': [{'event': event, 'object': envelope} for event, envelope in items]}


def _set_mode(engine, user_id, mode: int) -> None:
    # Isolated fixture bypasses readiness to test malformed-history v2 pull.
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert state is not None
        state.writer_transport_version = mode
        state.cutover_epoch += 1
        session.commit()


def test_c17_v2_migration_defaults_capabilities_and_mode_one_rejection(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert state is not None and (state.writer_transport_version, state.cutover_epoch) == (1, 0)

    capabilities = client.get('/api/v2/sync/encrypted/capabilities', headers=_headers(token))
    assert capabilities.status_code == 200
    assert capabilities.json() == {'supported_transport_version': 2, 'writer_transport_version': 1, 'cutover_epoch': 0}
    v1 = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_v1_request(device, _event(), _object()))
    assert v1.status_code == 200
    for method, path, kwargs in (
        ('post', '/api/v2/sync/encrypted/push', {'json': _v2_request(device, (_event(), _object()))}),
        ('get', '/api/v2/sync/encrypted/pull', {'params': {'device_id': device, 'since': 0, 'limit': 1, 'protocol_version': 2, 'encrypted_sync_version': 2}}),
        ('post', '/api/v2/sync/encrypted/ack', {'json': {'protocol_version': 2, 'encrypted_sync_version': 2, 'device_id': device, 'cursor': 0}}),
    ):
        response = getattr(client, method)(path, headers=_headers(token), **kwargs)
        assert response.status_code == 409 and response.json()['detail']['code'] == 'sync_transport_mode_incompatible'


def test_c17_v2_mode_two_is_exclusive_and_registration_remains_version_neutral(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    _set_mode(engine, user_id, 2)
    new_device = str(uuid4())
    assert client.put(f'/api/v1/sync/devices/{new_device}', headers=_headers(token)).status_code == 200
    for method, path, kwargs in (
        ('post', '/api/v1/sync/push', {'json': {'protocol_version': 1, 'device_id': device, 'events': []}}),
        ('post', '/api/v1/sync/encrypted/push', {'json': _v1_request(device, _event(), _object())}),
        ('get', '/api/v1/sync/pull', {'params': {'device_id': device, 'since': 0, 'limit': 1, 'protocol_version': 1}}),
        ('get', '/api/v1/sync/encrypted/pull', {'params': {'device_id': device, 'since': 0, 'limit': 1, 'protocol_version': 1, 'encrypted_sync_version': 1}}),
        ('post', '/api/v1/sync/ack', {'json': {'protocol_version': 1, 'device_id': device, 'cursor': 0}}),
    ):
        response = getattr(client, method)(path, headers=_headers(token), **kwargs)
        assert response.status_code == 409 and response.json()['detail']['code'] == 'sync_transport_mode_incompatible'
    assert client.get('/api/v2/sync/encrypted/capabilities', headers=_headers(token)).json()['cutover_epoch'] == 1


def test_c17_v2_cutover_epoch_cannot_decrease_or_change_mode_without_increment(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    _device(client, token)
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert state is not None
        state.cutover_epoch = -1
        try:
            session.commit()
            raise AssertionError('expected cutover epoch constraint rejection')
        except Exception:
            session.rollback()
        state = session.get(SyncUserState, user_id)
        state.cutover_epoch = 9_007_199_254_740_992
        try:
            session.commit()
            raise AssertionError('expected cutover epoch safe-integer rejection')
        except Exception:
            session.rollback()
        state = session.get(SyncUserState, user_id)
        state.writer_transport_version = 2
        try:
            session.commit()
            raise AssertionError('expected mode change epoch rejection')
        except Exception:
            session.rollback()
        state = session.get(SyncUserState, user_id)
        state.writer_transport_version = 2
        state.cutover_epoch = 1
        session.commit()
        state.writer_transport_version = 1
        state.cutover_epoch = 2
        try:
            session.commit()
            raise AssertionError('expected transport downgrade rejection')
        except Exception:
            session.rollback()


def test_c17_v2_opaque_resolution_replay_historical_pull_and_ack_without_pruning(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    historical, historical_object = _event(entity_id='old-note'), _object(b'a' * 24, b'old v1 ciphertext')
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_v1_request(device, historical, historical_object)).status_code == 200
    _set_mode(engine, user_id, 2)
    resolution = _event(entity_id='resolved-note', operation='resolution', revision=2)
    envelope = _object(b'b' * 24, b'opaque v2 resolution ciphertext')
    accepted = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=_v2_request(device, (resolution, envelope)))
    assert accepted.status_code == 200 and accepted.json()['results'][0]['server_sequence'] == 2
    replay = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=_v2_request(device, (resolution, envelope)))
    assert replay.status_code == 200 and replay.json()['results'][0]['duplicate'] is True
    changed = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=_v2_request(device, (resolution, _object(b'c' * 24, b'changed opaque ciphertext'))))
    assert changed.status_code == 409 and changed.json()['detail']['code'] == 'sync_event_id_conflict'
    pulled = client.get('/api/v2/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 0, 'limit': 10, 'protocol_version': 2, 'encrypted_sync_version': 2,
    })
    assert pulled.status_code == 200
    assert [(row['event']['operation'], row['event']['server_sequence']) for row in pulled.json()['items']] == [('upsert', 1), ('resolution', 2)]
    assert pulled.json()['items'][0]['object'] == historical_object
    assert client.post('/api/v2/sync/encrypted/ack', headers=_headers(token), json={
        'protocol_version': 2, 'encrypted_sync_version': 2, 'device_id': device, 'cursor': 2,
    }).status_code == 204
    with Session(engine) as session:
        assert session.get(SyncUserState, user_id).current_sequence == 2
        assert session.query(SyncEvent).filter_by(user_id=user_id).count() == 2
        assert session.query(EncryptedObject).filter_by(user_id=user_id).count() == 2


def test_c17_v2_rejects_invalid_versions_and_unsafe_metadata_and_blocks_legacy_metadata_gap(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    _set_mode(engine, user_id, 2)
    for event in (
        _event(entity_type='document'),
        _event(operation='event'),
        _event(operation='resolution', revision=1),
        _event(operation='resolution', deleted_at=datetime.now(timezone.utc).isoformat(), revision=2),
    ):
        assert client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=_v2_request(device, (event, _object()))).status_code == 422
    bad = _v2_request(device, (_event(), _object()))
    bad['encrypted_sync_version'] = 1
    assert client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=bad).status_code == 422
    # A v2 pull must fail closed rather than skip an historical metadata-only event.
    with Session(engine) as session:
        session.execute(text("INSERT INTO sync_events(user_id,event_id,device_id,project_id,entity_id,entity_type,operation,revision,updated_at,deleted_at,server_sequence) VALUES (:user,:event,:device,'project-1','legacy','note','event',1,now(),NULL,1)"), {
            'user': user_id, 'event': uuid4(), 'device': device,
        })
        session.get(SyncUserState, user_id).current_sequence = 1
        session.commit()
    response = client.get('/api/v2/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 0, 'limit': 1, 'protocol_version': 2, 'encrypted_sync_version': 2,
    })
    assert response.status_code == 409 and response.json()['detail']['code'] == 'encrypted_sync_event_incomplete'


def _cutover(client, token: str, epoch: int = 0):
    return client.post('/api/v2/sync/encrypted/cutover', headers=_headers(token),
                       json={'expected_cutover_epoch': epoch})


def test_c17_cutover_preserves_history_devices_ack_and_projects(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    first, second = _device(client, token), _device(client, token)
    _enable(client, token)
    event, encrypted = _event(), _object()
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(token),
                       json=_v1_request(first, event, encrypted)).status_code == 200
    assert client.post('/api/v1/sync/encrypted/ack', headers=_headers(token),
                       json={'protocol_version': 1, 'device_id': first, 'cursor': 1}).status_code == 204
    with Session(engine) as session:
        before = (
            [(row.event_id, row.server_sequence) for row in session.query(SyncEvent).filter_by(user_id=user_id).all()],
            [(row.event_id, row.ciphertext) for row in session.query(EncryptedObject).filter_by(user_id=user_id).all()],
            [(str(row.device_id), row.last_ack_sequence) for row in session.query(SyncDevice).filter_by(user_id=user_id).order_by(SyncDevice.device_id).all()],
            [(row.project_id, row.bootstrap_state) for row in session.query(CloudProject).filter_by(user_id=user_id).all()],
        )
    assert _cutover(client, token).json() == {
        'supported_transport_version': 2, 'writer_transport_version': 2, 'cutover_epoch': 1,
    }
    assert _cutover(client, token).json()['cutover_epoch'] == 1
    assert client.get('/api/v2/sync/encrypted/capabilities', headers=_headers(token)).json()['writer_transport_version'] == 2
    for method, path, kwargs in (
        ('post', '/api/v1/sync/encrypted/push', {'json': _v1_request(first, _event(), _object())}),
        ('get', '/api/v1/sync/encrypted/pull', {'params': {'device_id': first, 'since': 0, 'limit': 10, 'protocol_version': 1, 'encrypted_sync_version': 1}}),
        ('post', '/api/v1/sync/encrypted/ack', {'json': {'protocol_version': 1, 'device_id': first, 'cursor': 1}}),
    ):
        response = getattr(client, method)(path, headers=_headers(token), **kwargs)
        assert response.status_code == 409 and response.json()['detail']['code'] == 'sync_transport_mode_incompatible'
    pulled = client.get('/api/v2/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': second, 'since': 0, 'limit': 10, 'protocol_version': 2, 'encrypted_sync_version': 2,
    })
    assert pulled.status_code == 200 and pulled.json()['items'][0]['object'] == encrypted
    with Session(engine) as session:
        after = (
            [(row.event_id, row.server_sequence) for row in session.query(SyncEvent).filter_by(user_id=user_id).all()],
            [(row.event_id, row.ciphertext) for row in session.query(EncryptedObject).filter_by(user_id=user_id).all()],
            [(str(row.device_id), row.last_ack_sequence) for row in session.query(SyncDevice).filter_by(user_id=user_id).order_by(SyncDevice.device_id).all()],
            [(row.project_id, row.bootstrap_state) for row in session.query(CloudProject).filter_by(user_id=user_id).all()],
        )
    assert after == before
    new_event = _event(entity_id='new')
    assert client.post('/api/v2/sync/encrypted/push', headers=_headers(token),
                       json=_v2_request(first, (new_event, _object()))).status_code == 200
    assert client.post('/api/v2/sync/encrypted/ack', headers=_headers(token), json={
        'protocol_version': 2, 'encrypted_sync_version': 2, 'device_id': second, 'cursor': 2,
    }).status_code == 204


def test_c17_cutover_stale_epoch_and_exhaustion_leave_mode_one(cloud_client):
    client, engine = cloud_client
    assert client.post('/api/v2/sync/encrypted/cutover', json={'expected_cutover_epoch': 0}).status_code == 401
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    for invalid in (-1, 1.5, 9_007_199_254_740_992, True):
        assert _cutover(client, token, invalid).status_code == 422
    assert client.post('/api/v2/sync/encrypted/cutover', headers=_headers(token),
                       json={'expected_cutover_epoch': 0, 'user_id': str(user_id)}).status_code == 422
    with Session(engine) as session:
        state = SyncUserState(user_id=user_id, cutover_epoch=1)
        session.add(state)
        session.commit()
    response = _cutover(client, token, 0)
    assert response.status_code == 409 and response.json()['detail']['code'] == 'sync_transport_cutover_stale'
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert (state.writer_transport_version, state.cutover_epoch) == (1, 1)
        state.cutover_epoch = 9_007_199_254_740_991
        session.commit()
    response = _cutover(client, token, 9_007_199_254_740_991)
    assert response.status_code == 409 and response.json()['detail']['code'] == 'sync_transport_cutover_epoch_exhausted'
    assert client.get('/api/v2/sync/encrypted/capabilities', headers=_headers(token)).json()['writer_transport_version'] == 1


@pytest.mark.parametrize('entity_type,operation,object_version', [
    ('note', 'event', None), ('future', 'upsert', 1), ('note', 'upsert', None),
    ('note', 'upsert', 2), ('note', 'upsert', -1),
])
def test_c17_cutover_blocks_incompatible_history_at_any_sequence(cloud_client, entity_type, operation, object_version):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(token),
                       json=_v1_request(device, _event(), _object())).status_code == 200
    with Session(engine) as session:
        event_id = uuid4()
        session.add(SyncEvent(user_id=user_id, event_id=event_id, device_id=UUID(device),
            project_id='project-1', entity_id='late', entity_type=entity_type,
            operation=operation, revision=1, updated_at=datetime.now(timezone.utc),
            server_sequence=2))
        session.flush()
        if object_version is not None:
            session.add(EncryptedObject(user_id=user_id, event_id=event_id,
                crypto_version=object_version if object_version > 0 else 1,
                aad_version=2 if object_version < 0 else 1,
                nonce=b'n' * 24, ciphertext=b'opaque encrypted object'))
        session.get(SyncUserState, user_id).current_sequence = 2
        session.commit()
    response = _cutover(client, token)
    assert response.status_code == 409 and response.json()['detail']['code'] == 'sync_transport_cutover_blocked'
    assert client.get('/api/v2/sync/encrypted/capabilities', headers=_headers(token)).json() == {
        'supported_transport_version': 2, 'writer_transport_version': 1, 'cutover_epoch': 0,
    }


def test_c17_concurrent_cutover_increments_epoch_once(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)

    def attempt():
        with Session(engine) as session:
            return SyncService().cutover_to_v2(session, user_id, 0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results == [(2, 1), (2, 1)]
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert (state.writer_transport_version, state.cutover_epoch) == (2, 1)


def test_c17_v1_push_and_cutover_serialize_on_user_state(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event()
    item = EncryptedSyncPushRequest.model_validate(_v1_request(device, event, _object())).items[0]
    start = Barrier(2)

    def push():
        with Session(engine) as session:
            start.wait()
            try:
                SyncService().push_encrypted(session, user_id, UUID(device), [item])
                return 'accepted'
            except SyncProtocolError as error:
                return error.code

    def cutover():
        with Session(engine) as session:
            start.wait()
            return SyncService().cutover_to_v2(session, user_id, 0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        pushed = pool.submit(push)
        switched = pool.submit(cutover)
        assert switched.result() == (2, 1)
        outcome = pushed.result()
    assert outcome in ('accepted', 'sync_transport_mode_incompatible')
    with Session(engine) as session:
        events = session.query(SyncEvent).filter_by(user_id=user_id).all()
        assert len(events) == (1 if outcome == 'accepted' else 0)
        assert session.query(EncryptedObject).filter_by(user_id=user_id).count() == len(events)
