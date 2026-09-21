from __future__ import annotations

import base64
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from starlette.requests import Request

from backend.app.cloud.models import EncryptedObject, SyncEvent, SyncUserState
from backend.app.cloud.schemas import (MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES,
                                       MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES,
                                       MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES,
                                       EncryptedSyncPushItem, EncryptedSyncPushRequest,
                                       ObjectEnvelopeDto)
from backend.app.cloud.sync_router import _read_encrypted_push_body
from backend.app.cloud.services import SyncProtocolError, SyncService
from test_cloud_auth import cloud_client, create_user, login, migrated_database


def _headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _device(client, token: str) -> str:
    value = uuid4()
    assert client.put(f'/api/v1/sync/devices/{value}', headers=_headers(token)).status_code == 200
    return str(value)


def _enable(client, token: str, project_id: str = 'project-1') -> None:
    assert client.post(f'/api/v1/cloud/projects/{project_id}', headers=_headers(token)).status_code == 200


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def _event(project_id: str = 'project-1', **extra) -> dict[str, object]:
    value: dict[str, object] = {
        'event_id': str(uuid4()),
        'project_id': project_id,
        'entity_id': 'note-1',
        'entity_type': 'note',
        'operation': 'upsert',
        'revision': 1,
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'deleted_at': None,
    }
    value.update(extra)
    return value


def _object(nonce: bytes = b'n' * 24, ciphertext: bytes = b'ciphertext-with-tag') -> dict[str, object]:
    return {
        'crypto_version': 1,
        'aad_version': 1,
        'nonce': _b64url(nonce),
        'ciphertext': _b64url(ciphertext),
    }


def _encrypted_request(device_id: str, *items: tuple[dict[str, object], dict[str, object]]) -> dict[str, object]:
    return {
        'protocol_version': 1,
        'encrypted_sync_version': 1,
        'device_id': device_id,
        'items': [{'event': event, 'object': encrypted} for event, encrypted in items],
    }


def _push_item(event: dict[str, object], envelope: dict[str, object]) -> EncryptedSyncPushItem:
    return EncryptedSyncPushItem.model_validate({'event': event, 'object': envelope})


def _stream_request(chunks: list[bytes], *, content_length: int | None = None) -> tuple[Request, list[int]]:
    received: list[int] = []

    async def receive():
        index = len(received)
        received.append(index)
        chunk = chunks[index] if index < len(chunks) else b''
        return {'type': 'http.request', 'body': chunk, 'more_body': index < len(chunks) - 1}

    headers = [] if content_length is None else [(b'content-length', str(content_length).encode('ascii'))]
    return Request({'type': 'http', 'method': 'POST', 'path': '/', 'headers': headers}, receive), received


def test_c15_encrypted_push_bounded_stream_exact_limit_content_length_and_chunk_bypass():
    exact_request, _received = _stream_request([b'a' * MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES])
    assert len(asyncio.run(_read_encrypted_push_body(exact_request))) == MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES

    early_request, early_received = _stream_request([b'not-read'], content_length=MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES + 1)
    try:
        asyncio.run(_read_encrypted_push_body(early_request))
        raise AssertionError('expected HTTP 413')
    except HTTPException as error:
        assert error.status_code == 413 and error.detail['code'] == 'encrypted_sync_batch_too_large'
    assert early_received == []

    bypass_request, bypass_received = _stream_request(
        [b'a' * MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES, b'b', b'must-not-be-read'], content_length=1,
    )
    try:
        asyncio.run(_read_encrypted_push_body(bypass_request))
        raise AssertionError('expected HTTP 413')
    except HTTPException as error:
        assert error.status_code == 413 and error.detail['code'] == 'encrypted_sync_batch_too_large'
    assert len(bypass_received) == 2


def test_c15_encrypted_schema_exact_object_and_aggregate_decoded_boundaries():
    exact_object = _object(ciphertext=b'x' * MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES)
    assert len(base64.urlsafe_b64decode(exact_object['ciphertext'] + '==')) == MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES
    ObjectEnvelopeDto.model_validate(exact_object)
    try:
        ObjectEnvelopeDto.model_validate(_object(ciphertext=b'x' * (MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES + 1)))
        raise AssertionError('expected individual ciphertext rejection')
    except ValueError:
        pass

    device_id = str(uuid4())
    half = MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES // 2
    exact = _encrypted_request(device_id, (_event(entity_id='first'), _object(ciphertext=b'a' * half)),
                               (_event(entity_id='second'), _object(ciphertext=b'b' * half)))
    EncryptedSyncPushRequest.model_validate(exact)
    oversized = _encrypted_request(device_id, (_event(entity_id='first'), _object(ciphertext=b'a' * half)),
                                   (_event(entity_id='second'), _object(ciphertext=b'b' * (half + 1))))
    try:
        EncryptedSyncPushRequest.model_validate(oversized)
        raise AssertionError('expected aggregate ciphertext rejection')
    except ValueError:
        pass


