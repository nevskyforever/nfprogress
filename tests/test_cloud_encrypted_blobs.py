from __future__ import annotations

import hashlib
import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.app.cloud.blob_store import BlobAlreadyExists, FileSystemBlobStore
from backend.app.cloud.encrypted_blobs_service import BlobMetadata, EncryptedBlobService, MAX_COVER_CIPHERTEXT_BYTES
from test_cloud_encrypted_schema import ROOT, USER_ONE, _drop_all, _insert_event, _insert_user, _insert_user_crypto
from test_cloud_auth import AUTH_SECRET, _database_url, create_user, login, migrated_database
from backend.app.config import RuntimeConfig
from backend.app.main import create_app


BLOB = UUID('00000000-0000-0000-0000-000000000201')


def _headers(token: str, nonce: str = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/octet-stream',
            'X-WORTA-Crypto-Version': '1', 'X-WORTA-AAD-Version': '1', 'X-WORTA-Nonce': nonce}


def test_c14_http_transport_security_and_cors(migrated_database, tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='test', database_url=_database_url(), auth_secret=AUTH_SECRET, cloud_blob_dir=tmp_path / 'blobs'))
    blob = UUID('00000000-0000-0000-0000-000000000299'); data = b'x' * 16
    with TestClient(app) as client:
        assert client.put(f'/api/v1/cloud/projects/p/covers/{blob}', content=data).status_code == 401
        user = create_user(migrated_database); token = login(client).json()['access_token']
        assert client.post('/api/v1/cloud/projects/p', headers={'Authorization': f'Bearer {token}'}).status_code == 200
        put = client.put(f'/api/v1/cloud/projects/p/covers/{blob}', content=data, headers=_headers(token)); assert put.status_code == 200 and not put.json()['duplicate']
        retry = client.put(f'/api/v1/cloud/projects/p/covers/{blob}', content=data, headers=_headers(token)); assert retry.json()['duplicate']
        get = client.get(f'/api/v1/cloud/projects/p/covers/{blob}', headers={'Authorization': f'Bearer {token}', 'Origin': 'http://localhost:5173'})
        assert get.content == data and get.headers['access-control-expose-headers'].lower().find('x-worta-nonce') >= 0
        assert get.headers['cache-control'] == 'private, no-store' and get.headers['x-content-type-options'] == 'nosniff'
        assert client.delete('/api/v1/cloud/projects/p', headers={'Authorization': f'Bearer {token}'}).status_code == 204
        assert client.put(f'/api/v1/cloud/projects/p/covers/{blob}', content=data, headers=_headers(token)).json()['duplicate']
        assert client.put(f'/api/v1/cloud/projects/p/covers/{UUID(int=blob.int+1)}', content=data, headers=_headers(token)).json()['detail']['code'] == 'cloud_project_not_enabled'
        assert client.put(f'/api/v1/cloud/projects/p/covers/{UUID(int=blob.int+2)}', content=b'x'*15, headers=_headers(token)).json()['detail']['code'] == 'invalid_encrypted_blob'


def test_c14_ownership_and_immutable_conflicts(migrated_database, tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='test', database_url=_database_url(), auth_secret=AUTH_SECRET, cloud_blob_dir=tmp_path / 'blobs'))
    blob = UUID('00000000-0000-0000-0000-000000000298'); first = b'a' * 16; second = b'b' * 16
    with TestClient(app) as client:
        first_user = create_user(migrated_database, username='Alice', email='alice@example.test'); a = login(client, 'Alice').json()['access_token']
        second_user = create_user(migrated_database, username='Bob', email='bob@example.test'); b = login(client, 'Bob').json()['access_token']
        for token, project in ((a, 'one'), (a, 'two'), (b, 'one')):
            assert client.post(f'/api/v1/cloud/projects/{project}', headers={'Authorization': f'Bearer {token}'}).status_code == 200
        assert client.put(f'/api/v1/cloud/projects/one/covers/{blob}', content=first, headers=_headers(a)).status_code == 200
        foreign = client.get(f'/api/v1/cloud/projects/one/covers/{blob}', headers={'Authorization': f'Bearer {b}'})
        assert foreign.status_code == 404 and str(tmp_path) not in foreign.text
        assert client.put(f'/api/v1/cloud/projects/one/covers/{blob}', content=second, headers=_headers(b)).status_code == 200
        assert client.get(f'/api/v1/cloud/projects/one/covers/{blob}', headers={'Authorization': f'Bearer {a}'}).content == first
        assert client.get(f'/api/v1/cloud/projects/one/covers/{blob}', headers={'Authorization': f'Bearer {b}'}).content == second
        assert client.put(f'/api/v1/cloud/projects/one/covers/{blob}', content=first, headers=_headers(a)).json()['duplicate']
        for payload, headers, project in ((second, _headers(a), 'one'), (first, _headers(a, 'AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB'), 'one'), (first, _headers(a), 'two')):
            response = client.put(f'/api/v1/cloud/projects/{project}/covers/{blob}', content=payload, headers=headers)
            assert response.status_code == 409 and response.json()['detail']['code'] == 'encrypted_blob_id_conflict'
        with migrated_database.connect() as connection:
            row = connection.execute(text('SELECT project_id,ciphertext_size,ciphertext_sha256,nonce FROM encrypted_blobs WHERE user_id=:id AND blob_id=:blob'), {'id': first_user, 'blob': blob}).one()
            assert row.project_id == 'one' and row.ciphertext_size == len(first) and row.ciphertext_sha256 == hashlib.sha256(first).digest() and row.nonce == bytes(24)
        assert (tmp_path / 'blobs' / first_user.hex / f'{blob.hex}.blob').read_bytes() == first


