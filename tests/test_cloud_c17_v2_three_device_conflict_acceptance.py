from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.cloud.models import EncryptedObject, SyncDevice, SyncEvent, SyncUserState
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c15_headless_cross_runtime import NOTE_ID, PROJECT_ID, _crypto_bridge, _native_bridge, _provision_device
from test_cloud_c17_v2_two_device_acceptance import _pull_apply_ack
from test_cloud_encrypted_sync import _headers


def _call(tmp_path: Path, device: tuple[Path, dict], user_id: str, action: str, **values):
    database, identity = device
    return _native_bridge(tmp_path, {
        'action': action, 'database_path': str(database),
        'local_account_id': identity['local_account_id'], 'device_id': identity['device_id'],
        'canonical_user_id': user_id, **values,
    })


def _pull_one(client, token: str, device: tuple[Path, dict], since: int, event_id: str):
    response = client.get('/api/v2/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': device[1]['device_id'], 'since': since, 'limit': 100,
        'protocol_version': 2, 'encrypted_sync_version': 2,
    })
    assert response.status_code == 200, response.text
    page = response.json()
    assert page['items'][0]['event']['event_id'] == event_id
    return page['items'][0]


def _receive_note(client, token: str, tmp_path: Path, device: tuple[Path, dict],
                  user_id: str, amk: list[int], since: int, event_id: str):
    item = _pull_one(client, token, device, since, event_id)
    opened = _crypto_bridge(tmp_path, {
        'action': 'open', 'canonical_user_id': user_id, 'amk': amk, 'item': item,
    })
    result = _call(tmp_path, device, user_id, 'receive_apply_prepare',
                   item=item, expected_cursor=since, next_cursor=since + 1,
                   opened={key: opened[key] for key in (
                       'crypto_version', 'aad_version', 'nonce', 'ciphertext', 'plaintext',
                   )})
    return item, opened, result


def _ack(client, token: str, tmp_path: Path, device: tuple[Path, dict],
         user_id: str, expected: int, candidate: int):
    assert candidate >= expected
    accepted = client.post('/api/v2/sync/encrypted/ack', headers=_headers(token), json={
        'protocol_version': 2, 'encrypted_sync_version': 2,
        'device_id': device[1]['device_id'], 'cursor': candidate,
    })
    assert accepted.status_code == 204, accepted.text
    committed = _call(tmp_path, device, user_id, 'commit_ack',
                      expected_old_ack_cursor=expected, acknowledged_cursor=candidate,
                      project_id=PROJECT_ID)
    assert committed['result'] == 'advanced'
    assert (committed['pull_cursor'], committed['ack_cursor']) == (candidate, candidate)


def _state(device: tuple[Path, dict]):
    database, identity = device
    assert database.is_file()
    with sqlite3.connect(database) as connection:
        account = identity['local_account_id']
        note_row = connection.execute('SELECT payload_json FROM notes WHERE id=?', (NOTE_ID,)).fetchone()
        head = connection.execute(
            "SELECT head_event_id,head_sync_revision FROM cloud_sync_entities "
            "WHERE account_id=? AND project_id=? AND entity_id=? AND entity_type='note'",
            (account, PROJECT_ID, NOTE_ID),
        ).fetchone()
        cursors = connection.execute(
            'SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id=?', (account,),
        ).fetchone()
        groups = connection.execute(
            'SELECT group_id,common_parent_event_id,tip_revision,generation,lifecycle '
            'FROM cloud_sync_note_conflict_groups WHERE account_id=? ORDER BY created_at', (account,),
        ).fetchall()
        versions = connection.execute(
            'SELECT event_id,parent_event_id,revision,source,snapshot_json '
            'FROM cloud_sync_note_conflict_versions WHERE account_id=? ORDER BY event_id', (account,),
        ).fetchall()
        tips = connection.execute(
            'SELECT event_id FROM cloud_sync_note_conflict_tips ORDER BY event_id',
        ).fetchall()
        inbox = connection.execute(
            'SELECT event_id,state FROM cloud_sync_inbox WHERE account_id=? ORDER BY server_sequence',
            (account,),
        ).fetchall()
        history = connection.execute(
            'SELECT event_id,parent_event_id,revision FROM cloud_sync_note_causal_history '
            'WHERE account_id=? ORDER BY server_sequence', (account,),
        ).fetchall()
        ledger = connection.execute(
            'SELECT resolution_event_id,parent_event_ids_json,local_conflict_group_id '
            'FROM cloud_sync_note_applied_resolutions WHERE account_id=?', (account,),
        ).fetchall()
        edges = connection.execute(
            'SELECT resolution_event_id,parent_ordinal,parent_event_id '
            'FROM cloud_sync_note_applied_resolution_parents WHERE account_id=? ORDER BY parent_ordinal',
            (account,),
        ).fetchall()
        outbox = connection.execute(
            'SELECT event_id,parent_event_id,revision,lifecycle FROM cloud_sync_outbox '
            'WHERE account_id=? ORDER BY local_ordinal', (account,),
        ).fetchall()
        orphans = connection.execute(
            "SELECT count(*) FROM cloud_sync_inbox WHERE account_id=? AND state='orphan'", (account,),
        ).fetchone()[0]
    return {'note': json.loads(note_row[0]) if note_row else None, 'head': head,
            'cursors': cursors, 'groups': groups, 'versions': versions, 'tips': tips,
            'inbox': inbox, 'history': history, 'ledger': ledger, 'edges': edges,
            'outbox': outbox, 'orphans': orphans}


