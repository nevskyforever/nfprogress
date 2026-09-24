from __future__ import annotations

from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c15_headless_cross_runtime import (
    PROJECT_ID, TIMESTAMP, _crypto_bridge, _headers, _native_bridge,
)


def _note(note_id: str, title: str) -> dict[str, object]:
    return {
        'id': note_id, 'project_id': PROJECT_ID, 'stage_id': None, 'source_type': 'project',
        'source_map_id': None, 'source_node_id': None, 'content_format': 'html',
        'title': title, 'content': f'<p>{title} private body</p>', 'checklist': [],
        'color': 'default', 'pinned': False, 'archived': False, 'sort_order': 0,
        'tags': [], 'created_at': TIMESTAMP, 'updated_at': TIMESTAMP,
        'revision': 0, 'metadata': {},
    }


def _native(tmp_path, database_path, identity, action, **values):
    return _native_bridge(tmp_path, {
        'action': action, 'database_path': str(database_path),
        'local_account_id': identity['local_account_id'],
        'device_id': identity['device_id'], 'project_id': PROJECT_ID, **values,
    })


def _apply_page(client, tmp_path, token, database_path, identity, canonical_user_id, amk):
    pulled = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': identity['device_id'], 'since': 0, 'limit': 100,
        'protocol_version': 1, 'encrypted_sync_version': 1,
    })
    assert pulled.status_code == 200
    page = pulled.json()
    assert len(page['items']) == 2 and page['next_cursor'] == 2
    expected_cursor = 0
    applied = None
    for item in page['items']:
        opened = _crypto_bridge(tmp_path, {
            'action': 'open', 'canonical_user_id': canonical_user_id,
            'amk': amk, 'item': item,
        })
        applied = _native_bridge(tmp_path, {
            'action': 'receive_apply_prepare', 'database_path': str(database_path),
            'local_account_id': identity['local_account_id'], 'device_id': identity['device_id'],
            'canonical_user_id': canonical_user_id, 'item': item,
            'expected_cursor': expected_cursor, 'next_cursor': item['event']['server_sequence'],
            'opened': {key: opened[key] for key in ('crypto_version', 'aad_version', 'nonce', 'ciphertext', 'plaintext')},
        })
        assert applied['apply_result'] in ('applied', 'already_applied', 'self_echo_applied')
        expected_cursor = item['event']['server_sequence']
    assert applied is not None and applied['ack']['candidate_cursor'] == 2
    acknowledged = client.post('/api/v1/sync/ack', headers=_headers(token), json={
        'protocol_version': 1, 'device_id': identity['device_id'], 'cursor': 2,
    })
    assert acknowledged.status_code == 204
    committed = _native_bridge(tmp_path, {
        'action': 'commit_ack', 'database_path': str(database_path),
        'local_account_id': identity['local_account_id'], 'device_id': identity['device_id'],
        'canonical_user_id': canonical_user_id, 'expected_old_ack_cursor': 0,
        'acknowledged_cursor': 2, 'project_id': PROJECT_ID,
    })
    assert committed['ack_cursor'] == 2 and committed['note_count'] == 2