def test_c15_encrypted_push_upsert_delete_retry_and_immutable_conflict(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event()
    envelope = _object(ciphertext=b'first encrypted note')

    accepted = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(device, (event, envelope)))
    assert accepted.status_code == 200
    assert accepted.json()['results'] == [{'event_id': event['event_id'], 'server_sequence': 1, 'duplicate': False}]
    with Session(engine) as session:
        stored_event = session.get(SyncEvent, (user_id, event['event_id']))
        stored_object = session.get(EncryptedObject, (user_id, event['event_id']))
        assert stored_event is not None and stored_object is not None
        assert stored_event.operation == 'upsert' and stored_event.server_sequence == 1
        assert stored_object.nonce == b'n' * 24 and stored_object.ciphertext == b'first encrypted note'

    retry = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(device, (event, envelope)))
    assert retry.status_code == 200
    assert retry.json()['results'] == [{'event_id': event['event_id'], 'server_sequence': 1, 'duplicate': True}]
    conflict = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (event, _object(ciphertext=b'changed encrypted note')),
    ))
    assert conflict.status_code == 409 and conflict.json()['detail']['code'] == 'sync_event_id_conflict'
    with Session(engine) as session:
        assert session.get(EncryptedObject, (user_id, event['event_id'])).ciphertext == b'first encrypted note'
        assert session.query(SyncEvent).filter_by(user_id=user_id).count() == 1
        assert session.query(EncryptedObject).filter_by(user_id=user_id).count() == 1

    deleted_at = datetime.now(timezone.utc).isoformat()
    delete = _event(entity_id='note-delete', operation='delete', deleted_at=deleted_at)
    deleted = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (delete, _object(nonce=b'd' * 24, ciphertext=b'encrypted tombstone')),
    ))
    assert deleted.status_code == 200
    with Session(engine) as session:
        stored_event = session.get(SyncEvent, (user_id, delete['event_id']))
        stored_object = session.get(EncryptedObject, (user_id, delete['event_id']))
        assert stored_event.operation == 'delete' and stored_event.deleted_at is not None
        assert stored_object is not None and stored_object.ciphertext == b'encrypted tombstone'


def test_c15_historical_metadata_event_cannot_be_completed_and_batch_is_atomic(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    historical = _event()
    assert client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [historical],
    }).status_code == 200
    incomplete = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (historical, _object()),
    ))
    assert incomplete.status_code == 409
    assert incomplete.json()['detail']['code'] == 'encrypted_sync_event_incomplete'
    with Session(engine) as session:
        assert session.get(SyncEvent, (user_id, historical['event_id'])) is not None
        assert session.get(EncryptedObject, (user_id, historical['event_id'])) is None

    valid = _event(entity_id='valid')
    disabled = _event('disabled-project', entity_id='disabled')
    response = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (valid, _object(ciphertext=b'valid encrypted note')), (disabled, _object(ciphertext=b'disabled encrypted note')),
    ))
    assert response.status_code == 409 and response.json()['detail']['code'] == 'cloud_project_not_enabled'
    with Session(engine) as session:
        assert session.get(SyncEvent, (user_id, valid['event_id'])) is None
        assert session.get(EncryptedObject, (user_id, valid['event_id'])) is None
        assert session.get(SyncEvent, (user_id, disabled['event_id'])) is None
        assert session.get(EncryptedObject, (user_id, disabled['event_id'])) is None
        assert session.get(SyncUserState, user_id).current_sequence == 1