def _local_event(client, token: str, tmp_path: Path, device: tuple[Path, dict],
                 user_id: str, amk: list[int], title: str, content: str):
    intent = _call(tmp_path, device, user_id, 'local_note_edit', project_id=PROJECT_ID,
                   entity_id=NOTE_ID, patch={'title': title, 'content': content})
    assert intent['event']['operation'] == 'upsert'
    assert intent['note']['title'] == title and intent['note']['content'] == content
    push = _seal_local_intent(tmp_path, device, user_id, amk, intent)
    _call(tmp_path, device, user_id, 'seal_local_note',
          event_id=intent['event']['event_id'], mutation_generation=intent['mutation_generation'],
          object=push['items'][0]['object'])
    response = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=push)
    assert response.status_code == 200, response.text
    receipt = response.json()['results'][0]
    assert receipt['event_id'] == intent['event']['event_id'] and receipt['duplicate'] is False
    _call(tmp_path, device, user_id, 'ordinary_receipt', event_id=receipt['event_id'],
          server_sequence=receipt['server_sequence'])
    return intent, push, receipt['server_sequence']


def _seal_local_intent(tmp_path: Path, device: tuple[Path, dict], user_id: str,
                       amk: list[int], intent: dict):
    event = intent['event']
    prepared = _crypto_bridge(tmp_path, {
        'action': 'seal_intent', 'canonical_user_id': user_id, 'amk': amk,
        'intent': {
            **event, 'account_id': device[1]['local_account_id'],
            'device_id': device[1]['device_id'],
            'parent_event_id': intent['parent_event_id'],
            'local_ordinal': 1, 'mutation_generation': intent['mutation_generation'],
            'snapshot_json': intent['snapshot_json'], 'seal_state': 'pending',
            'seal_attempt_count': 0, 'last_error_code': None, 'next_attempt_at': None,
        },
    })
    push = {'protocol_version': 2, 'encrypted_sync_version': 2,
            'device_id': device[1]['device_id'], 'items': [{
                'event': prepared['event'], 'object': prepared['object'],
            }]}
    assert push['items'][0]['event']['event_id'] == event['event_id']
    return push