def test_c14_http_size_and_canonical_headers(migrated_database, tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='test', database_url=_database_url(), auth_secret=AUTH_SECRET, cloud_blob_dir=tmp_path / 'blobs'))
    maximum = 2 * 1024 * 1024 + 16
    with TestClient(app) as client:
        user = create_user(migrated_database, username='Size', email='size@example.test'); token = login(client, 'Size').json()['access_token']
        assert client.post('/api/v1/cloud/projects/size', headers={'Authorization': f'Bearer {token}'}).status_code == 200
        def put(number, data, headers=None): return client.put(f'/api/v1/cloud/projects/size/covers/{UUID(int=300+number)}', content=data, headers=headers or _headers(token))
        assert put(1, b'a' * 15).json()['detail']['code'] == 'invalid_encrypted_blob'
        assert put(2, b'a' * 16).status_code == 200
        assert put(3, b'a' * maximum).status_code == 200
        assert put(4, b'a' * (maximum + 1)).status_code == 413
        for index, value in enumerate((None, '0', '2', 'abc', '+1', '01')):
            headers = _headers(token)
            if value is None: headers.pop('X-WORTA-Crypto-Version')
            else: headers['X-WORTA-Crypto-Version'] = value
            assert put(20 + index, b'a' * 16, headers).json()['detail']['code'] == 'invalid_encrypted_blob'
        for index, value in enumerate((None, '0', '2', 'abc', '+1', '01')):
            headers = _headers(token)
            if value is None: headers.pop('X-WORTA-AAD-Version')
            else: headers['X-WORTA-AAD-Version'] = value
            assert put(30 + index, b'a' * 16, headers).json()['detail']['code'] == 'invalid_encrypted_blob'
        for index, nonce in enumerate(('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', '!', 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', '')):
            headers = _headers(token, nonce)
            assert put(40 + index, b'a' * 16, headers).json()['detail']['code'] == 'invalid_encrypted_blob'


def test_c14_streamed_oversize_rejects_before_storage(migrated_database, tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='test', database_url=_database_url(), auth_secret=AUTH_SECRET, cloud_blob_dir=tmp_path / 'blobs'))
    blob = UUID('00000000-0000-0000-0000-000000000397')
    with TestClient(app) as client:
        user = create_user(migrated_database, username='Stream', email='stream@example.test')
        token = login(client, 'Stream').json()['access_token']
        assert client.post('/api/v1/cloud/projects/stream', headers={'Authorization': f'Bearer {token}'}).status_code == 200
    emitted: list[int] = []
    chunks = [b'a' * 1024 * 1024, b'b' * 1024 * 1024, b'c' * 17]
    messages = iter([{'type': 'http.request', 'body': chunk, 'more_body': index < 2} for index, chunk in enumerate(chunks)])
    sent = []
    async def receive():
        message = next(messages); emitted.append(len(message['body'])); return message
    async def send(message): sent.append(message)
    headers = _headers(token)
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': 'PUT',
             'scheme': 'http', 'path': f'/api/v1/cloud/projects/stream/covers/{blob}', 'raw_path': f'/api/v1/cloud/projects/stream/covers/{blob}'.encode(),
             'query_string': b'', 'headers': [(key.lower().encode(), value.encode()) for key, value in headers.items()],
             'client': ('127.0.0.1', 1234), 'server': ('testserver', 80), 'root_path': ''}
    asyncio.run(app(scope, receive, send))
    assert emitted == [1024 * 1024, 1024 * 1024, 17]
    assert sent[0]['status'] == 413 and b'encrypted_blob_too_large' in b''.join(message.get('body', b'') for message in sent)
    with migrated_database.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM encrypted_blobs WHERE user_id=:id AND blob_id=:blob'), {'id': user, 'blob': blob}).scalar_one() == 0
    target = tmp_path / 'blobs' / user.hex / f'{blob.hex}.blob'
    assert not target.exists() and not list(target.parent.glob('.upload-*'))