def test_c15_encrypted_pull_scans_global_metadata_gaps_and_c9_stays_metadata_only(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    historical = _event(entity_id='historical')
    encrypted = _event(entity_id='encrypted')
    nonce, ciphertext = b'\x01' * 24, b'opaque bytes for pull'
    assert client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [historical],
    }).status_code == 200
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (encrypted, _object(nonce, ciphertext)),
    )).status_code == 200

    first = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 0, 'limit': 1, 'protocol_version': 1, 'encrypted_sync_version': 1,
    })
    assert first.status_code == 200
    first_page = first.json()
    assert [item['event']['server_sequence'] for item in first_page['items']] == [1]
    assert first_page['items'][0]['object'] is None
    assert first_page['next_cursor'] == 1 and first_page['has_more'] is True

    second = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 1, 'limit': 1, 'protocol_version': 1, 'encrypted_sync_version': 1,
    })
    assert second.status_code == 200
    second_page = second.json()
    assert [item['event']['server_sequence'] for item in second_page['items']] == [2]
    assert second_page['next_cursor'] == 2 and second_page['has_more'] is False
    assert second_page['items'][0]['object'] == {
        'crypto_version': 1, 'aad_version': 1, 'nonce': _b64url(nonce), 'ciphertext': _b64url(ciphertext),
    }
    assert '=' not in second_page['items'][0]['object']['nonce']
    assert '=' not in second_page['items'][0]['object']['ciphertext']

    c9_pull = client.get('/api/v1/sync/pull', headers=_headers(token), params={'device_id': device, 'since': 0})
    assert c9_pull.status_code == 200
    assert all({'object', 'ciphertext', 'nonce'}.isdisjoint(item) for item in c9_pull.json()['events'])
    with Session(engine) as session:
        columns = {column.name for column in SyncEvent.__table__.columns}
        assert {'ciphertext', 'payload', 'content'}.isdisjoint(columns)
        assert session.execute(text('SELECT count(*) FROM encrypted_objects WHERE user_id=:id'), {'id': user_id}).scalar_one() == 1


def test_c15_concurrent_exact_duplicate_uses_one_sequence_and_object(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event()
    envelope = _object(nonce=b'e' * 24, ciphertext=b'exact concurrent ciphertext')
    barrier = Barrier(2)

    def push_once():
        barrier.wait()
        with Session(engine) as session:
            return SyncService().push_encrypted(session, user_id, UUID(device), [_push_item(event, envelope)])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: push_once(), range(2)))
    rows = [result[0][0] for result in results]
    assert sorted(result.duplicate for result in rows) == [False, True]
    assert {result.server_sequence for result in rows} == {1}
    with Session(engine) as session:
        assert session.query(SyncEvent).filter_by(user_id=user_id, event_id=event['event_id']).count() == 1
        stored = session.get(EncryptedObject, (user_id, event['event_id']))
        assert stored is not None and stored.nonce == b'e' * 24 and stored.ciphertext == b'exact concurrent ciphertext'
        assert session.get(SyncUserState, user_id).current_sequence == 1


def test_c15_concurrent_conflicting_object_keeps_one_immutable_winner(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event()
    first = _object(nonce=b'a' * 24, ciphertext=b'concurrent object A')
    second = _object(nonce=b'b' * 24, ciphertext=b'concurrent object B')
    barrier = Barrier(2)

    def push_once(envelope):
        barrier.wait()
        try:
            with Session(engine) as session:
                return ('accepted', SyncService().push_encrypted(session, user_id, UUID(device), [_push_item(event, envelope)]))
        except SyncProtocolError as error:
            return ('error', error.code)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(push_once, (first, second)))
    accepted = [value for kind, value in results if kind == 'accepted']
    assert len(accepted) == 1 and accepted[0][0][0].duplicate is False
    assert [value for kind, value in results if kind == 'error'] == ['sync_event_id_conflict']
    with Session(engine) as session:
        assert session.query(SyncEvent).filter_by(user_id=user_id, event_id=event['event_id']).count() == 1
        stored = session.get(EncryptedObject, (user_id, event['event_id']))
        assert stored is not None and (stored.nonce, stored.ciphertext) in {
            (b'a' * 24, b'concurrent object A'), (b'b' * 24, b'concurrent object B'),
        }
        assert session.get(SyncUserState, user_id).current_sequence == 1


