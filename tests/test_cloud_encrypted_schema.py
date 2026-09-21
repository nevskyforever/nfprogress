from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.app.cloud.models import EncryptedObject, UserCrypto
from backend.app.cloud.schemas import (ObjectEnvelopeDto, PasswordWrappedAmkDto,
                                       RecoveryWrappedAmkDto,
                                       decode_canonical_base64url)


ROOT = Path(__file__).resolve().parents[1]
USER_ONE = '00000000-0000-0000-0000-000000000131'
USER_TWO = '00000000-0000-0000-0000-000000000132'
USER_THREE = '00000000-0000-0000-0000-000000000135'
EVENT_ID = '00000000-0000-0000-0000-000000000133'
BAD_EVENT_ID = '00000000-0000-0000-0000-000000000134'


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def password_dto() -> dict[str, object]:
    return {
        'crypto_version': 1, 'wrapping_version': 1,
        'kdf': {'kdf_version': 1, 'algorithm': 'argon2id13', 'salt': b64(b'a' * 16), 'opslimit': 2, 'memlimit': 67_108_864},
        'nonce': b64(b'b' * 24), 'ciphertext': b64(b'c' * 48),
    }


def test_c13_wire_dtos_accept_only_canonical_base64url_and_c11_shapes():
    password = PasswordWrappedAmkDto.model_validate(password_dto())
    assert decode_canonical_base64url(password.nonce, expected_length=24) == b'b' * 24
    assert RecoveryWrappedAmkDto.model_validate({
        'crypto_version': 1, 'wrapping_version': 1, 'nonce': b64(b'd' * 24), 'ciphertext': b64(b'e' * 48),
    })
    assert ObjectEnvelopeDto.model_validate({
        'crypto_version': 1, 'aad_version': 1, 'nonce': b64(b'f' * 24), 'ciphertext': b64(b'g' * 16),
    })

    for value in ('a', 'YWJj=', 'YWJj+', 'YWJj/', 'YWJj\n'):
        with pytest.raises(ValidationError):
            PasswordWrappedAmkDto.model_validate({**password_dto(), 'nonce': value})
    for field, value in (('salt', b64(b'a' * 15)), ('nonce', b64(b'b' * 23)), ('ciphertext', b64(b'c' * 47))):
        candidate = password_dto()
        if field == 'salt':
            candidate['kdf'] = {**candidate['kdf'], field: value}  # type: ignore[index]
        else:
            candidate[field] = value
        with pytest.raises(ValidationError):
            PasswordWrappedAmkDto.model_validate(candidate)
    with pytest.raises(ValidationError):
        ObjectEnvelopeDto.model_validate({
            'crypto_version': 1, 'aad_version': 1, 'nonce': b64(b'f' * 24), 'ciphertext': b64(b'g' * 15),
        })


def _drop_all(connection) -> None:
    for table in ('encrypted_objects', 'user_crypto', 'sync_events', 'sync_devices', 'sync_user_state', 'cloud_projects',
                  'reserved_usernames', 'user_limit_overrides', 'global_limits', 'registration_settings',
                  'password_reset_tokens', 'email_verification_tokens', 'auth_refresh_tokens', 'auth_sessions',
                  'users', 'alembic_version'):
        connection.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))


def _insert_user(connection, user_id: str, username: str) -> None:
    connection.execute(text("""INSERT INTO users(id, username, username_normalized, email, email_normalized,
        email_verified, password_hash, role, status) VALUES
        (:id, :username, :normalized, :email, :email, true, 'hash', 'user', 'active')"""), {
        'id': user_id, 'username': username, 'normalized': username.lower(), 'email': f'{username.lower()}@example.test',
    })


def _insert_event(connection, user_id: str, event_id: str, sequence: int) -> None:
    connection.execute(text("""INSERT INTO sync_events(user_id, event_id, device_id, project_id, entity_id,
        entity_type, operation, revision, updated_at, deleted_at, server_sequence)
        VALUES (:user_id, :event_id, '00000000-0000-0000-0000-000000000199', 'project', 'entity',
        'document', 'upsert', 1, timezone('utc', now()), NULL, :sequence)"""), {
        'user_id': user_id, 'event_id': event_id, 'sequence': sequence,
    })


