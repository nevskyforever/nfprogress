from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.cloud.models import SyncDevice
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_encrypted_sync import _headers


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'
CARGO_MANIFEST = FRONTEND / 'src-tauri' / 'Cargo.toml'
PROJECT_ID = 'project-1'
NOTE_ID = 'note-1'
TIMESTAMP = '2026-09-23T00:00:00.000000Z'


def _exchange_path(tmp_path: Path, label: str) -> tuple[Path, Path]:
    token = uuid4().hex
    return tmp_path / f'{label}-{token}-request.json', tmp_path / f'{label}-{token}-response.json'


def _native_bridge(tmp_path: Path, request: dict[str, object]) -> dict[str, object]:
    request_path, response_path = _exchange_path(tmp_path, 'native')
    request_path.write_text(json.dumps(request), encoding='utf-8')
    request_path.chmod(0o600)
    environment = os.environ.copy()
    environment.update({
        'NFPROGRESS_C15_NATIVE_BRIDGE_REQUEST': str(request_path),
        'NFPROGRESS_C15_NATIVE_BRIDGE_RESPONSE': str(response_path),
    })
    completed = subprocess.run([
        'cargo', 'test', '--manifest-path', str(CARGO_MANIFEST),
        'c15_headless_native_bridge', '--', '--ignored', '--nocapture', '--test-threads=1',
    ], cwd=ROOT, env=environment, text=True, capture_output=True, timeout=180, check=False)
    if completed.returncode != 0:
        raise AssertionError(f'native bridge failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}')
    assert response_path.is_file(), 'native bridge did not produce a response'
    response = json.loads(response_path.read_text(encoding='utf-8'))
    request_path.unlink()
    response_path.unlink()
    return response


def _crypto_bridge(tmp_path: Path, request: dict[str, object]) -> dict[str, object]:
    request_path, response_path = _exchange_path(tmp_path, 'crypto')
    request_path.write_text(json.dumps(request), encoding='utf-8')
    request_path.chmod(0o600)
    environment = os.environ.copy()
    environment.update({
        'NFPROGRESS_C15_CRYPTO_BRIDGE_REQUEST': str(request_path),
        'NFPROGRESS_C15_CRYPTO_BRIDGE_RESPONSE': str(response_path),
    })
    completed = subprocess.run([
        'npm', 'test', '--', '--run', 'src/cloud/noteSyncHeadlessCryptoBridge.spec.ts',
    ], cwd=FRONTEND, env=environment, text=True, capture_output=True, timeout=120, check=False)
    if completed.returncode != 0:
        raise AssertionError(f'crypto bridge failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}')
    assert response_path.is_file(), 'crypto bridge did not produce a response'
    response = json.loads(response_path.read_text(encoding='utf-8'))
    request_path.unlink()
    response_path.unlink()
    return response


def _provision_device(tmp_path: Path, name: str, canonical_user_id: str) -> tuple[Path, dict[str, object]]:
    data_root = tmp_path / name
    database_path = data_root / 'nfprogress.db'
    identity = _native_bridge(tmp_path, {
        'action': 'provision',
        'data_root': str(data_root),
        'database_path': str(database_path),
        'canonical_user_id': canonical_user_id,
        'project_id': PROJECT_ID,
    })
    return database_path, identity


