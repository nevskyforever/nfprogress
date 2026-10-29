"""Private encrypted Note source seed against disposable PostgreSQL16 and real Chromium."""
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


def test_browser_replay_source_seed_real_api_postgresql(cloud_client, tmp_path):
    client, engine = cloud_client
    create_user(engine, username='SourceSeed', email='sourceseed@example.test')
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
            result = subprocess.run(['node', 'scripts/browser-replay-source-seed-acceptance.mjs',
                f'http://127.0.0.1:{vite_port}', f'http://127.0.0.1:{api_port}'],
                cwd=ROOT / 'frontend', capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, result.stdout + result.stderr
            evidence = json.loads(result.stdout.strip().splitlines()[-1])
            assert evidence['pass'] and evidence['sourceRows'] == 2 and evidence['events'] == 104
            assert evidence['readerWrites'] == 0
            print(f"Encrypted source seed: {evidence['scenarios']} Chromium scenarios; two real sources; zero reader writes")
            with Session(engine) as session:
                for device in session.query(SyncDevice):
                    assert device.last_ack_sequence == 0
                    assert device.note_ordinary_reader_version == 0
                for row in session.query(EncryptedObject):
                    assert b'PRIVATE_SEED_CONTENT_' not in row.ciphertext
        finally:
            vite.terminate()
            vite.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=15)
            api_socket.close()


def test_browser_replay_initial_notes_real_api_postgresql(cloud_client, tmp_path):
    client, engine = cloud_client
    create_user(engine, username='InitialNotes', email='initialnotes@example.test')
    api_socket = socket.socket()
    api_socket.bind(('127.0.0.1', 0))
    api_port = api_socket.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(client.app, lifespan='off', access_log=False, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [api_socket]}, daemon=True)
    thread.start()
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        vite_port = port_socket.getsockname()[1]
    with (tmp_path / 'vite-notes.log').open('w+') as log:
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
            result = subprocess.run(['node', 'scripts/browser-replay-initial-notes-acceptance.mjs',
                f'http://127.0.0.1:{vite_port}', f'http://127.0.0.1:{api_port}'],
                cwd=ROOT / 'frontend', capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, result.stdout + result.stderr
            evidence = json.loads(result.stdout.strip().splitlines()[-1])
            assert evidence['pass'] and evidence['noteProofs'] == 3 and evidence['structuralProofs'] == 4
            assert evidence['readerWrites'] == 0
            print(f"Initial Legacy Note replay: {evidence['scenarios']} Chromium scenarios; zero reader writes")
            with Session(engine) as session:
                for device in session.query(SyncDevice):
                    assert device.last_ack_sequence == 0
                    assert device.note_ordinary_reader_version == 0
                for row in session.query(EncryptedObject):
                    assert b'PRIVATE_SEED_CONTENT_' not in row.ciphertext
        finally:
            vite.terminate()
            vite.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=15)
            api_socket.close()


def test_browser_replay_note_updates_real_api_postgresql(cloud_client, tmp_path):
    client, engine = cloud_client
    create_user(engine, username='NoteUpdates', email='noteupdates@example.test')
    for suffix in ('WrongParent', 'RevisionGap', 'Fork'):
        create_user(engine, username=f'NoteUpdates{suffix}', email=f'noteupdates{suffix.lower()}@example.test')
    api_socket = socket.socket()
    api_socket.bind(('127.0.0.1', 0))
    api_port = api_socket.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(client.app, lifespan='off', access_log=False, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [api_socket]}, daemon=True)
    thread.start()
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        vite_port = port_socket.getsockname()[1]
    with (tmp_path / 'vite-updates.log').open('w+') as log:
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
            result = subprocess.run(['node', 'scripts/browser-replay-note-updates-acceptance.mjs',
                f'http://127.0.0.1:{vite_port}', f'http://127.0.0.1:{api_port}'],
                cwd=ROOT / 'frontend', capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, result.stdout + result.stderr
            evidence = json.loads(result.stdout.strip().splitlines()[-1])
            assert evidence['pass'] and evidence['noteProofs'] == 7 and evidence['readerWrites'] == 0
            print(f"Post-initial Legacy Note replay: {evidence['scenarios']} Chromium scenarios; zero reader writes")
            with Session(engine) as session:
                for device in session.query(SyncDevice):
                    assert device.last_ack_sequence == 0
                    assert device.note_ordinary_reader_version == 0
                for row in session.query(EncryptedObject):
                    assert b'PRIVATE_SEED_UPDATED_CONTENT_' not in row.ciphertext
        finally:
            vite.terminate()
            vite.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=15)
            api_socket.close()


def test_browser_replay_note_deletion_real_api_postgresql(cloud_client, tmp_path):
    client, engine = cloud_client
    create_user(engine, username='NoteDeletion', email='notedeletion@example.test')
    for kind in ('wrong_parent', 'revision_gap', 'unknown_note', 'repeat'):
        suffix = kind.replace('_', '')
        create_user(engine, username=f'NoteDelete{suffix}', email=f'notedelete{suffix}@example.test')
    for suffix in ('WrongParent', 'RevisionGap', 'Fork'):
        create_user(engine, username=f'NoteUpdates{suffix}', email=f'notedeletion{suffix.lower()}@example.test')
    api_socket = socket.socket()
    api_socket.bind(('127.0.0.1', 0))
    api_port = api_socket.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(client.app, lifespan='off', access_log=False, log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [api_socket]}, daemon=True)
    thread.start()
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        vite_port = port_socket.getsockname()[1]
    with (tmp_path / 'vite-deletion.log').open('w+') as log:
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
            result = subprocess.run(['node', 'scripts/browser-replay-note-deletion-acceptance.mjs',
                f'http://127.0.0.1:{vite_port}', f'http://127.0.0.1:{api_port}'],
                cwd=ROOT / 'frontend', capture_output=True, text=True, timeout=300)
            assert result.returncode == 0, result.stdout + result.stderr
            evidence = json.loads(result.stdout.strip().splitlines()[-1])
            assert evidence['pass'] and evidence['noteProofs'] == 9 and evidence['tombstones'] == 2
            assert evidence['readerWrites'] == 0
            print(f"Legacy Note deletion replay: {evidence['scenarios']} Chromium scenarios; two tombstones; zero reader writes")
            with Session(engine) as session:
                for device in session.query(SyncDevice):
                    assert device.last_ack_sequence == 0
                    assert device.note_ordinary_reader_version == 0
                for row in session.query(EncryptedObject):
                    assert b'PRIVATE_SEED_BAD_CONTENT_' not in row.ciphertext
        finally:
            vite.terminate()
            vite.wait(timeout=15)
            server.should_exit = True
            thread.join(timeout=15)
            api_socket.close()