def test_c15_same_batch_duplicates_and_disabled_retry_semantics(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event()
    envelope = _object(ciphertext=b'batch duplicate object')
    exact = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (event, envelope), (event, envelope),
    ))
    assert exact.status_code == 200
    assert exact.json()['results'] == [
        {'event_id': event['event_id'], 'server_sequence': 1, 'duplicate': False},
        {'event_id': event['event_id'], 'server_sequence': 1, 'duplicate': True},
    ]
    assert client.delete('/api/v1/cloud/projects/project-1', headers=_headers(token)).status_code == 204
    retry = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(device, (event, envelope)))
    assert retry.status_code == 200 and retry.json()['results'][0]['duplicate'] is True
    conflict = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (event, _object(ciphertext=b'changed after disable')),
    ))
    assert conflict.status_code == 409 and conflict.json()['detail']['code'] == 'sync_event_id_conflict'
    disabled = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (_event(), _object(ciphertext=b'new disabled object')),
    ))
    assert disabled.status_code == 409 and disabled.json()['detail']['code'] == 'cloud_project_not_enabled'
    with Session(engine) as session:
        assert session.query(SyncEvent).filter_by(user_id=user_id).count() == 1
        assert session.query(EncryptedObject).filter_by(user_id=user_id).count() == 1
        assert session.get(SyncUserState, user_id).current_sequence == 1


def test_c15_same_batch_conflict_rolls_back_intermediate_flush(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event()
    response = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (event, _object(ciphertext=b'first batch object')),
        (event, _object(ciphertext=b'conflicting batch object')),
    ))
    assert response.status_code == 409 and response.json()['detail']['code'] == 'sync_event_id_conflict'
    with Session(engine) as session:
        assert session.get(SyncEvent, (user_id, event['event_id'])) is None
        assert session.get(EncryptedObject, (user_id, event['event_id'])) is None
        assert session.get(SyncUserState, user_id).current_sequence == 0


def test_c15_encrypted_transport_auth_device_versions_binary_and_scope_validation(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    other_id = create_user(engine, username='Other', email='other@example.test')
    token = login(client).json()['access_token']
    other_token = login(client, 'Other').json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    event = _event()
    request = _encrypted_request(device, (event, _object()))
    assert client.post('/api/v1/sync/encrypted/push', json=request).status_code == 401
    assert client.get('/api/v1/sync/encrypted/pull', params={'device_id': device, 'since': 0}).status_code == 401
    unregistered = client.post('/api/v1/sync/encrypted/push', headers=_headers(other_token), json=request)
    assert unregistered.status_code == 409 and unregistered.json()['detail']['code'] == 'sync_device_not_registered'

    for encrypted_version in (0, 2):
        response = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json={
            **request, 'encrypted_sync_version': encrypted_version,
        })
        assert response.status_code == 422 and response.json()['detail']['code'] == 'encrypted_sync_version_unsupported'
    unsupported_protocol = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json={
        **request, 'protocol_version': 2,
    })
    assert unsupported_protocol.status_code == 422 and unsupported_protocol.json()['detail']['code'] == 'sync_protocol_version_unsupported'
    for changed in ({'crypto_version': 2}, {'aad_version': 2}):
        response = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
            device, (_event(), {**_object(), **changed}),
        ))
        assert response.status_code == 422 and response.json()['detail']['code'] == 'encrypted_sync_version_unsupported'

    invalid_envelopes = [
        {'nonce': _b64url(b'a' * 23)}, {'nonce': _b64url(b'a' * 25)},
        {'nonce': _b64url(b'a' * 24) + '='}, {'nonce': '*invalid*'},
        {'ciphertext': _b64url(b'a' * 15)}, {'ciphertext': _b64url(b'a' * 16) + '='},
        {'ciphertext': '*invalid*'},
    ]
    for invalid in invalid_envelopes:
        response = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
            device, (_event(), {**_object(), **invalid}),
        ))
        assert response.status_code == 422
    for invalid_event in (_event(entity_type='future_document'), _event(operation='event')):
        response = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
            device, (invalid_event, _object()),
        ))
        assert response.status_code == 422 and response.json()['detail']['code'] == 'encrypted_sync_event_unsupported'
    missing_object = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json={
        'protocol_version': 1, 'encrypted_sync_version': 1, 'device_id': device, 'items': [{'event': _event()}],
    })
    assert missing_object.status_code == 422
    with Session(engine) as session:
        assert session.query(SyncEvent).filter_by(user_id=user_id).count() == 0
        assert session.query(EncryptedObject).filter_by(user_id=user_id).count() == 0
        assert session.get(SyncUserState, user_id).current_sequence == 0
        assert session.query(SyncEvent).filter_by(user_id=other_id).count() == 0


