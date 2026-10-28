"""Real Imported Metadata owner, replay migration and Chromium restart against disposable PostgreSQL16."""
from __future__ import annotations

import json
import socket
import subprocess
import threading
import time
import urllib.request

import uvicorn
from sqlalchemy.orm import Session

from backend.app.cloud.models import EncryptedObject, SyncDevice, SyncEvent
from test_cloud_auth import ROOT, cloud_client, create_user, migrated_database


def test_browser_replay_metadata_owner_real_api_postgresql(cloud_client, tmp_path):
    client, engine = cloud_client
    for username in ['Metadata', 'MetadataOther', 'MetaSelf', *('Meta' + kind for kind in ('corrupt', 'descriptor', 'bootstrap', 'account', 'device', 'missing', 'conflict', 'delete', 'cover', 'generation', 'mixed'))]:
        create_user(engine, username=username, email=f'{username.lower()}@example.test')
    api_socket = socket.socket()
    api_socket.bind(('127.0.0.1', 0))
    api_port = api_socket.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(client.app, lifespan='off', access_log=False, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [api_socket]}, daemon=True)
    thread.start()
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        vite_port = port_socket.getsockname()[1]
    with (tmp_path / 'vite.log').open('w+') as log:
        vite = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(vite_port), '--strictPort'], cwd=ROOT / 'frontend', stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{vite_port}/scripts/browser-cloud-account-harness.html', timeout=1).close()
                    if server.started:
                        break
                except OSError:
                    pass
                time.sleep(.1)
            else:
                raise AssertionError('isolated backend/Vite did not start')
            result = subprocess.run(['node', 'scripts/browser-replay-metadata-acceptance.mjs', f'http://127.0.0.1:{vite_port}', f'http://127.0.0.1:{api_port}'], cwd=ROOT / 'frontend', capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, result.stdout + result.stderr
            evidence = json.loads(result.stdout.strip().splitlines()[-1])
            assert evidence['pass'] and evidence['scenarios'] == 47 and evidence['ownerProofs'] == 102 and evidence['readerWrites'] == 0
            print(f"Metadata replay: {evidence['scenarios']} Chromium scenarios; {evidence['ownerProofs']} real owner proofs; zero reader writes")
            with Session(engine) as session:
                devices = session.query(SyncDevice).filter(SyncDevice.device_id.in_(evidence['identities'])).all()
                assert len(devices) == len(evidence['identities'])
                for device in devices:
                    assert device.last_ack_sequence == 0
                    assert device.reader_transport_version == (3 if str(device.device_id) == evidence['selfEchoDevice'] else 2)
                    assert not device.compression_id1
                    assert device.note_ordinary_reader_version == 0
                    assert device.note_resolution_reader_version == 0
                assert session.query(SyncEvent).count() == 123
                assert session.query(EncryptedObject).count() == 123
                for row in session.query(EncryptedObject):
                    assert b'PRIVATE_METADATA_' not in row.ciphertext
        finally:
            vite.terminate()
            vite.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=15)
            api_socket.close()
