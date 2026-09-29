from __future__ import annotations

import base64
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app.cloud.models import EncryptedObject, SyncEvent, SyncUserState
from backend.app.cloud.schemas import V3EncryptedSyncPushRequest
from test_cloud_auth import cloud_client, create_user, login, migrated_database


def _headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def _object() -> dict:
    return {'crypto_version': 1, 'aad_version': 1,
            'nonce': base64.urlsafe_b64encode(b'n' * 24).decode().rstrip('='),
            'ciphertext': base64.urlsafe_b64encode(b'opaque project metadata ciphertext').decode().rstrip('=')}


def _event(**changes) -> dict:
    event = {'event_id': str(uuid4()), 'project_id': 'project-1', 'entity_id': 'project-1',
             'entity_type': 'project_metadata', 'operation': 'upsert', 'revision': 1,
             'updated_at': datetime.now(timezone.utc).isoformat(), 'deleted_at': None}
    event.update(changes)
    return event


def _request(device: str, event: dict, obj: dict | None = None) -> dict:
    return {'protocol_version': 3, 'encrypted_sync_version': 3, 'device_id': device,
            'items': [{'event': event, 'object': obj or _object()}]}


def test_metadata_v3_schema_rejects_scope_and_unknown_plaintext_fields():
    device = str(uuid4())
    V3EncryptedSyncPushRequest.model_validate(_request(device, _event()))
    with pytest.raises(ValueError):
        V3EncryptedSyncPushRequest.model_validate(_request(device, _event(entity_id='other')))
    with pytest.raises(ValueError):
        V3EncryptedSyncPushRequest.model_validate(_request(device, _event(name='server-visible')))


def test_metadata_v3_dormant_mode_and_opaque_replay(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    token = login(client).json()['access_token']
    device = str(uuid4())
    assert client.put(f'/api/v1/sync/devices/{device}', headers=_headers(token)).status_code == 200
    assert client.post('/api/v1/cloud/projects/project-1', headers=_headers(token)).status_code == 200
    event, obj = _event(), _object()
    request = _request(device, event, obj)
    path = '/api/v3/sync/encrypted/push'
    blocked = client.post(path, headers=_headers(token), json=request)
    assert blocked.status_code == 409
    assert blocked.json()['detail']['code'] == 'sync_transport_mode_incompatible'
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert state is not None
        state.writer_transport_version = 2
        state.cutover_epoch += 1
        session.commit()
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert state is not None
        state.writer_transport_version = 3  # test-only fixture, no public cutover
        state.cutover_epoch += 1
        session.commit()
    first = client.post(path, headers=_headers(token), json=request)
    assert first.status_code == 200, first.text
    assert first.json()['results'][0]['duplicate'] is False
    replay = client.post(path, headers=_headers(token), json=request)
    assert replay.status_code == 200
    assert replay.json()['results'][0]['duplicate'] is True
    missing_project = client.post(path, headers=_headers(token), json=_request(
        device, _event(project_id='not-enabled', entity_id='not-enabled')))
    assert missing_project.status_code == 409
    unregistered = client.post(path, headers=_headers(token), json=_request(str(uuid4()), _event()))
    assert unregistered.status_code == 409
    invalid_identity = client.post(path, headers=_headers(token), json=_request(device, _event(entity_id='other')))
    assert invalid_identity.status_code == 422
    altered = _request(device, event, {**obj, 'nonce': base64.urlsafe_b64encode(b'x' * 24).decode().rstrip('=')})
    assert client.post(path, headers=_headers(token), json=altered).status_code == 409
    pull = client.get('/api/v3/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device, 'since': 0, 'protocol_version': 3, 'encrypted_sync_version': 3,
    })
    assert pull.status_code == 200, pull.text
    assert pull.json()['items'][0]['event']['entity_type'] == 'project_metadata'
    assert pull.json()['items'][0]['object'] == obj
    with Session(engine) as session:
        row = session.query(SyncEvent).filter_by(user_id=user_id, event_id=event['event_id']).one()
        assert row.entity_id == 'project-1'
        encrypted = session.query(EncryptedObject).filter_by(user_id=user_id, event_id=event['event_id']).one()
        assert encrypted.ciphertext == b'opaque project metadata ciphertext'
