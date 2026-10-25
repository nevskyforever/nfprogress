from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from backend.app.cloud.passwords import PasswordCapacityError, PasswordService
from backend.app.db import CloudDatabase, DatabaseReadiness
from backend.app.db.database import POSTGRESQL_POOL_SIZE
from test_cloud_auth import cloud_client, create_user, login, migrated_database


def test_argon2_hash_compatibility_and_capacity_recovery(monkeypatch):
    service = PasswordService()
    password = 'test-only-long-password'
    stored = service.hash(password)
    assert stored.startswith('$argon2id$')
    assert service.verify(password, stored)[0]
    assert not service.verify('wrong-long-password', stored)[0]
    service.verify_dummy(password)

    monkeypatch.setattr('backend.app.cloud.passwords.ARGON2_WAIT_TIMEOUT_SECONDS', 0.02)
    assert service._slots.acquire(timeout=1)
    try:
        with pytest.raises(PasswordCapacityError, match='capacity'):
            service.hash(password)
        with pytest.raises(PasswordCapacityError, match='capacity'):
            service.verify(password, stored)
    finally:
        service._slots.release()
    assert service.verify(password, stored)[0]


@pytest.mark.skipif(not os.environ.get('NFPROGRESS_TEST_DATABASE_URL'),
                    reason='requires an isolated PostgreSQL test database')
def test_postgresql_pool_exhaustion_and_recovery():
    database = CloudDatabase(os.environ['NFPROGRESS_TEST_DATABASE_URL'])
    checked_out = [database.engine.connect() for _ in range(POSTGRESQL_POOL_SIZE)]
    try:
        assert database.readiness() == DatabaseReadiness.UNAVAILABLE
        with pytest.raises(PoolTimeoutError):
            with database.engine.connect():
                pass
    finally:
        for connection in checked_out:
            connection.close()
    try:
        assert database.readiness() == DatabaseReadiness.READY
        scope = database.session_scope()
        try:
            session = next(scope)
            assert session.scalar(text('SELECT 1')) == 1
        finally:
            scope.close()
    finally:
        database.dispose()


def test_cloud_endpoint_returns_503_on_argon2_capacity_and_recovers(cloud_client, monkeypatch):
    client, engine = cloud_client
    create_user(engine)
    service = PasswordService()
    monkeypatch.setattr('backend.app.cloud.passwords.ARGON2_WAIT_TIMEOUT_SECONDS', 0.02)
    assert service._slots.acquire(timeout=1)
    try:
        response = login(client)
        assert response.status_code == 503
        assert response.json()['detail']['code'] == 'password_capacity_unavailable'
        assert response.headers['Retry-After'] == '2'
    finally:
        service._slots.release()
    assert login(client).status_code == 200


def test_cloud_endpoint_returns_503_on_pool_capacity_and_recovers(cloud_client):
    client, _engine = cloud_client
    database = client.app.state.cloud_database
    checked_out = [database.engine.connect() for _ in range(POSTGRESQL_POOL_SIZE)]
    try:
        response = client.get('/api/v1/auth/registration')
        assert response.status_code == 503
        assert response.json()['detail']['code'] == 'database_capacity_unavailable'
    finally:
        for connection in checked_out:
            connection.close()
    response = client.get('/api/v1/auth/registration')
    assert response.status_code == 200 and response.json()['mode'] == 'closed'