def test_c15_owner_isolation_future_type_pull_and_mixed_global_pagination(cloud_client):
    client, engine = cloud_client
    first_id = create_user(engine)
    second_id = create_user(engine, username='Other', email='other@example.test')
    first_token = login(client).json()['access_token']
    second_token = login(client, 'Other').json()['access_token']
    first_device, second_device = _device(client, first_token), _device(client, second_token)
    _enable(client, first_token)
    _enable(client, second_token)
    shared_event_id = str(uuid4())
    first_event = _event(event_id=shared_event_id, entity_id='first-note')
    second_event = _event(event_id=shared_event_id, entity_id='second-note')
    first_object = _object(nonce=b'1' * 24, ciphertext=b'first user opaque object')
    second_object = _object(nonce=b'2' * 24, ciphertext=b'second user opaque object')
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(first_token), json=_encrypted_request(
        first_device, (first_event, first_object),
    )).status_code == 200
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(second_token), json=_encrypted_request(
        second_device, (second_event, second_object),
    )).status_code == 200
    with Session(engine) as session:
        assert session.get(EncryptedObject, (first_id, shared_event_id)).ciphertext == b'first user opaque object'
        assert session.get(EncryptedObject, (second_id, shared_event_id)).ciphertext == b'second user opaque object'

    # Build the C18-compatible future item directly: C15 push remains note-only,
    # but generic encrypted pull must preserve opaque future entity types.
    historical_one = _event(entity_id='historical-one')
    historical_two = _event(entity_id='historical-two')
    assert client.post('/api/v1/sync/push', headers=_headers(first_token), json={
        'protocol_version': 1, 'device_id': first_device, 'events': [historical_one],
    }).status_code == 200
    future_event_id = uuid4()
    future_nonce, future_ciphertext = b'f' * 24, b'future opaque object'
    with Session(engine) as session:
        with session.begin():
            state = session.get(SyncUserState, first_id)
            state.current_sequence += 1
            sequence = state.current_sequence
            future = SyncEvent(
                user_id=first_id, event_id=future_event_id, device_id=UUID(first_device),
                project_id='project-1', entity_id='document-1', entity_type='future_document',
                operation='upsert', revision=1, updated_at=datetime.now(timezone.utc), deleted_at=None,
                server_sequence=sequence,
            )
            session.add(future)
            session.flush()
            session.add(EncryptedObject(
                user_id=first_id, event_id=future_event_id, crypto_version=1, aad_version=1,
                nonce=future_nonce, ciphertext=future_ciphertext,
            ))
    assert client.post('/api/v1/sync/push', headers=_headers(first_token), json={
        'protocol_version': 1, 'device_id': first_device, 'events': [historical_two],
    }).status_code == 200

    seen = []
    cursor = 0
    while True:
        response = client.get('/api/v1/sync/encrypted/pull', headers=_headers(first_token), params={
            'device_id': first_device, 'since': cursor, 'limit': 1,
        })
        assert response.status_code == 200
        page = response.json()
        if not page['items']:
            break
        item = page['items'][0]
        seen.append((item['event']['server_sequence'], item['event']['entity_type'], item['object']))
        assert page['next_cursor'] == item['event']['server_sequence']
        cursor = page['next_cursor']
        if not page['has_more']:
            break
    assert [sequence for sequence, _type, _object_value in seen] == [1, 2, 3, 4]
    assert [value is None for _sequence, _type, value in seen] == [False, True, False, True]
    future_item = next(value for _sequence, entity_type, value in seen if entity_type == 'future_document')
    assert future_item == {
        'crypto_version': 1, 'aad_version': 1,
        'nonce': _b64url(future_nonce), 'ciphertext': _b64url(future_ciphertext),
    }
    first_pull = client.get('/api/v1/sync/encrypted/pull', headers=_headers(first_token), params={
        'device_id': first_device, 'since': 0,
    }).json()
    second_pull = client.get('/api/v1/sync/encrypted/pull', headers=_headers(second_token), params={
        'device_id': second_device, 'since': 0,
    }).json()
    assert all(item['object'] != second_object for item in first_pull['items'])
    assert all(item['object'] != first_object for item in second_pull['items'])