def test_c16_bootstrap_partial_restart_completion_and_second_device_import(cloud_client, tmp_path):
    client, engine = cloud_client
    canonical_user_id = str(create_user(engine))
    token = login(client).json()['access_token']
    notes = [_note('note-a', 'First'), _note('note-b', 'Second')]

    root_a = tmp_path / 'bootstrap-device-a'
    database_a = root_a / 'nfprogress.db'
    identity_a = _native_bridge(tmp_path, {
        'action': 'provision', 'data_root': str(root_a), 'database_path': str(database_a),
        'canonical_user_id': canonical_user_id, 'project_id': PROJECT_ID,
        'bind_project': False, 'notes': notes,
    })
    assert client.put(f"/api/v1/sync/devices/{identity_a['device_id']}", headers=_headers(token)).status_code == 200
    prepared = _native(tmp_path, database_a, identity_a, 'bootstrap_prepare')
    registered = client.post(
        f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap', headers=_headers(token),
        json={'bootstrap_id': prepared['bootstrap_id'], 'device_id': identity_a['device_id']},
    )
    assert registered.status_code == 200 and registered.json()['project']['state'] == 'initializing'
    captured = _native(
        tmp_path, database_a, identity_a, 'bootstrap_prepare_capture',
        bootstrap_id=prepared['bootstrap_id'], remote_high_water=0,
    )
    assert captured['record']['initial_event_count'] == 2

    sealed = []
    amk = None
    for event in captured['events']:
        note_for_wire = {key: value for key, value in event['note'].items() if key != 'revision'}
        result = _crypto_bridge(tmp_path, {
            'action': 'seal', 'canonical_user_id': canonical_user_id,
            'device_id': identity_a['device_id'], 'event': {
                key: event[key] for key in (
                    'event_id', 'project_id', 'entity_id', 'entity_type', 'operation',
                    'revision', 'updated_at', 'deleted_at',
                )
            },
            'note': note_for_wire, **({} if amk is None else {'amk': amk}),
        })
        amk = result['amk']
        sealed.append({
            'event_id': event['event_id'], 'mutation_generation': event['mutation_generation'],
            'push': result['push'], 'object': result['push']['items'][0]['object'],
        })

    first_push = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=sealed[0]['push'])
    assert first_push.status_code == 200
    first_receipt = first_push.json()['results'][0]
    partial = _native(
        tmp_path, database_a, identity_a, 'bootstrap_commit_upload',
        bootstrap_id=prepared['bootstrap_id'], accepted=[{
            **sealed[0], 'server_sequence': first_receipt['server_sequence'],
        }],
    )
    assert partial['cohort'] == {'event_count': 2, 'accepted_count': 1, 'max_server_sequence': 1, 'complete': False}

    resumed = _native(tmp_path, database_a, identity_a, 'bootstrap_prepare')
    assert resumed['bootstrap_id'] == prepared['bootstrap_id']
    replay_capture = _native(
        tmp_path, database_a, identity_a, 'bootstrap_prepare_capture',
        bootstrap_id=prepared['bootstrap_id'], remote_high_water=1,
    )
    assert replay_capture['event_ids'] == captured['event_ids']

    second_push = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=sealed[1]['push'])
    assert second_push.status_code == 200
    second_receipt = second_push.json()['results'][0]
    complete_local = _native(
        tmp_path, database_a, identity_a, 'bootstrap_commit_upload',
        bootstrap_id=prepared['bootstrap_id'], accepted=[{
            **sealed[1], 'server_sequence': second_receipt['server_sequence'],
        }],
    )
    assert complete_local['cohort']['complete'] is True
    completed = client.post(
        f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete', headers=_headers(token),
        json={
            'bootstrap_id': prepared['bootstrap_id'], 'device_id': identity_a['device_id'],
            'initial_event_count': 2, 'initial_max_server_sequence': 2,
        },
    )
    assert completed.status_code == 200 and completed.json()['project']['state'] == 'active'
    _native(
        tmp_path, database_a, identity_a, 'bootstrap_confirm_active',
        bootstrap_id=prepared['bootstrap_id'], remote_high_water=2,
    )
    _apply_page(client, tmp_path, token, database_a, identity_a, canonical_user_id, amk)
    ready_a = _native(
        tmp_path, database_a, identity_a, 'bootstrap_mark_ready', bootstrap_id=prepared['bootstrap_id'],
    )
    assert ready_a['phase'] == 'ready'

    root_b = tmp_path / 'bootstrap-device-b'
    database_b = root_b / 'nfprogress.db'
    identity_b = _native_bridge(tmp_path, {
        'action': 'provision', 'data_root': str(root_b), 'database_path': str(database_b),
        'canonical_user_id': canonical_user_id, 'project_id': PROJECT_ID,
        'create_project': False, 'bind_project': False,
    })
    assert client.put(f"/api/v1/sync/devices/{identity_b['device_id']}", headers=_headers(token)).status_code == 200
    imported = _native(
        tmp_path, database_b, identity_b, 'bootstrap_import',
        bootstrap_id=prepared['bootstrap_id'], remote_high_water=2, display_name='Imported project',
    )
    assert imported['mode'] == 'import_remote' and imported['phase'] == 'captured'
    _apply_page(client, tmp_path, token, database_b, identity_b, canonical_user_id, amk)
    ready_b = _native(
        tmp_path, database_b, identity_b, 'bootstrap_mark_ready', bootstrap_id=prepared['bootstrap_id'],
    )
    assert ready_b['phase'] == 'ready'