def test_c14_http_blob_integrity_fails_closed(migrated_database, tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='test', database_url=_database_url(), auth_secret=AUTH_SECRET, cloud_blob_dir=tmp_path / 'blobs'))
    with TestClient(app) as client:
        user = create_user(migrated_database, username='Integrity', email='integrity@example.test'); token = login(client, 'Integrity').json()['access_token']
        client.post('/api/v1/cloud/projects/integrity', headers={'Authorization': f'Bearer {token}'})
        for index, change, code in ((401, 'missing', 'encrypted_blob_unavailable'), (402, 'corrupt', 'encrypted_blob_corrupt'), (403, 'size', 'encrypted_blob_corrupt')):
            blob = UUID(int=index); data = b'a' * 16; path = tmp_path / 'blobs' / user.hex / f'{blob.hex}.blob'
            assert client.put(f'/api/v1/cloud/projects/integrity/covers/{blob}', content=data, headers=_headers(token)).status_code == 200
            if change == 'missing': path.unlink()
            elif change == 'corrupt': path.write_bytes(b'b' * 16)
            else: path.write_bytes(b'a' * 15)
            response = client.get(f'/api/v1/cloud/projects/integrity/covers/{blob}', headers={'Authorization': f'Bearer {token}'})
            assert response.status_code == 503 and response.json()['detail']['code'] == code and response.content != data and str(tmp_path) not in response.text
            with migrated_database.connect() as connection:
                assert connection.execute(text('SELECT count(*) FROM encrypted_blobs WHERE user_id=:id AND blob_id=:blob'), {'id': user, 'blob': blob}).scalar_one() == 1


def test_blob_store_immutable_publish_and_verification(tmp_path):
    store = FileSystemBlobStore(tmp_path); user = UUID(USER_ONE); blob = UUID(int=499); first = b'a' * 16
    store.create(user, blob, first)
    with pytest.raises(BlobAlreadyExists): store.create(user, blob, b'b' * 16)
    assert store.path_for(user, blob) == tmp_path / user.hex / f'{blob.hex}.blob'
    assert store.read_verified(user, blob, 16, hashlib.sha256(first).digest()) == first
    with pytest.raises(Exception): store.read_verified(user, blob, 16, b'x' * 32)
    with pytest.raises(Exception): store.read_verified(user, blob, 15, hashlib.sha256(first).digest())
    assert store.path_for(user, blob).read_bytes() == first and not list((tmp_path / user.hex).glob('.upload-*'))


def test_new_blob_flush_failure_removes_only_published_file(migrated_database, tmp_path):
    user = create_user(migrated_database, username='Flush', email='flush@example.test')
    from backend.app.cloud.services import CloudProjectService
    with Session(migrated_database) as setup:
        CloudProjectService().enable(setup, user, 'flush-project')
    blob = UUID(int=601); ciphertext = b'f' * 16; store = FileSystemBlobStore(tmp_path / 'blobs')
    target = store.path_for(user, blob); metadata = BlobMetadata('flush-project', blob, 1, 1, bytes(24)); seen = []
    with Session(migrated_database) as session:
        session.autoflush = False
        def fail_flush():
            assert target.exists() and target.read_bytes() == ciphertext
            seen.append(True); raise RuntimeError('simulated database flush failure')
        session.flush = fail_flush  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match='simulated database flush failure'):
            EncryptedBlobService(store).upload(session, user, metadata, ciphertext)
    assert seen == [True] and not target.exists() and not list(target.parent.glob('.upload-*'))
    with Session(migrated_database) as fresh:
        assert fresh.execute(text('SELECT count(*) FROM encrypted_blobs WHERE user_id=:id AND blob_id=:blob'), {'id': user, 'blob': blob}).scalar_one() == 0