def _insert_user_crypto(connection, user_id: str, **changes: object) -> None:
    values: dict[str, object] = {
        'user_id': user_id, 'password_crypto_version': 1, 'password_wrapping_version': 1,
        'kdf_version': 1, 'kdf_algorithm': 'argon2id13', 'kdf_salt': b'a' * 16,
        'kdf_opslimit': 2, 'kdf_memlimit': 67_108_864, 'password_nonce': b'b' * 24,
        'password_wrapped_amk': b'c' * 48, 'recovery_crypto_version': None,
        'recovery_wrapping_version': None, 'recovery_nonce': None, 'recovery_wrapped_amk': None,
    }
    values.update(changes)
    connection.execute(text("""INSERT INTO user_crypto(user_id, password_crypto_version, password_wrapping_version,
        kdf_version, kdf_algorithm, kdf_salt, kdf_opslimit, kdf_memlimit, password_nonce, password_wrapped_amk,
        recovery_crypto_version, recovery_wrapping_version, recovery_nonce, recovery_wrapped_amk)
        VALUES (:user_id, :password_crypto_version, :password_wrapping_version, :kdf_version, :kdf_algorithm,
        :kdf_salt, :kdf_opslimit, :kdf_memlimit, :password_nonce, :password_wrapped_amk,
        :recovery_crypto_version, :recovery_wrapping_version, :recovery_nonce, :recovery_wrapped_amk)"""), values)


