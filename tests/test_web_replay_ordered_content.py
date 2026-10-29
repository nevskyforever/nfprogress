"""Bounded ordered Content replay through real FastAPI, PostgreSQL 16 and Chromium."""
from __future__ import annotations

import json
import socket
import subprocess
import threading
import time
import urllib.request

import uvicorn
from sqlalchemy.orm import Session

from backend.app.cloud.models import EncryptedObject, SyncDevice
from test_cloud_auth import ROOT, cloud_client, create_user, migrated_database


def test_bounded_ordered_content_real_server(cloud_client, tmp_path):
    client, engine = cloud_client
    create_user(engine, username='OrderedContentServer', email='orderedcontent@example.test')
    api_socket = socket.socket()
    api_socket.bind(('127.0.0.1', 0))
    api_port = api_socket.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(client.app, lifespan='off', access_log=False, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [api_socket]}, daemon=True)
    thread.start()
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        vite_port = port_socket.getsockname()[1]
    with (tmp_path / 'vite-ordered-content.log').open('w+') as log:
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
            result = subprocess.run(['node', 'scripts/browser-replay-ordered-content-server-acceptance.mjs',
                f'http://127.0.0.1:{vite_port}', f'http://127.0.0.1:{api_port}'],
                cwd=ROOT / 'frontend', capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, result.stdout + result.stderr
            evidence = json.loads(result.stdout.strip().splitlines()[-1])
            assert evidence['pass'] and evidence['events'] == 7 and evidence['readerWrites'] == 0
            with Session(engine) as session:
                devices = list(session.query(SyncDevice))
                assert len(devices) == 2
                assert all(device.last_ack_sequence == 0 for device in devices)
                assert any(device.note_ordinary_reader_version == 0 for device in devices) is False
                assert len(list(session.query(EncryptedObject))) == evidence['events'] + 1
                assert all(b'PRIVATE_CONTENT_UPDATE_BODY' not in row.ciphertext for row in session.query(EncryptedObject))
        finally:
            vite.terminate()
            vite.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=15)
            api_socket.close()