def test_c15_encrypted_push_manual_validation_preserves_openapi_and_safe_malformed_contract(cloud_client):
    client, _engine = cloud_client
    token = login(client).json()['access_token']
    malformed = client.post('/api/v1/sync/encrypted/push', headers={
        **_headers(token), 'Content-Type': 'application/json',
    }, content=b'{"protocol_version":')
    assert malformed.status_code == 422
    assert isinstance(malformed.json()['detail'], list)

    schema = client.get('/openapi.json').json()
    request_body = schema['paths']['/api/v1/sync/encrypted/push']['post']['requestBody']
    body_schema = request_body['content']['application/json']['schema']
    assert request_body['required'] is True
    assert set(body_schema['properties']) == {
        'protocol_version', 'encrypted_sync_version', 'device_id', 'items',
    }


def test_c15_encrypted_push_rejects_actual_raw_body_over_limit_despite_small_content_length(cloud_client):
    client, _engine = cloud_client
    token = login(client).json()['access_token']
    body = json.dumps({'protocol_version': 1}).encode() + b' ' * MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES
    response = client.post('/api/v1/sync/encrypted/push', headers={
        **_headers(token), 'Content-Type': 'application/json', 'Content-Length': '1',
    }, content=body)
    assert response.status_code == 413
    assert response.json()['detail']['code'] == 'encrypted_sync_batch_too_large'


def test_c15_descriptor_first_pull_blocks_oversized_object_without_skipping_cursor(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)

    safe_event = _event(entity_id='safe')
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=_encrypted_request(
        device, (safe_event, _object(ciphertext=b'safe encrypted object')),
    )).status_code == 200
    blocked_event = _event(entity_id='blocked')
    assert client.post('/api/v1/sync/push', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device, 'events': [blocked_event],
    }).status_code == 200
    with Session(engine) as session:
        with session.begin():
            session.add(EncryptedObject(
                user_id=user_id, event_id=UUID(str(blocked_event['event_id'])), crypto_version=1, aad_version=1,
                nonce=b'o' * 24, ciphertext=b'x' * (MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES + 1),
            ))

    prefix = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 0,
    })
    assert prefix.status_code == 200
    assert [item['event']['entity_id'] for item in prefix.json()['items']] == ['safe']
    assert prefix.json()['next_cursor'] == 1 and prefix.json()['has_more'] is True

    blocked = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 1,
    })
    assert blocked.status_code == 413
    assert blocked.json()['detail']['code'] == 'encrypted_sync_object_too_large'
    retry = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 1,
    })
    assert retry.status_code == 413


def test_c15_descriptor_first_pull_uses_exact_aggregate_prefix_and_second_ciphertext_query(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    _enable(client, token)
    object_size = MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES // 2
    event_ids = []
    with Session(engine) as session:
        with session.begin():
            state = session.get(SyncUserState, user_id)
            for sequence in range(1, 4):
                event_id = uuid4()
                event_ids.append(event_id)
                session.add(SyncEvent(
                    user_id=user_id, event_id=event_id, device_id=UUID(device), project_id='project-1',
                    entity_id=f'note-{sequence}', entity_type='note', operation='upsert', revision=1,
                    updated_at=datetime.now(timezone.utc), deleted_at=None, server_sequence=sequence,
                ))
                session.flush()
                session.add(EncryptedObject(
                    user_id=user_id, event_id=event_id, crypto_version=1, aad_version=1,
                    nonce=bytes([sequence]) * 24, ciphertext=bytes([sequence]) * object_size,
                ))
            state.current_sequence = 3

    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        if 'sync_events' in statement and 'encrypted_objects' in statement:
            statements.append(statement)

    from sqlalchemy import event as sqlalchemy_event
    sqlalchemy_event.listen(engine, 'before_cursor_execute', capture)
    try:
        response = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
            'device_id': device, 'since': 0,
        })
    finally:
        sqlalchemy_event.remove(engine, 'before_cursor_execute', capture)
    assert response.status_code == 200
    page = response.json()
    assert [item['event']['server_sequence'] for item in page['items']] == [1, 2]
    assert page['next_cursor'] == 2 and page['has_more'] is True
    assert len(base64.urlsafe_b64decode(page['items'][0]['object']['ciphertext'] + '==')) == object_size
    assert len(statements) == 2
    assert 'octet_length(encrypted_objects.ciphertext)' in statements[0]
    assert 'encrypted_objects.ciphertext AS encrypted_objects_ciphertext' not in statements[0]
    assert 'encrypted_objects.ciphertext AS encrypted_objects_ciphertext' in statements[1]

    final = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 2,
    }).json()
    assert [item['event']['server_sequence'] for item in final['items']] == [3]
    assert final['next_cursor'] == 3 and final['has_more'] is False
