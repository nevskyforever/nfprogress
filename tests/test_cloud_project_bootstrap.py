from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.cloud.models import CloudProject
from backend.app.cloud.services import CloudProjectBootstrapError, CloudProjectService
from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_encrypted_sync import _device, _encrypted_request, _event, _headers, _object


def _register(client, token: str, project_id: str, bootstrap_id: str, device_id: str):
    return client.post(
        f'/api/v1/cloud/projects/{project_id}/bootstrap', headers=_headers(token),
        json={'bootstrap_id': bootstrap_id, 'device_id': device_id},
    )


def _complete(client, token: str, project_id: str, bootstrap_id: str, device_id: str,
              count: int, sequence: int):
    return client.post(
        f'/api/v1/cloud/projects/{project_id}/bootstrap/complete', headers=_headers(token),
        json={
            'bootstrap_id': bootstrap_id, 'device_id': device_id,
            'initial_event_count': count, 'initial_max_server_sequence': sequence,
        },
    )


def test_bootstrap_auth_isolation_listing_and_strict_registration(cloud_client):
    client, engine = cloud_client
    create_user(engine, username='First', email='first-bootstrap@example.test')
    create_user(engine, username='Second', email='second-bootstrap@example.test')
    first = login(client, 'First').json()['access_token']
    second = login(client, 'Second').json()['access_token']
    device = _device(client, first)
    bootstrap = str(uuid4())

    assert client.get('/api/v1/cloud/projects/bootstrap').status_code == 401
    malformed = client.post('/api/v1/cloud/projects/p/bootstrap', headers=_headers(first), json={
        'bootstrap_id': bootstrap, 'device_id': device, 'unknown': 'secret',
    })
    assert malformed.status_code == 422
    registered = _register(client, first, 'p', bootstrap, device)
    assert registered.status_code == 200
    assert registered.json()['project'] == {
        'project_id': 'p', 'bootstrap_id': bootstrap, 'origin_device_id': device,
        'state': 'initializing', 'initial_event_count': None,
        'initial_max_server_sequence': None,
    }
    assert client.get('/api/v1/cloud/projects/bootstrap', headers=_headers(second)).json() == {
        'projects': [], 'current_cursor': 0,
    }
    assert client.get('/api/v1/cloud/projects/bootstrap', headers=_headers(first)).json()['projects'] == [
        registered.json()['project'],
    ]


def test_exact_registration_and_completion_replay_are_immutable(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    other_device = _device(client, token)
    bootstrap = str(uuid4())

    first = _register(client, token, 'p', bootstrap, device)
    assert first.status_code == 200
    assert _register(client, token, 'p', bootstrap, device).json() == first.json()
    conflict = _register(client, token, 'p', str(uuid4()), device)
    assert conflict.status_code == 409
    assert conflict.json()['detail']['code'] == 'cloud_project_bootstrap_conflict'
    wrong_device = _register(client, token, 'p', bootstrap, other_device)
    assert wrong_device.status_code == 409
    assert wrong_device.json()['detail']['code'] == 'cloud_project_bootstrap_conflict'

    completed = _complete(client, token, 'p', bootstrap, device, 0, 0)
    assert completed.status_code == 200 and completed.json()['project']['state'] == 'active'
    assert _complete(client, token, 'p', bootstrap, device, 0, 0).json() == completed.json()
    changed = _complete(client, token, 'p', bootstrap, device, 1, 1)
    assert changed.status_code == 409
    assert changed.json()['detail']['code'] == 'cloud_project_bootstrap_conflict'
    deletion = client.delete('/api/v1/cloud/projects/p', headers=_headers(token))
    assert deletion.status_code == 409
    assert deletion.json()['detail']['code'] == 'cloud_project_bootstrap_managed'


def test_initializing_project_restricts_new_events_but_preserves_exact_replay(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    token = login(client).json()['access_token']
    origin = _device(client, token)
    other = _device(client, token)
    bootstrap = str(uuid4())
    assert _register(client, token, 'p', bootstrap, origin).status_code == 200

    event = _event(project_id='p')
    envelope = _object()
    request = _encrypted_request(origin, (event, envelope))
    accepted = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=request)
    assert accepted.status_code == 200
    sequence = accepted.json()['results'][0]['server_sequence']
    replay = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=request)
    assert replay.status_code == 200 and replay.json()['results'][0]['duplicate'] is True

    foreign = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=
                          _encrypted_request(other, (_event(project_id='p'), _object(nonce=b'o' * 24))))
    assert foreign.status_code == 409
    assert foreign.json()['detail']['code'] == 'cloud_project_bootstrap_origin_required'

    incomplete = _complete(client, token, 'p', bootstrap, origin, 2, sequence + 1)
    assert incomplete.status_code == 409
    assert incomplete.json()['detail']['code'] == 'cloud_project_initial_upload_incomplete'
    completed = _complete(client, token, 'p', bootstrap, origin, 1, sequence)
    assert completed.status_code == 200 and completed.json()['project']['state'] == 'active'
    after = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=
                        _encrypted_request(other, (_event(project_id='p'), _object(nonce=b'z' * 24))))
    assert after.status_code == 200


def test_legacy_reservation_and_orphaned_history_fail_closed(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    token = login(client).json()['access_token']
    device = _device(client, token)
    assert client.post('/api/v1/cloud/projects/legacy', headers=_headers(token)).status_code == 200
    legacy = _register(client, token, 'legacy', str(uuid4()), device)
    assert legacy.status_code == 409
    assert legacy.json()['detail']['code'] == 'cloud_project_legacy_reservation'

    assert client.post('/api/v1/cloud/projects/orphan', headers=_headers(token)).status_code == 200
    pushed = client.post('/api/v1/sync/encrypted/push', headers=_headers(token), json=
                         _encrypted_request(device, (_event(project_id='orphan'), _object())))
    assert pushed.status_code == 200
    assert client.delete('/api/v1/cloud/projects/orphan', headers=_headers(token)).status_code == 204
    orphan = _register(client, token, 'orphan', str(uuid4()), device)
    assert orphan.status_code == 409
    assert orphan.json()['detail']['code'] == 'cloud_project_orphaned_remote_history'


def test_concurrent_bootstrap_registration_serializes_lineage(migrated_database):
    user_id = create_user(migrated_database)
    device_id = uuid4()
    bootstrap = uuid4()
    with Session(migrated_database) as session:
        from backend.app.cloud.services import SyncService
        SyncService().register_device(session, user_id, device_id)

    def register(candidate):
        with Session(migrated_database) as session:
            try:
                state = CloudProjectService().register_bootstrap(
                    session, user_id, 'p', candidate, device_id,
                )
                return ('ok', state.projects[0].bootstrap_id)
            except CloudProjectBootstrapError as error:
                return (error.code, None)

    with ThreadPoolExecutor(max_workers=2) as executor:
        same = list(executor.map(register, (bootstrap, bootstrap)))
    assert same == [('ok', bootstrap), ('ok', bootstrap)]

    with ThreadPoolExecutor(max_workers=2) as executor:
        different = list(executor.map(register, (bootstrap, uuid4())))
    assert sorted(code for code, _ in different) == ['cloud_project_bootstrap_conflict', 'ok']
    with Session(migrated_database) as session:
        row = session.get(CloudProject, (user_id, 'p'))
        assert row is not None and row.bootstrap_id == bootstrap and row.bootstrap_state == 'initializing'