def test_concurrent_exact_upload_is_create_then_duplicate(migrated_database, tmp_path):
    user = create_user(migrated_database, username='Concurrent', email='concurrent@example.test')
    from backend.app.cloud.services import CloudProjectService
    with Session(migrated_database) as setup: CloudProjectService().enable(setup, user, 'concurrent-project')
    blob = UUID(int=701); data = b'c' * 16; store = FileSystemBlobStore(tmp_path / 'blobs'); metadata = BlobMetadata('concurrent-project', blob, 1, 1, bytes(24)); barrier = threading.Barrier(2)
    def upload():
        with Session(migrated_database) as session:
            barrier.wait(timeout=10)
            return EncryptedBlobService(store).upload(session, user, metadata, data)
    with ThreadPoolExecutor(max_workers=2) as executor: results = list(executor.map(lambda _: upload(), range(2)))
    assert sorted(results) == [False, True]
    target = store.path_for(user, blob)
    assert target.read_bytes() == data and not list(target.parent.glob('.upload-*'))
    with Session(migrated_database) as fresh:
        assert fresh.execute(text('SELECT count(*) FROM encrypted_blobs WHERE user_id=:id AND blob_id=:blob'), {'id': user, 'blob': blob}).scalar_one() == 1


def test_concurrent_conflicting_upload_preserves_one_winner(migrated_database, tmp_path):
    user = create_user(migrated_database, username='Race', email='race@example.test')
    from backend.app.cloud.services import CloudProjectService
    with Session(migrated_database) as setup: CloudProjectService().enable(setup, user, 'race-project')
    blob = UUID(int=702); store = FileSystemBlobStore(tmp_path / 'blobs'); barrier = threading.Barrier(2)
    candidates = [(b'a' * 16, bytes(24)), (b'b' * 16, b'\x01' * 24)]
    def upload(candidate):
        with Session(migrated_database) as session:
            barrier.wait(timeout=10)
            try: return ('created', candidate, EncryptedBlobService(store).upload(session, user, BlobMetadata('race-project', blob, 1, 1, candidate[1]), candidate[0]))
            except Exception as error: return ('error', candidate, error)
    with ThreadPoolExecutor(max_workers=2) as executor: results = list(executor.map(upload, candidates))
    winner = next(result for result in results if result[0] == 'created')
    loser = next(result for result in results if result[0] == 'error')
    assert winner[2] is False and getattr(loser[2], 'code') == 'encrypted_blob_id_conflict' and getattr(loser[2], 'status_code') == 409
    data, nonce = winner[1]; target = store.path_for(user, blob)
    assert target.read_bytes() == data and not list(target.parent.glob('.upload-*'))
    with Session(migrated_database) as fresh:
        row = fresh.execute(text('SELECT nonce,ciphertext_size,ciphertext_sha256 FROM encrypted_blobs WHERE user_id=:id AND blob_id=:blob'), {'id': user, 'blob': blob}).one()
        assert row.nonce == nonce and row.ciphertext_size == len(data) and row.ciphertext_sha256 == hashlib.sha256(data).digest()


def test_filesystem_blob_store_is_raw_immutable_and_uuid_addressed(tmp_path: Path):
    store = FileSystemBlobStore(tmp_path)
    user = UUID(USER_ONE)
    ciphertext = b'ciphertext-not-base64'
    store.create(user, BLOB, ciphertext)
    target = tmp_path / user.hex / f'{BLOB.hex}.blob'
    assert target.read_bytes() == ciphertext
    assert target.name == f'{BLOB.hex}.blob'
    with pytest.raises(BlobAlreadyExists):
        store.create(user, BLOB, b'different')
    assert store.read_verified(user, BLOB, len(ciphertext), hashlib.sha256(ciphertext).digest()) == ciphertext
    assert not list(target.parent.glob('.upload-*'))