def test_c17_three_file_backed_devices_resolve_and_continue_after_resolution(cloud_client, tmp_path):
    client, engine = cloud_client
    user_id = str(create_user(engine))
    token = login(client).json()['access_token']
    a, b, c = (_provision_device(tmp_path, f'device-{name}', user_id) for name in 'abc')
    assert len({str(a[0]), str(b[0]), str(c[0])}) == 3
    assert len({a[1]['local_account_id'], b[1]['local_account_id'], c[1]['local_account_id']}) == 3
    assert len({a[1]['device_id'], b[1]['device_id'], c[1]['device_id']}) == 3
    for device in (a, b, c):
        registered = client.put(f"/api/v1/sync/devices/{device[1]['device_id']}", headers=_headers(token))
        assert registered.status_code == 200, registered.text
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}', headers=_headers(token)).status_code == 200

    r1 = str(uuid4())
    base = ('Private common base', '<p>Private common body</p>')
    timestamp = '2026-09-23T00:00:00.000000Z'
    sealed = _crypto_bridge(tmp_path, {
        'action': 'seal', 'canonical_user_id': user_id, 'device_id': a[1]['device_id'],
        'event': {'event_id': r1, 'project_id': PROJECT_ID, 'entity_id': NOTE_ID,
                  'entity_type': 'note', 'operation': 'upsert', 'revision': 1,
                  'updated_at': timestamp, 'deleted_at': None},
        'note': {'id': NOTE_ID, 'project_id': PROJECT_ID, 'stage_id': None,
                 'source_type': 'project', 'source_map_id': None, 'source_node_id': None,
                 'content_format': 'html', 'title': base[0], 'content': base[1],
                 'checklist': [], 'color': 'default', 'pinned': False, 'archived': False,
                 'sort_order': 0, 'tags': [], 'created_at': timestamp,
                 'updated_at': timestamp, 'metadata': {}},
    })
    assert all(value not in json.dumps(sealed['push']) for value in base)
    amk = sealed['amk']
    assert len(amk) == 32
    pushed = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=sealed['push'])
    assert pushed.status_code == 200 and pushed.json()['results'][0]['server_sequence'] == 1
    for device in (a, b, c):
        _pull_apply_ack(client, token, tmp_path, device[0], device[1], user_id,
                        amk, 1, 0, r1, None, 1, *base)
        state = _state(device)
        assert state['head'] == (r1, 1) and state['cursors'] == (1, 1)
        assert state['note']['content'] == base[1]
        assert state['inbox'] == [(r1, 'applied')]
    cutover = client.post('/api/v2/sync/encrypted/cutover', headers=_headers(token),
                          json={'expected_cutover_epoch': 0})
    assert cutover.status_code == 200
    assert (cutover.json()['writer_transport_version'], cutover.json()['cutover_epoch']) == (2, 1)

    # Both mutations are made against R1 before either device sees the other's branch.
    b_intent = _call(tmp_path, b, user_id, 'local_note_edit', project_id=PROJECT_ID,
                     entity_id=NOTE_ID, patch={'title': 'Private B2', 'content': '<p>Private B branch</p>'})
    c_intent = _call(tmp_path, c, user_id, 'local_note_edit', project_id=PROJECT_ID,
                     entity_id=NOTE_ID, patch={'title': 'Private C2', 'content': '<p>Private C branch</p>'})
    b2, c2 = b_intent['event']['event_id'], c_intent['event']['event_id']
    assert b2 != c2
    for intent in (b_intent, c_intent):
        assert (intent['event']['revision'], intent['parent_event_id']) == (2, r1)
    assert _state(b)['cursors'] == _state(c)['cursors'] == (1, 1)

    def publish_intent(device, intent):
        push = _seal_local_intent(tmp_path, device, user_id, amk, intent)
        _call(tmp_path, device, user_id, 'seal_local_note',
              event_id=intent['event']['event_id'], mutation_generation=intent['mutation_generation'],
              object=push['items'][0]['object'])
        result = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=push)
        assert result.status_code == 200, result.text
        row = result.json()['results'][0]
        assert row['duplicate'] is False
        _call(tmp_path, device, user_id, 'ordinary_receipt',
              event_id=row['event_id'], server_sequence=row['server_sequence'])
        return push, row['server_sequence']

    _, b_sequence = publish_intent(b, b_intent)
    assert b_sequence == 2
    _, _, b_self = _receive_note(client, token, tmp_path, b, user_id, amk, 1, b2)
    assert b_self['apply_result'] == 'self_echo_applied'
    _, _, c_conflict = _receive_note(client, token, tmp_path, c, user_id, amk, 1, b2)
    assert c_conflict['apply_result'] == 'conflict'
    assert c_conflict['inbox_state'] == 'conflict_preserved'
    assert c_conflict['note']['content'] == c_intent['note']['content']
    assert c_conflict['ack']['candidate_cursor'] == 2  # receipt proof, not resolution
    c_early = _state(c)  # reopened while the local C2 branch is still unsealed
    assert c_early['groups'][0][3:] == (1, 'open')
    assert {row[0] for row in c_early['versions']} == {b2, c2}
    _, c_sequence = publish_intent(c, c_intent)
    assert c_sequence == 3

    _, _, a_b = _receive_note(client, token, tmp_path, a, user_id, amk, 1, b2)
    assert a_b['apply_result'] == 'applied'
    _, _, a_c = _receive_note(client, token, tmp_path, a, user_id, amk, 2, c2)
    assert a_c['apply_result'] == 'conflict' and a_c['inbox_state'] == 'conflict_preserved'
    _, _, b_c = _receive_note(client, token, tmp_path, b, user_id, amk, 2, c2)
    assert b_c['apply_result'] == 'conflict' and b_c['inbox_state'] == 'conflict_preserved'
    _, _, c_self = _receive_note(client, token, tmp_path, c, user_id, amk, 2, c2)
    assert c_self['apply_result'] == 'self_echo_applied'
    for device in (a, b, c):
        state = _state(device)  # reopen after preservation
        assert len(state['groups']) == 1
        group_id, common_parent, tip_revision, generation, lifecycle = state['groups'][0]
        assert (common_parent, tip_revision, generation, lifecycle) == (r1, 2, 1, 'open')
        assert {tip[0] for tip in state['tips']} == {b2, c2}
        assert {version[0] for version in state['versions']} == {b2, c2}
        assert {version[1] for version in state['versions']} == {r1}
        assert {version[2] for version in state['versions']} == {2}
        assert len({version[4] for version in state['versions']}) == 2
        assert state['head'][1] == 2 and state['head'][0] in {b2, c2}
        assert state['cursors'] == (3, 1)
        assert state['inbox'][-1][1] in {'applied', 'conflict_preserved'}
        _ack(client, token, tmp_path, device, user_id, 1, 3)

    a_state = _state(a)
    group_id = a_state['groups'][0][0]
    parents = sorted((b2, c2))
    res = str(uuid4())
    merge_title, merge_content = 'Private merged Note', '<p>Private B and C merged result</p>'
    merge_time = '2026-09-23T00:00:03.000000Z'
    merged_note = dict(a_state['note'], title=merge_title, content=merge_content, updated_at=merge_time)
    merged_note.pop('revision')  # Local Notes revision is absent from the wire record.
    payload = {
        'version': 2,
        'header': {'event_id': res, 'parent_event_id': parents[0],
                   'additional_parent_event_ids': parents[1:], 'project_id': PROJECT_ID,
                   'entity_id': NOTE_ID, 'entity_type': 'note', 'operation': 'resolution',
                   'revision': 3, 'updated_at': merge_time},
        'mutation': 'resolution',
        'resolution': {'conflict_group_id': group_id, 'conflict_generation': 1,
                       'resolved_event_ids': parents, 'strategy': 'manual_merge'},
        'result': {'operation': 'upsert', 'note': merged_note},
    }
    encoded = _crypto_bridge(tmp_path, {'action': 'resolution_encode', 'payload': payload})
    canonical_payload = encoded['canonical_payload']
    canonical_bytes = list(base64.urlsafe_b64decode(canonical_payload + '=' * (-len(canonical_payload) % 4)))
    assert encoded['decoded'] == payload
    applied = _call(tmp_path, a, user_id, 'prepare_apply_resolution', canonical_payload=canonical_bytes)
    assert applied == {'prepared': 'Prepared', 'applied': 'Applied'}
    post_local = _state(a)  # restart after local application
    assert post_local['note']['content'] == merge_content
    assert post_local['head'] == a_state['head']  # RES becomes head after its authenticated echo.
    assert post_local['groups'][0][4] == 'resolving'
    intents = _call(tmp_path, a, user_id, 'list_resolution_intents')
    assert len(intents) == 1 and intents[0]['event_id'] == res
    assert intents[0]['canonical_payload'] == canonical_payload
    resolution_object = _crypto_bridge(tmp_path, {
        'action': 'resolution_seal', 'canonical_user_id': user_id,
        'amk': amk, 'canonical_payload': canonical_payload,
        'event': payload['header'], 'device_id': a[1]['device_id'],
    })['object']
    assert _call(tmp_path, a, user_id, 'seal_resolution', event_id=res,
                 project_id=PROJECT_ID, entity_id=NOTE_ID,
                 canonical_payload=canonical_payload, object=resolution_object) == 'sealed'
    uploads = _call(tmp_path, a, user_id, 'resolution_uploads', event_id=res)
    assert uploads['readiness'] == {'event_id': res, 'ready': True}
    assert len(uploads['uploads']) == 1
    upload = uploads['uploads'][0]
    assert (upload['event_id'], upload['operation'], upload['revision']) == (res, 'resolution', 3)
    assert upload['envelope'] == resolution_object
    resolution_push = {'protocol_version': 2, 'encrypted_sync_version': 2,
                       'device_id': a[1]['device_id'], 'items': [{
                           'event': {'event_id': res, 'project_id': PROJECT_ID,
                                     'entity_id': NOTE_ID, 'entity_type': 'note',
                                     'operation': 'resolution', 'revision': 3,
                                     'updated_at': merge_time, 'deleted_at': None},
                           'object': resolution_object,
                       }]}
    resolution_response = client.post('/api/v2/sync/encrypted/push',
                                      headers=_headers(token), json=resolution_push)
    assert resolution_response.status_code == 200, resolution_response.text
    assert resolution_response.json()['results'] == [
        {'event_id': res, 'server_sequence': 4, 'duplicate': False},
    ]
    assert _call(tmp_path, a, user_id, 'resolution_receipt',
                 event_id=res, server_sequence=4) == ['accepted']
    retry = client.post('/api/v2/sync/encrypted/push', headers=_headers(token), json=resolution_push)
    assert retry.status_code == 200 and retry.json()['results'] == [
        {'event_id': res, 'server_sequence': 4, 'duplicate': True},
    ]
    for device in (a, b, c):
        item = _pull_one(client, token, device, 3, res)
        opened = _crypto_bridge(tmp_path, {
            'action': 'resolution_open', 'canonical_user_id': user_id, 'amk': amk, 'item': item,
        })
        assert opened['decoded'] == payload
        result = _call(tmp_path, device, user_id, 'receive_resolution',
                       item=item, opened={key: opened[key] for key in (
                           'crypto_version', 'aad_version', 'nonce', 'ciphertext', 'plaintext',
                       )}, expected_cursor=3, next_cursor=4)
        assert result['result'] == ('reconciled' if device == a else 'applied')
        assert result['ack'] == {'current_ack_cursor': 3, 'candidate_cursor': 4}
        state = _state(device)  # restart after resolution apply
        assert state['note']['content'] == merge_content and state['head'] == (res, 3)
        assert state['groups'][0][4] == 'resolved'
        assert len(state['ledger']) == 1 and state['ledger'][0][0] == res
        assert json.loads(state['ledger'][0][1]) == parents
        assert [(edge[1], edge[2]) for edge in state['edges']] == list(enumerate(parents))
        assert state['inbox'][-1] == (res, 'applied')
        _ack(client, token, tmp_path, device, user_id, 3, 4)

    b4_intent, _, b4_sequence = _local_event(
        client, token, tmp_path, b, user_id, amk,
        'Private post-resolution child', '<p>Private B4 continuation</p>',
    )
    b4 = b4_intent['event']['event_id']
    assert b4_sequence == 5
    assert (b4_intent['event']['revision'], b4_intent['parent_event_id']) == (4, res)
    for device in (a, b, c):
        _, opened, result = _receive_note(client, token, tmp_path, device, user_id, amk, 4, b4)
        assert opened['decoded']['version'] == 1
        assert opened['decoded']['header']['parent_event_id'] == res
        assert result['apply_result'] == ('self_echo_applied' if device == b else 'applied')
        assert result['ack'] == {'current_ack_cursor': 4, 'candidate_cursor': 5}
        _ack(client, token, tmp_path, device, user_id, 4, 5)
    for device in (a, b, c):
        state = _state(device)  # independent final disk reopen
        assert state['note']['content'] == '<p>Private B4 continuation</p>'
        assert state['head'] == (b4, 4) and state['cursors'] == (5, 5)
        assert state['groups'][0][4] == 'resolved' and state['orphans'] == 0
        assert len(state['versions']) == 2 and len(state['ledger']) == 1
        assert [(edge[1], edge[2]) for edge in state['edges']] == list(enumerate(parents))
        assert state['history'][-1] == (b4, res, 4)
        assert state['inbox'][-1] == (b4, 'applied')
    assert (b4, res, 4, 'accepted') in _state(b)['outbox']

    with Session(engine) as session:
        server = session.get(SyncUserState, user_id)
        assert (server.current_sequence, server.writer_transport_version, server.cutover_epoch) == (5, 2, 1)
        events = session.query(SyncEvent).filter_by(user_id=user_id).order_by(SyncEvent.server_sequence).all()
        assert [(str(row.event_id), row.server_sequence) for row in events] == [
            (r1, 1), (b2, 2), (c2, 3), (res, 4), (b4, 5),
        ]
        assert [row.operation for row in events] == ['upsert', 'upsert', 'upsert', 'resolution', 'upsert']
        objects = session.query(EncryptedObject).filter_by(user_id=user_id).all()
        assert len(objects) == 5 and {str(row.event_id) for row in objects} == {r1, b2, c2, res, b4}
        private_values = (base[0], base[1], 'Private B2', '<p>Private B branch</p>',
                          'Private C2', '<p>Private C branch</p>', merge_title,
                          merge_content, '<p>Private B4 continuation</p>')
        for encrypted in objects:
            assert (encrypted.crypto_version, encrypted.aad_version) == (1, 1)
            assert len(encrypted.nonce) == 24
            assert all(value.encode() not in encrypted.ciphertext for value in private_values)
        devices = session.query(SyncDevice).filter_by(user_id=user_id).all()
        assert {str(row.device_id): row.last_ack_sequence for row in devices} == {
            device[1]['device_id']: 5 for device in (a, b, c)
        }