@pytest.mark.skipif(not os.environ.get('NFPROGRESS_TEST_DATABASE_URL'), reason='requires dedicated real PostgreSQL')
def test_c13_postgresql_migration_constraints_isolation_and_roundtrip(monkeypatch):
    url = os.environ['NFPROGRESS_TEST_DATABASE_URL']
    assert url.startswith('postgresql+psycopg://')
    engine = create_engine(url)
    config = AlembicConfig(str(ROOT / 'alembic.ini'))
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', url)
    try:
        with engine.begin() as connection:
            _drop_all(connection)
        command.upgrade(config, 'c9_sync_protocol')
        with engine.begin() as connection:
            _insert_user(connection, USER_ONE, 'C13 One')
            _insert_user(connection, USER_TWO, 'C13 Two')
            _insert_user(connection, USER_THREE, 'C13 Three')
            connection.execute(text("INSERT INTO cloud_projects(user_id, project_id) VALUES (:user_id, 'c13-project')"), {'user_id': USER_ONE})
            _insert_event(connection, USER_ONE, EVENT_ID, 1)
            _insert_event(connection, USER_TWO, EVENT_ID, 1)
            _insert_event(connection, USER_THREE, EVENT_ID, 1)
            _insert_event(connection, USER_TWO, BAD_EVENT_ID, 2)
            for index in range(13):
                _insert_user(connection, f'00000000-0000-0000-0000-000000000{140 + index}', f'C13 Invalid {index}')
        command.upgrade(config, 'c13_encrypted_cloud_schema')
        with engine.begin() as connection:
            _insert_user_crypto(connection, USER_ONE, recovery_crypto_version=1, recovery_wrapping_version=1,
                                recovery_nonce=b'd' * 24, recovery_wrapped_amk=b'e' * 48)
            _insert_user_crypto(connection, USER_TWO)
            _insert_user_crypto(connection, USER_THREE)
            for user_id, byte in ((USER_ONE, b'f'), (USER_TWO, b'g'), (USER_THREE, b'i')):
                connection.execute(text("""INSERT INTO encrypted_objects(user_id,event_id,crypto_version,aad_version,nonce,ciphertext)
                    VALUES (:user_id,:event_id,1,1,:nonce,:ciphertext)"""), {
                    'user_id': user_id, 'event_id': EVENT_ID, 'nonce': b'h' * 24, 'ciphertext': byte * 16,
                })

        with engine.connect() as connection:
            inspector = inspect(connection)
            assert {column['name'] for column in inspector.get_columns('user_crypto')} == {
                'user_id', 'password_crypto_version', 'password_wrapping_version', 'kdf_version', 'kdf_algorithm',
                'kdf_salt', 'kdf_opslimit', 'kdf_memlimit', 'password_nonce', 'password_wrapped_amk',
                'recovery_crypto_version', 'recovery_wrapping_version', 'recovery_nonce', 'recovery_wrapped_amk',
                'created_at', 'updated_at',
            }
            assert {column['name'] for column in inspector.get_columns('encrypted_objects')} == {
                'user_id', 'event_id', 'crypto_version', 'aad_version', 'nonce', 'ciphertext', 'stored_at',
            }
            assert set(UserCrypto.__table__.columns.keys()) == {column['name'] for column in inspector.get_columns('user_crypto')}
            assert set(EncryptedObject.__table__.columns.keys()) == {column['name'] for column in inspector.get_columns('encrypted_objects')}
            assert {'payload', 'ciphertext', 'content', 'nonce'}.isdisjoint({column['name'] for column in inspector.get_columns('sync_events')})

        invalid_crypto = [
            {'kdf_salt': b'a' * 15}, {'kdf_salt': b'a' * 17}, {'password_nonce': b'b' * 23},
            {'password_nonce': b'b' * 25}, {'password_wrapped_amk': b'c' * 47}, {'password_wrapped_amk': b'c' * 49},
            {'password_crypto_version': 0}, {'password_wrapping_version': -1}, {'kdf_version': 0},
            {'kdf_opslimit': 0}, {'kdf_memlimit': -1}, {'recovery_crypto_version': 1},
            {'recovery_crypto_version': 1, 'recovery_wrapping_version': 1, 'recovery_nonce': b'd' * 23, 'recovery_wrapped_amk': b'e' * 48},
            {'recovery_crypto_version': 1, 'recovery_wrapping_version': 1, 'recovery_nonce': b'd' * 24, 'recovery_wrapped_amk': b'e' * 47},
        ]
        with engine.connect() as connection:
            for index, values in enumerate(invalid_crypto):
                with pytest.raises(IntegrityError), connection.begin_nested():
                    _insert_user_crypto(connection, f'00000000-0000-0000-0000-000000000{140 + index}', **values)
            for values in ({'nonce': b'h' * 23}, {'nonce': b'h' * 25}, {'ciphertext': b'i' * 15},
                           {'crypto_version': 0}, {'aad_version': 0}, {'user_id': USER_ONE, 'event_id': BAD_EVENT_ID}):
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(text("""INSERT INTO encrypted_objects(user_id,event_id,crypto_version,aad_version,nonce,ciphertext)
                        VALUES (:user_id,:event_id,:crypto_version,:aad_version,:nonce,:ciphertext)"""), {
                        'user_id': USER_TWO, 'event_id': BAD_EVENT_ID, 'crypto_version': 1, 'aad_version': 1,
                        'nonce': b'h' * 24, 'ciphertext': b'i' * 16, **values,
                    })

        with engine.begin() as connection:
            connection.execute(text('DELETE FROM users WHERE id = :id'), {'id': USER_THREE})
            assert connection.execute(text('SELECT count(*) FROM user_crypto WHERE user_id = :id'), {'id': USER_THREE}).scalar_one() == 0
            assert connection.execute(text('SELECT count(*) FROM encrypted_objects WHERE user_id = :id'), {'id': USER_THREE}).scalar_one() == 0
            assert connection.execute(text('SELECT count(*) FROM encrypted_objects WHERE user_id = :id'), {'id': USER_TWO}).scalar_one() == 1

        command.downgrade(config, 'c9_sync_protocol')
        with engine.connect() as connection:
            assert not {'user_crypto', 'encrypted_objects'} & set(inspect(connection).get_table_names())
            assert connection.execute(text('SELECT count(*) FROM sync_events WHERE user_id = :id'), {'id': USER_TWO}).scalar_one() == 2
            assert connection.execute(text('SELECT count(*) FROM users WHERE id = :id'), {'id': USER_TWO}).scalar_one() == 1
            assert connection.execute(text('SELECT project_id FROM cloud_projects WHERE user_id = :id'), {'id': USER_ONE}).scalar_one() == 'c13-project'
        command.upgrade(config, 'c13_encrypted_cloud_schema')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'c13_encrypted_cloud_schema'
    finally:
        with engine.begin() as connection:
            _drop_all(connection)
        engine.dispose()
