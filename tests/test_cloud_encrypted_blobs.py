from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.app.cloud.blob_store import BlobAlreadyExists, FileSystemBlobStore
from backend.app.cloud.encrypted_blobs_service import MAX_COVER_CIPHERTEXT_BYTES
from test_cloud_encrypted_schema import ROOT, USER_ONE, _drop_all, _insert_event, _insert_user, _insert_user_crypto


BLOB = UUID('00000000-0000-0000-0000-000000000201')


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
            _insert_event(connection, USER_ONE, '00000000-0000-0000-0000-000000000202', 1)
            _insert_user_crypto(connection, USER_ONE)
            connection.execute(text("""INSERT INTO encrypted_objects(user_id,event_id,crypto_version,aad_version,nonce,ciphertext)
                VALUES (:user_id,'00000000-0000-0000-0000-000000000202',1,1,:nonce,:ciphertext)"""), {'user_id': USER_ONE, 'nonce': b'a' * 24, 'ciphertext': b'b' * 16})
        command.upgrade(config, 'c14_encrypted_cover_blobs')
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
        command.upgrade(config, 'c14_encrypted_cover_blobs')
    finally:
        with engine.begin() as connection:
            _drop_all(connection)
        engine.dispose()
