"""One real protected-reader dependency-order reproduction, without capability writes."""
import json
import socket
import subprocess
import threading
import time
import urllib.request

import uvicorn
from sqlalchemy import text

from test_cloud_auth import ROOT, cloud_client, create_user, migrated_database


def test_stage_waiting_for_later_metadata_preserves_ciphertext_on_restart(cloud_client, tmp_path):
    client, engine = cloud_client
    create_user(engine, username='LateDependency', email='late@example.test')
    api_socket = socket.socket()
    api_socket.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(client.app, lifespan='off', access_log=False, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [api_socket]}, daemon=True)
    thread.start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with (tmp_path / 'vite.log').open('w+') as log:
        vite = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
                                 '--port', str(port), '--strictPort'], cwd=ROOT / 'frontend', stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{port}/scripts/browser-cloud-account-harness.html', timeout=1).close()
                    if server.started:
                        break
                except OSError:
                    time.sleep(.1)
                    continue
                time.sleep(.1)
            else:
                raise AssertionError('isolated server/Vite did not start')
            result = subprocess.run(['node', 'scripts/browser-replay-late-dependency-acceptance.mjs',
                                     f'http://127.0.0.1:{port}', f'http://127.0.0.1:{api_socket.getsockname()[1]}'],
                                    cwd=ROOT / 'frontend', capture_output=True, text=True, timeout=120)
            assert result.returncode == 0, result.stdout + result.stderr
            evidence = json.loads(result.stdout.strip().splitlines()[-1])
            assert evidence['pass'] and evidence['events'] == 3 and evidence['ownerProofs'] == 1
            assert evidence['readerWrites'] == 0 and evidence['projectResultReturned'] is False
            with engine.connect() as connection:
                assert connection.scalar(text('SELECT count(*) FROM sync_events')) == 3
                assert connection.scalar(text('SELECT count(*) FROM encrypted_objects')) == 3
                assert connection.scalar(text('SELECT max(last_ack_sequence) FROM sync_devices')) == 0
                assert connection.scalar(text('SELECT max(note_ordinary_reader_version) FROM sync_devices')) == 0
            print('Late Metadata dependency:', evidence)
        finally:
            vite.terminate()
            vite.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=15)
            api_socket.close()
