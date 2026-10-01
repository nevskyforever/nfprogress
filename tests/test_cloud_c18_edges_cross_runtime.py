"""C18.3.03 paginated import and stale resolution: real opaque PostgreSQL + SQLite."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3

from test_cloud_auth import cloud_client, create_user, login, migrated_database
from test_cloud_c18_authority_cross_runtime import bootstrap, native, provision, publish, sync
from test_cloud_c15_headless_cross_runtime import PROJECT_ID, _crypto_bridge, _headers


def test_metadata_large_import_and_additional_tip_resolution(cloud_client, tmp_path):
    client, engine = cloud_client
    user = str(create_user(engine)); token = login(client).json()['access_token']; headers = _headers(token)
    devices = [provision(tmp_path, label, user, label == 'A') for label in ('A', 'B', 'C', 'D-import')]
    (a, ia), (b, ib), (c, ic), (d, idd) = devices
    for _, identity in devices:
        assert client.put(f"/api/v1/sync/devices/{identity['device_id']}", headers=headers).status_code == 200
    boot = bootstrap(tmp_path, a, ia, 'bootstrap_prepare')['bootstrap_id']
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap', headers=headers,
        json=dict(bootstrap_id=boot, device_id=ia['device_id'])).status_code == 200
    bootstrap(tmp_path, a, ia, 'bootstrap_prepare_capture', bootstrap_id=boot, remote_high_water=0)
    assert client.post(f'/api/v1/cloud/projects/{PROJECT_ID}/bootstrap/complete', headers=headers,
        json=dict(bootstrap_id=boot, device_id=ia['device_id'], initial_event_count=0, initial_max_server_sequence=0)).status_code == 200
    bootstrap(tmp_path, a, ia, 'bootstrap_confirm_active', bootstrap_id=boot, remote_high_water=0)
    assert client.post('/api/v2/sync/encrypted/cutover', headers=headers, json=dict(expected_cutover_epoch=0)).status_code == 200
    for _, identity in devices:
        assert client.post('/api/v3/sync/encrypted/reader-ready', headers=headers,
            json=dict(device_id=identity['device_id'], reader_transport_version=3)).status_code == 204
    assert client.post('/api/v3/sync/encrypted/cutover', headers=headers, json=dict(expected_cutover_epoch=1)).status_code == 200
    amk = list(os.urandom(32)); native(tmp_path, a, ia, user, 'begin')
    genesis, _ = publish(client, tmp_path, token, a, ia, user, amk)
    sync(client, tmp_path, token, a, ia, user, amk)
    last = genesis
    # Deliberately one event/page below: 17 ordinary events cross the old page cap.
    for index in range(17):
        proposed = native(tmp_path, a, ia, user, 'read')['view']['local']
        proposed['name'] = f'History {index}'
        native(tmp_path, a, ia, user, 'normal_edit', proposed=proposed)
        last, _ = publish(client, tmp_path, token, a, ia, user, amk)
        assert sync(client, tmp_path, token, a, ia, user, amk)['view']['state'] == 'active'
    for path, identity in ((b, ib), (c, ic)):
        bootstrap(tmp_path, path, identity, 'bootstrap_import', bootstrap_id=boot,
            remote_high_water=18, display_name=last['metadata']['name'], authenticated_metadata=last['metadata'])
        assert sync(client, tmp_path, token, path, identity, user, amk)['view']['state'] == 'active'
    # Prepare all three siblings against exactly the same head, before any peer arrival.
    for path, identity, name in ((a, ia, 'A'), (b, ib, 'B'), (c, ic, 'C')):
        proposed = native(tmp_path, path, identity, user, 'read')['view']['local']; proposed['name'] = name
        native(tmp_path, path, identity, user, 'normal_edit', proposed=proposed)
    ea, _ = publish(client, tmp_path, token, a, ia, user, amk)
    eb, _ = publish(client, tmp_path, token, b, ib, user, amk)
    for path, identity in ((a, ia), (b, ib)):
        assert sync(client, tmp_path, token, path, identity, user, amk)['view']['state'] == 'metadata_conflict'
    r = native(tmp_path, a, ia, user, 'change', kind='choose_branch', selected=eb['header']['event_id'])['result']
    ec, _ = publish(client, tmp_path, token, c, ic, user, amk)
    # A has not observed C: server accepts the opaque R(A,B), with no semantic winner.
    stale, stale_request = publish(client, tmp_path, token, a, ia, user, amk)
    assert stale['header']['event_id'] == r
    assert stale['header']['parent_event_ids'] == sorted([ea['header']['event_id'], eb['header']['event_id']])
    for path, identity in ((a, ia), (b, ib), (c, ic)):
        view = sync(client, tmp_path, token, path, identity, user, amk)['view']
        assert view['state'] == 'metadata_conflict'
        assert {branch['event_id'] for branch in view['branches']} == {r, ec['header']['event_id']}
        assert native(tmp_path, path, identity, user, 'read')['view'] == view  # reopen after every bridge call
    with sqlite3.connect(a) as db:
        assert db.execute('SELECT state FROM cloud_sync_metadata_decisions WHERE event_id=?', (r,)).fetchone()[0] == 'conflict'
        assert db.execute('SELECT COUNT(*) FROM cloud_sync_metadata_invalidated_decisions').fetchone()[0] == 1
    # Retry is an exact immutable server replay, never a different resolution identity.
    replay = client.post('/api/v3/sync/encrypted/push', headers=headers, json=stale_request)
    assert replay.status_code == 200 and replay.json()['results'][0]['duplicate']
    r2 = native(tmp_path, a, ia, user, 'change', kind='choose_branch', selected=ec['header']['event_id'])['result']
    resolved, _ = publish(client, tmp_path, token, a, ia, user, amk)
    assert r2 != r and resolved['header']['parent_event_ids'] == sorted([r, ec['header']['event_id']])
    for path, identity in ((a, ia), (b, ib), (c, ic)):
        view = sync(client, tmp_path, token, path, identity, user, amk)['view']
        assert view['state'] == 'active' and view['local']['name'] == 'C'
    progress = native(tmp_path, d, idd, user, 'import_read', bootstrap_id=boot)
    pages = 0
    while True:
        since = progress['cursor']
        response = client.get('/api/v3/sync/encrypted/pull', headers=headers, params=dict(
            device_id=idd['device_id'], since=since, limit=1, protocol_version=3, encrypted_sync_version=3))
        assert response.status_code == 200, response.text
        wire = response.json(); events = []
        for item in wire['items']:
            opened = _crypto_bridge(tmp_path, dict(action='metadata_open', canonical_user_id=user, amk=amk, item=item))
            events.append(dict(server_sequence=item['event']['server_sequence'], plaintext=opened['plaintext']))
        page = dict(expected_cursor=since, next_cursor=wire['next_cursor'], has_more=wire['has_more'],
            page_events=len(wire['items']), page_identity=hashlib.sha256(json.dumps(wire, sort_keys=True).encode()).hexdigest(), events=events)
        progress = native(tmp_path, d, idd, user, 'import_page', bootstrap_id=boot, page=page)
        repeated = native(tmp_path, d, idd, user, 'import_page', bootstrap_id=boot, page=page)
        assert repeated == progress
        resumed = native(tmp_path, d, idd, user, 'import_read', bootstrap_id=boot)
        assert resumed == progress
        pages += 1
        with sqlite3.connect(d) as db:
            assert db.execute('SELECT pull_cursor,ack_cursor FROM cloud_sync_state').fetchone() == (0, 0)
            assert db.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 0
        if pages == 16:
            assert progress['state'] == 'running' and progress['head'] is None and progress['metadata'] is None
        if progress['state'] == 'complete': break
    assert pages == 23 and progress['event_count'] == 23 and progress['head'] == r2
    bootstrap(tmp_path, d, idd, 'bootstrap_import', bootstrap_id=boot, remote_high_water=23,
        display_name=progress['metadata']['name'], authenticated_metadata=progress['metadata'])
    view = sync(client, tmp_path, token, d, idd, user, amk)['view']
    assert view['state'] == 'active' and view['local']['name'] == 'C'
    for path, _ in devices:
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT COUNT(*) FROM cloud_sync_metadata_events').fetchone()[0] == 23
            assert db.execute('SELECT COUNT(*) FROM cloud_sync_metadata_tips').fetchone()[0] == 1
            assert db.execute('SELECT head_event_id FROM cloud_sync_metadata_reconciliation').fetchone()[0] == r2
