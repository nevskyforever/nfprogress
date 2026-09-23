from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.cloud.models import EncryptedObject, SyncDevice, SyncEvent
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_encrypted_sync import _encrypted_request, _headers, _object


def _event(*, revision: int, operation: str = 'upsert') -> dict[str, object]:
    return {
        'event_id': str(uuid4()), 'project_id': 'project-1', 'entity_id': 'note-1',
        'entity_type': 'note', 'operation': operation, 'revision': revision,
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'deleted_at': datetime.now(timezone.utc).isoformat() if operation == 'delete' else None,
    }


def _register(client, token: str) -> str:
    device_id = str(uuid4())
    assert client.put(f'/api/v1/sync/devices/{device_id}', headers=_headers(token)).status_code == 200
    return device_id


def _pull(client, token: str, device_id: str, since: int) -> dict[str, object]:
    response = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device_id, 'since': since, 'limit': 100,
        'protocol_version': 1, 'encrypted_sync_version': 1,
    })
    assert response.status_code == 200
    return response.json()


def _ack(client, token: str, device_id: str, cursor: int) -> None:
    assert client.post('/api/v1/sync/ack', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': device_id, 'cursor': cursor,
    }).status_code == 204


def test_c15_two_device_encrypted_transport_retry_and_independent_ack(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device_a, device_b = _register(client, token), _register(client, token)
    assert device_a != device_b
    assert client.post('/api/v1/cloud/projects/project-1', headers=_headers(token)).status_code == 200

    create = _event(revision=1)
    create_object = _object(nonce=b'a' * 24, ciphertext=b'opaque-create-ciphertext')
    request = _encrypted_request(device_a, (create, create_object))
    accepted = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=request)
    assert accepted.status_code == 200
    assert accepted.json()['results'] == [{'event_id': create['event_id'], 'server_sequence': 1, 'duplicate': False}]

    # Lost upload response: replay the exact immutable envelope after server commit.
    replay = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=request)
    assert replay.status_code == 200
    assert replay.json()['results'] == [{'event_id': create['event_id'], 'server_sequence': 1, 'duplicate': True}]
    first_b = _pull(client, token, device_b, 0)
    assert first_b['next_cursor'] == 1
    assert first_b['items'][0]['event']['event_id'] == create['event_id']
    assert first_b['items'][0]['object'] == create_object
    _ack(client, token, device_b, 1)

    update = _event(revision=2)
    update_object = _object(nonce=b'b' * 24, ciphertext=b'opaque-update-ciphertext')
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=
                       _encrypted_request(device_b, (update, update_object))).status_code == 200
    first_a = _pull(client, token, device_a, 0)
    assert [item['event']['server_sequence'] for item in first_a['items']] == [1, 2]
    _ack(client, token, device_a, 2)

    delete = _event(revision=3, operation='delete')
    delete_object = _object(nonce=b'c' * 24, ciphertext=b'opaque-delete-tombstone')
    assert client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=
                       _encrypted_request(device_a, (delete, delete_object))).status_code == 200
    final_b = _pull(client, token, device_b, 1)
    assert [item['event']['operation'] for item in final_b['items']] == ['upsert', 'delete']
    assert final_b['next_cursor'] == 3

    # Lost ACK response: repeating the same monotonic ACK is safe.
    _ack(client, token, device_b, 3)
    _ack(client, token, device_b, 3)
    with Session(engine) as session:
        a = session.get(SyncDevice, (user_id, device_a))
        b = session.get(SyncDevice, (user_id, device_b))
        assert a is not None and a.last_ack_sequence == 2
        assert b is not None and b.last_ack_sequence == 3
        assert session.query(SyncEvent).filter_by(user_id=user_id).count() == 3
        objects = session.query(EncryptedObject).filter_by(user_id=user_id).all()
        assert len(objects) == 3
        server_bytes = b''.join(item.ciphertext for item in objects)
        assert b'note plaintext' not in server_bytes
        assert {item.nonce for item in objects} == {b'a' * 24, b'b' * 24, b'c' * 24}
