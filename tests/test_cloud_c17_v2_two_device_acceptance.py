from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.cloud.models import EncryptedObject, SyncDevice, SyncEvent, SyncUserState
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c15_headless_cross_runtime import (
    NOTE_ID, PROJECT_ID, _crypto_bridge, _native_bridge, _provision_device,
)
from test_cloud_encrypted_sync import _headers


def _seal_note(tmp_path: Path, user_id: str, device_id: str, amk: list[int] | None,
               event_id: str, revision: int, parent: str | None,
               title: str, content: str) -> dict:
    timestamp = f'2026-09-23T00:00:0{revision - 1}.000000Z'
    request = {
        'action': 'seal', 'canonical_user_id': user_id, 'device_id': device_id,
        'event': {
            'event_id': event_id, 'project_id': PROJECT_ID, 'entity_id': NOTE_ID,
            'entity_type': 'note', 'operation': 'upsert', 'revision': revision,
            'updated_at': timestamp, 'deleted_at': None,
        },
        'note': {
            'id': NOTE_ID, 'project_id': PROJECT_ID, 'stage_id': None,
            'source_type': 'project', 'source_map_id': None, 'source_node_id': None,
            'content_format': 'html', 'title': title, 'content': content,
            'checklist': [], 'color': 'default', 'pinned': False, 'archived': False,
            'sort_order': 0, 'tags': [],
            'created_at': '2026-09-23T00:00:00.000000Z',
            'updated_at': timestamp, 'metadata': {},
        },
    }
    if amk is not None:
        request['amk'] = amk
    if parent is not None:
        request['parent_event_id'] = parent
    sealed = _crypto_bridge(tmp_path, request)
    wire = json.dumps(sealed['push'])
    assert title not in wire and content not in wire and 'amk' not in wire
    return sealed


def _pull_apply_ack(client, token: str, tmp_path: Path, database: Path,
                    identity: dict, user_id: str, amk: list[int],
                    version: int, since: int, event_id: str, parent: str | None,
                    revision: int, title: str, content: str) -> dict:
    prefix = f'/api/v{version}/sync/encrypted'
    pulled = client.get(f'{prefix}/pull', headers=_headers(token), params={
        'device_id': identity['device_id'], 'since': since, 'limit': 100,
        'protocol_version': version, 'encrypted_sync_version': version,
    })
    assert pulled.status_code == 200, pulled.text
    page = pulled.json()
    assert page['has_more'] is False
    assert len(page['items']) == 1
    item = page['items'][0]
    assert item['event']['event_id'] == event_id
    assert item['event']['server_sequence'] == since + 1
    assert page['next_cursor'] == since + 1
    opened = _crypto_bridge(tmp_path, {
        'action': 'open', 'canonical_user_id': user_id, 'amk': amk, 'item': item,
    })
    assert opened['decoded']['mutation'] == ('create' if revision == 1 else 'update')
    assert opened['decoded']['header']['parent_event_id'] == parent
    assert opened['decoded']['note']['title'] == title
    assert opened['decoded']['note']['content'] == content
    applied = _native_bridge(tmp_path, {
        'action': 'receive_apply_prepare', 'database_path': str(database),
        'local_account_id': identity['local_account_id'],
        'device_id': identity['device_id'], 'canonical_user_id': user_id,
        'item': item, 'expected_cursor': since, 'next_cursor': page['next_cursor'],
        'opened': {key: opened[key] for key in (
            'crypto_version', 'aad_version', 'nonce', 'ciphertext', 'plaintext',
        )},
    })
    assert applied['apply_result'] == 'applied'
    assert applied['inbox_state'] == 'applied'
    assert applied['note']['title'] == title
    assert applied['note']['content'] == content
    assert applied['head_event_id'] == event_id
    assert applied['head_revision'] == revision
    assert applied['ack'] == {
        'current_ack_cursor': since, 'candidate_cursor': since + 1,
    }
    ack_body = {
        'protocol_version': version, 'device_id': identity['device_id'],
        'cursor': since + 1,
    }
    if version == 2:
        ack_body['encrypted_sync_version'] = 2
    acknowledged = client.post(
        '/api/v1/sync/ack' if version == 1 else f'{prefix}/ack',
        headers=_headers(token), json=ack_body,
    )
    assert acknowledged.status_code == 204, acknowledged.text
    if version == 2 and revision == 2:
        replay = client.post(f'{prefix}/ack', headers=_headers(token), json=ack_body)
        assert replay.status_code == 204, replay.text
    committed = _native_bridge(tmp_path, {
        'action': 'commit_ack', 'database_path': str(database),
        'local_account_id': identity['local_account_id'],
        'device_id': identity['device_id'], 'canonical_user_id': user_id,
        'expected_old_ack_cursor': since, 'acknowledged_cursor': since + 1,
        'project_id': PROJECT_ID,
    })
    assert committed == {
        'result': 'advanced', 'pull_cursor': since + 1,
        'ack_cursor': since + 1, 'note_count': 1,
    }
    return item