def test_c15_headless_cross_runtime_encrypted_apply_and_ack(cloud_client, tmp_path):
    client, engine = cloud_client
    canonical_user_id = str(create_user(engine))
    token = login(client).json()['access_token']
    database_a, identity_a = _provision_device(tmp_path, 'device-a', canonical_user_id)
    database_b, identity_b = _provision_device(tmp_path, 'device-b', canonical_user_id)
    assert database_a != database_b
    assert identity_a['local_account_id'] != identity_b['local_account_id']
    assert identity_a['device_id'] != identity_b['device_id']

    for identity in (identity_a, identity_b):
        response = client.put(
            f"/api/v1/sync/devices/{identity['device_id']}",
            headers=_headers(token),
        )
        assert response.status_code == 200
        assert response.json()['device_id'] == identity['device_id']
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}', headers=_headers(token)).status_code == 200

    event_id = str(uuid4())
    title = 'Cross-runtime private title'
    content = '<p>Cross-runtime private body</p>'
    sealed = _crypto_bridge(tmp_path, {
        'action': 'seal',
        'canonical_user_id': canonical_user_id,
        'device_id': identity_a['device_id'],
        'event': {
            'event_id': event_id,
            'project_id': PROJECT_ID,
            'entity_id': NOTE_ID,
            'entity_type': 'note',
            'operation': 'upsert',
            'revision': 1,
            'updated_at': TIMESTAMP,
            'deleted_at': None,
        },
        'note': {
            'id': NOTE_ID,
            'project_id': PROJECT_ID,
            'stage_id': None,
            'source_type': 'project',
            'source_map_id': None,
            'source_node_id': None,
            'content_format': 'html',
            'title': title,
            'content': content,
            'checklist': [],
            'color': 'default',
            'pinned': False,
            'archived': False,
            'sort_order': 0,
            'tags': [],
            'created_at': TIMESTAMP,
            'updated_at': TIMESTAMP,
            'metadata': {},
        },
    })
    push = sealed['push']
    serialized_push = json.dumps(push)
    assert title not in serialized_push and content not in serialized_push
    assert 'amk' not in push
    pushed = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=push)
    assert pushed.status_code == 200
    assert pushed.json()['results'] == [{
        'event_id': event_id,
        'server_sequence': 1,
        'duplicate': False,
    }]

    pulled = client.get('/api/v1/sync/encrypted/pull', headers=_headers(token), params={
        'device_id': identity_b['device_id'],
        'since': 0,
        'limit': 100,
        'protocol_version': 1,
        'encrypted_sync_version': 1,
    })
    assert pulled.status_code == 200
    page = pulled.json()
    assert page['next_cursor'] == 1 and len(page['items']) == 1
    assert page['items'][0]['event']['event_id'] == event_id
    assert page['items'][0]['object'] == push['items'][0]['object']

    opened = _crypto_bridge(tmp_path, {
        'action': 'open',
        'canonical_user_id': canonical_user_id,
        'amk': sealed['amk'],
        'item': page['items'][0],
    })
    assert opened['decoded']['mutation'] == 'create'
    assert opened['decoded']['note']['title'] == title
    assert opened['decoded']['note']['content'] == content

    applied = _native_bridge(tmp_path, {
        'action': 'receive_apply_prepare',
        'database_path': str(database_b),
        'local_account_id': identity_b['local_account_id'],
        'device_id': identity_b['device_id'],
        'canonical_user_id': canonical_user_id,
        'item': page['items'][0],
        'next_cursor': page['next_cursor'],
        'opened': {
            key: opened[key]
            for key in ('crypto_version', 'aad_version', 'nonce', 'ciphertext', 'plaintext')
        },
    })
    assert applied['apply_result'] == 'applied'
    assert applied['inbox_state'] == 'applied'
    assert applied['note']['title'] == title and applied['note']['content'] == content
    assert applied['head_event_id'] == event_id and applied['head_revision'] == 1
    assert applied['ack'] == {'current_ack_cursor': 0, 'candidate_cursor': 1}

    acknowledged = client.post('/api/v1/sync/ack', headers=_headers(token), json={
        'protocol_version': 1,
        'device_id': identity_b['device_id'],
        'cursor': applied['ack']['candidate_cursor'],
    })
    assert acknowledged.status_code == 204
    committed = _native_bridge(tmp_path, {
        'action': 'commit_ack',
        'database_path': str(database_b),
        'local_account_id': identity_b['local_account_id'],
        'device_id': identity_b['device_id'],
        'canonical_user_id': canonical_user_id,
        'expected_old_ack_cursor': applied['ack']['current_ack_cursor'],
        'acknowledged_cursor': applied['ack']['candidate_cursor'],
        'project_id': PROJECT_ID,
    })
    assert committed == {'result': 'advanced', 'pull_cursor': 1, 'ack_cursor': 1, 'note_count': 1}

    with Session(engine) as session:
        server_device = session.query(SyncDevice).filter_by(
            user_id=canonical_user_id,
            device_id=identity_b['device_id'],
        ).one()
        assert server_device.last_ack_sequence == 1
    with sqlite3.connect(database_b) as connection:
        payload = json.loads(connection.execute(
            'SELECT payload_json FROM notes WHERE id=?', (NOTE_ID,),
        ).fetchone()[0])
        local_cursors = connection.execute(
            'SELECT pull_cursor,ack_cursor FROM cloud_sync_state WHERE account_id=?',
            (identity_b['local_account_id'],),
        ).fetchone()
    assert payload['title'] == title and payload['content'] == content
    assert local_cursors == (1, 1)