@pytest.mark.skipif(not os.environ.get('NFPROGRESS_TEST_DATABASE_URL'), reason='requires dedicated real PostgreSQL')
def test_c14_postgresql_constraints_and_c13_roundtrip(monkeypatch):
    url = os.environ['NFPROGRESS_TEST_DATABASE_URL']
    engine = create_engine(url)
    config = AlembicConfig(str(ROOT / 'alembic.ini'))
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', url)
    try:
        with engine.begin() as connection:
            _drop_all(connection)
        command.upgrade(config, 'c13_encrypted_cloud_schema')
        with engine.begin() as connection:
            _insert_user(connection, USER_ONE, 'C14 One')
            connection.execute(text("INSERT INTO cloud_projects(user_id,project_id) VALUES (:user_id, 'c14-project')"), {'user_id': USER_ONE})
            _insert_event(connection, USER_ONE, '00000000-0000-0000-0000-000000000202', 1)
            _insert_user_crypto(connection, USER_ONE)
            connection.execute(text("""INSERT INTO encrypted_objects(user_id,event_id,crypto_version,aad_version,nonce,ciphertext)
                VALUES (:user_id,'00000000-0000-0000-0000-000000000202',1,1,:nonce,:ciphertext)"""), {'user_id': USER_ONE, 'nonce': b'a' * 24, 'ciphertext': b'b' * 16})
        command.upgrade(config, 'c14_encrypted_cover_blobs')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT username FROM users WHERE id=:id'), {'id': USER_ONE}).scalar_one() == 'C14 One'
            assert connection.execute(text('SELECT project_id FROM cloud_projects WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == 'c14-project'
            assert connection.execute(text('SELECT ciphertext FROM encrypted_objects WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == b'b' * 16
            assert connection.execute(text('SELECT password_wrapped_amk FROM user_crypto WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == b'c' * 48
        valid = {'user_id': USER_ONE, 'blob_id': str(BLOB), 'project_id': 'project', 'kind': 'project_cover',
                 'crypto_version': 1, 'aad_version': 1, 'nonce': b'n' * 24,
                 'ciphertext_size': 16, 'ciphertext_sha256': b'h' * 32}
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO encrypted_blobs(user_id,blob_id,project_id,kind,crypto_version,aad_version,nonce,ciphertext_size,ciphertext_sha256)
                VALUES (:user_id,:blob_id,:project_id,:kind,:crypto_version,:aad_version,:nonce,:ciphertext_size,:ciphertext_sha256)"""), valid)
        with engine.connect() as connection:
            columns = {column['name'] for column in inspect(connection).get_columns('encrypted_blobs')}
            assert columns == {'user_id', 'blob_id', 'project_id', 'kind', 'crypto_version', 'aad_version', 'nonce', 'ciphertext_size', 'ciphertext_sha256', 'created_at'}
            for index, changes in enumerate(({'crypto_version': 0}, {'aad_version': 0}, {'nonce': b'n' * 23}, {'nonce': b'n' * 25},
                            {'ciphertext_size': 15}, {'ciphertext_size': MAX_COVER_CIPHERTEXT_BYTES + 1},
                            {'ciphertext_sha256': b'h' * 31}, {'ciphertext_sha256': b'h' * 33}, {'kind': 'attachment'})):
                candidate = {**valid, **changes, 'blob_id': str(UUID(int=BLOB.int + index + 1))}
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(text("""INSERT INTO encrypted_blobs(user_id,blob_id,project_id,kind,crypto_version,aad_version,nonce,ciphertext_size,ciphertext_sha256)
                        VALUES (:user_id,:blob_id,:project_id,:kind,:crypto_version,:aad_version,:nonce,:ciphertext_size,:ciphertext_sha256)"""), candidate)
        command.downgrade(config, 'c13_encrypted_cloud_schema')
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            assert 'encrypted_blobs' not in tables and {'user_crypto', 'encrypted_objects', 'sync_events', 'cloud_projects'} <= tables
            assert connection.execute(text('SELECT username FROM users WHERE id=:id'), {'id': USER_ONE}).scalar_one() == 'C14 One'
            assert connection.execute(text('SELECT project_id FROM cloud_projects WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == 'c14-project'
            assert connection.execute(text('SELECT ciphertext FROM encrypted_objects WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == b'b' * 16
            assert connection.execute(text('SELECT password_wrapped_amk FROM user_crypto WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == b'c' * 48
        command.upgrade(config, 'c14_encrypted_cover_blobs')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT count(*) FROM encrypted_blobs')).scalar_one() == 0
            assert connection.execute(text('SELECT project_id FROM cloud_projects WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == 'c14-project'
            assert connection.execute(text('SELECT ciphertext FROM encrypted_objects WHERE user_id=:id'), {'id': USER_ONE}).scalar_one() == b'b' * 16
    finally:
        with engine.begin() as connection:
            _drop_all(connection)
        engine.dispose()