def _reopened_state(database: Path, account_id: str) -> tuple:
    with sqlite3.connect(database) as connection:
        note = json.loads(connection.execute(
            'SELECT payload_json FROM notes WHERE id=?', (NOTE_ID,),
        ).fetchone()[0])
        head = connection.execute(
            "SELECT head_event_id,head_sync_revision FROM cloud_sync_entities "
            "WHERE account_id=? AND project_id=? AND entity_id=? AND entity_type='note'",
            (account_id, PROJECT_ID, NOTE_ID),
        ).fetchone()
        cursors = connection.execute(
            'SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id=?',
            (account_id,),
        ).fetchone()
        history = connection.execute(
            'SELECT event_id,parent_event_id,revision,server_sequence '
            'FROM cloud_sync_note_causal_history WHERE account_id=? ORDER BY server_sequence',
            (account_id,),
        ).fetchall()
        inbox = connection.execute(
            'SELECT event_id,state FROM cloud_sync_inbox WHERE account_id=? ORDER BY server_sequence',
            (account_id,),
        ).fetchall()
    return note, head, cursors, history, inbox


def test_c17_real_cutover_two_file_backed_devices_continue_bidirectionally(cloud_client, tmp_path):
    client, engine = cloud_client
    user_id = str(create_user(engine))
    token = login(client).json()['access_token']
    database_a, device_a = _provision_device(tmp_path, 'device-a', user_id)
    database_b, device_b = _provision_device(tmp_path, 'device-b', user_id)
    assert database_a != database_b
    assert device_a['local_account_id'] != device_b['local_account_id']
    assert device_a['device_id'] != device_b['device_id']
    for device in (device_a, device_b):
        registered = client.put(
            f"/api/v1/sync/devices/{device['device_id']}", headers=_headers(token),
        )
        assert registered.status_code == 200, registered.text
    assert client.post(
        f'/api/v1/cloud/projects/{PROJECT_ID}', headers=_headers(token),
    ).status_code == 200
    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert state is not None
        assert (state.writer_transport_version, state.cutover_epoch) == (1, 0)

    create_id, b_update_id, a_update_id = (str(uuid4()) for _ in range(3))
    notes = [
        ('Private initial title', '<p>Private initial body</p>'),
        ('Private B edit', '<p>Private B body</p>'),
        ('Private A edit', '<p>Private A final body</p>'),
    ]
    first = _seal_note(tmp_path, user_id, device_a['device_id'], None,
                       create_id, 1, None, *notes[0])
    amk = first['amk']
    assert len(amk) == 32
    pushed = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=first['push'])
    assert pushed.status_code == 200, pushed.text
    assert pushed.json()['results'] == [
        {'event_id': create_id, 'server_sequence': 1, 'duplicate': False},
    ]
    _pull_apply_ack(client, token, tmp_path, database_a, device_a, user_id,
                    amk, 1, 0, create_id, None, 1, *notes[0])
    _pull_apply_ack(client, token, tmp_path, database_b, device_b, user_id,
                    amk, 1, 0, create_id, None, 1, *notes[0])

    cutover = client.post('/api/v2/sync/encrypted/cutover', headers=_headers(token),
                          json={'expected_cutover_epoch': 0})
    assert cutover.status_code == 200, cutover.text
    assert cutover.json() == {
        'supported_transport_version': 2, 'writer_transport_version': 2, 'cutover_epoch': 1,
    }
    assert client.get('/api/v2/sync/encrypted/capabilities', headers=_headers(token)).json() == cutover.json()
    historical = client.get('/api/v2/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device_b['device_id'], 'since': 0, 'limit': 100,
        'protocol_version': 2, 'encrypted_sync_version': 2,
    })
    assert historical.status_code == 200, historical.text
    historical_item = historical.json()['items'][0]
    assert historical_item['event']['event_id'] == create_id
    assert historical_item['object'] == first['push']['items'][0]['object']
    historical_opened = _crypto_bridge(tmp_path, {
        'action': 'open', 'canonical_user_id': user_id, 'amk': amk,
        'item': historical_item,
    })
    assert historical_opened['decoded']['note']['content'] == notes[0][1]
    rejected = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device_a['device_id'], 'since': 1, 'limit': 100,
        'protocol_version': 1, 'encrypted_sync_version': 1,
    })
    assert rejected.status_code == 409
    assert rejected.json()['detail']['code'] == 'sync_transport_mode_incompatible'

    def push_update(device: dict, event_id: str, revision: int,
                    parent: str, title: str, content: str) -> dict:
        sealed = _seal_note(tmp_path, user_id, device['device_id'], amk,
                            event_id, revision, parent, title, content)
        request = {**sealed['push'], 'protocol_version': 2, 'encrypted_sync_version': 2}
        accepted = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=request)
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()['results'] == [
            {'event_id': event_id, 'server_sequence': revision, 'duplicate': False},
        ]
        retry = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=request)
        assert retry.status_code == 200, retry.text
        assert retry.json()['results'] == [
            {'event_id': event_id, 'server_sequence': revision, 'duplicate': True},
        ]
        return request['items'][0]['object']

    b_object = push_update(device_b, b_update_id, 2, create_id, *notes[1])
    b_self = _pull_apply_ack(client, token, tmp_path, database_b, device_b, user_id,
                             amk, 2, 1, b_update_id, create_id, 2, *notes[1])
    assert _reopened_state(database_a, device_a['local_account_id'])[2] == (1, 1)
    assert _reopened_state(database_b, device_b['local_account_id'])[2] == (2, 2)
    with Session(engine) as session:
        acknowledgements = session.query(SyncDevice).filter_by(user_id=user_id).all()
        assert {str(row.device_id): row.last_ack_sequence for row in acknowledgements} == {
            device_a['device_id']: 1, device_b['device_id']: 2,
        }
    a_received = _pull_apply_ack(client, token, tmp_path, database_a, device_a, user_id,
                                  amk, 2, 1, b_update_id, create_id, 2, *notes[1])
    assert b_self['object'] == a_received['object'] == b_object

    a_object = push_update(device_a, a_update_id, 3, b_update_id, *notes[2])
    _pull_apply_ack(client, token, tmp_path, database_a, device_a, user_id,
                    amk, 2, 2, a_update_id, b_update_id, 3, *notes[2])
    b_received = _pull_apply_ack(client, token, tmp_path, database_b, device_b, user_id,
                                  amk, 2, 2, a_update_id, b_update_id, 3, *notes[2])
    assert b_received['object'] == a_object

    expected_history = [
        (create_id, None, 1, 1), (b_update_id, create_id, 2, 2),
        (a_update_id, b_update_id, 3, 3),
    ]
    for database, identity in ((database_a, device_a), (database_b, device_b)):
        note, head, cursors, history, inbox = _reopened_state(
            database, identity['local_account_id'],
        )
        assert note['id'] == NOTE_ID
        assert (note['title'], note['content']) == notes[2]
        assert head == (a_update_id, 3)
        assert cursors == (3, 3)
        assert history == expected_history
        assert inbox == [(event_id, 'applied') for event_id, _, _, _ in expected_history]

    with Session(engine) as session:
        state = session.get(SyncUserState, user_id)
        assert state is not None
        assert (state.current_sequence, state.writer_transport_version, state.cutover_epoch) == (3, 2, 1)
        events = session.query(SyncEvent).filter_by(user_id=user_id).order_by(SyncEvent.server_sequence).all()
        assert [(str(row.event_id), str(row.device_id), row.server_sequence) for row in events] == [
            (create_id, device_a['device_id'], 1),
            (b_update_id, device_b['device_id'], 2),
            (a_update_id, device_a['device_id'], 3),
        ]
        objects = session.query(EncryptedObject).filter_by(user_id=user_id).all()
        assert len(objects) == 3
        assert {str(row.event_id) for row in objects} == {create_id, b_update_id, a_update_id}
        for encrypted in objects:
            assert (encrypted.crypto_version, encrypted.aad_version) == (1, 1)
            assert len(encrypted.nonce) == 24
            assert all(value.encode() not in encrypted.ciphertext for note in notes for value in note)
        devices = session.query(SyncDevice).filter_by(user_id=user_id).all()
        assert {str(row.device_id): row.last_ack_sequence for row in devices} == {
            device_a['device_id']: 3, device_b['device_id']: 3,
        }
