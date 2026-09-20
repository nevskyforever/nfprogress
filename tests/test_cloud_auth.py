from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pytest
import jwt
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.cloud.models import AuthRefreshToken, AuthSession, User
from backend.app.cloud.repositories import normalize_username
from backend.app.cloud.services import AccountService
from backend.app.cloud.tokens import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, TokenService, utc_now
from backend.app.config import RuntimeConfig
from backend.app.main import create_app


ROOT = Path(__file__).resolve().parents[1]
AUTH_SECRET = 'test-only-auth-secret-with-at-least-32-characters'


def _database_url() -> str:
    return os.environ['NFPROGRESS_TEST_DATABASE_URL']


@pytest.fixture()
def migrated_database(monkeypatch):
    if not os.environ.get('NFPROGRESS_TEST_DATABASE_URL'):
        pytest.skip('requires dedicated real PostgreSQL database in NFPROGRESS_TEST_DATABASE_URL')
    url = _database_url()
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', url)
    monkeypatch.setenv('NFPROGRESS_ENV', 'test')
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text('DROP TABLE IF EXISTS auth_refresh_tokens CASCADE'))
        connection.execute(text('DROP TABLE IF EXISTS auth_sessions CASCADE'))
        connection.execute(text('DROP TABLE IF EXISTS users CASCADE'))
        connection.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE'))
    alembic_config = AlembicConfig(str(ROOT / 'alembic.ini'))
    command.upgrade(alembic_config, 'head')
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            connection.execute(text('DROP TABLE IF EXISTS auth_refresh_tokens CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS auth_sessions CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS users CASCADE'))
            connection.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE'))
        engine.dispose()


@pytest.fixture()
def cloud_client(migrated_database, tmp_path):
    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='test', database_url=_database_url(), auth_secret=AUTH_SECRET))
    with TestClient(app) as client:
        yield client, migrated_database


def create_user(engine, *, username='Arthur', email='arthur@example.test', password='correct horse battery staple', status='active'):
    with Session(engine) as session:
        user = AccountService().create_user(session, username=username, email=email, password=password, status=status)
        session.commit()
        session.refresh(user)
        return user.id


def login(client, username='Arthur', password='correct horse battery staple'):
    return client.post('/api/v1/auth/login', json={'username': username, 'password': password})


def test_c2_schema_and_repeated_head_upgrade(migrated_database, monkeypatch):
    assert set(inspect(migrated_database).get_table_names()) == {
        'alembic_version', 'users', 'auth_sessions', 'auth_refresh_tokens',
    }
    assert inspect(migrated_database).get_columns('users')[0]['name'] == 'id'
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', _database_url())
    command.upgrade(AlembicConfig(str(ROOT / 'alembic.ini')), 'head')
    with migrated_database.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'c2_account_auth_core'


def test_user_normalization_password_hash_and_unique_constraints(migrated_database):
    user_id = create_user(migrated_database)
    with Session(migrated_database) as session:
        user = session.get(User, user_id)
        assert normalize_username(' Arthur ') == 'arthur'
        assert user.password_hash.startswith('$argon2id$')
        assert 'correct horse battery staple' not in user.password_hash
        AccountService().create_user(session, username='arthur', email='another@example.test', password='x' * 15, status='active')
        with pytest.raises(IntegrityError):
            session.commit()

    with Session(migrated_database) as session:
        AccountService().create_user(session, username='Different', email='ARTHUR@example.test', password='x' * 15, status='active')
        with pytest.raises(IntegrityError):
            session.commit()


def test_login_account_access_logout_and_ownership(cloud_client):
    client, engine = cloud_client
    first_id = create_user(engine)
    second_id = create_user(engine, username='Other', email='other@example.test')
    response = login(client, 'ARTHUR')
    assert response.status_code == 200
    tokens = response.json()
    assert tokens['token_type'] == 'bearer' and tokens['access_expires_in'] == 900
    me = client.get('/api/v1/account/me', headers={'Authorization': f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200 and me.json()['id'] == str(first_id)
    assert me.json()['id'] != str(second_id)
    assert 'password_hash' not in me.json()
    logout = client.post('/api/v1/auth/logout', headers={'Authorization': f"Bearer {tokens['access_token']}"})
    assert logout.status_code == 204
    assert client.get('/api/v1/account/me', headers={'Authorization': f"Bearer {tokens['access_token']}"}).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401


@pytest.mark.parametrize('status', ['pending', 'rejected', 'blocked'])
def test_non_active_users_cannot_login(cloud_client, status):
    client, engine = cloud_client
    create_user(engine, status=status)
    response = login(client)
    assert response.status_code == 401
    assert response.json()['detail']['code'] == 'invalid_credentials'


def test_bad_credentials_have_same_contract(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    wrong_password = login(client, password='wrong password that is long enough')
    unknown = login(client, username='Nobody', password='wrong password that is long enough')
    assert wrong_password.status_code == unknown.status_code == 401
    assert wrong_password.json() == unknown.json()


def test_refresh_rotation_replay_revokes_session(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    first = login(client).json()
    rotated = client.post('/api/v1/auth/refresh', json={'refresh_token': first['refresh_token']})
    assert rotated.status_code == 200
    second = rotated.json()
    assert second['refresh_token'] != first['refresh_token']
    with Session(engine) as session:
        assert first['refresh_token'] not in str(session.query(AuthRefreshToken).all())
        row = session.query(AuthRefreshToken).first()
        assert row.token_hash not in first['refresh_token']
    replay = client.post('/api/v1/auth/refresh', json={'refresh_token': first['refresh_token']})
    assert replay.status_code == 401
    assert client.get('/api/v1/account/me', headers={'Authorization': f"Bearer {second['access_token']}"}).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': second['refresh_token']}).status_code == 401


def test_access_token_validation_and_blocked_user(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine)
    tokens = login(client).json()
    token_service = TokenService(AUTH_SECRET)
    with Session(engine) as session:
        auth_session = session.query(AuthSession).one()
        expired = token_service.issue_access_token(user_id, auth_session.id, utc_now() - timedelta(hours=1))
    assert client.get('/api/v1/account/me', headers={'Authorization': f'Bearer {expired}'}).status_code == 401
    wrong_signature = TokenService('another-secret-that-is-definitely-long-enough').issue_access_token(user_id, auth_session.id)
    assert client.get('/api/v1/account/me', headers={'Authorization': f'Bearer {wrong_signature}'}).status_code == 401
    with Session(engine) as session:
        session.get(User, user_id).status = 'blocked'
        session.commit()
    assert client.get('/api/v1/account/me', headers={'Authorization': f"Bearer {tokens['access_token']}"}).status_code == 401


def test_access_jwt_requires_expected_claims_issuer_audience_and_algorithm(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    tokens = login(client).json()
    claims = jwt.decode(tokens['access_token'], AUTH_SECRET, algorithms=[JWT_ALGORITHM], audience=JWT_AUDIENCE)
    invalid_payloads = [
        {key: value for key, value in claims.items() if key != 'jti'},
        {**claims, 'iss': 'wrong-issuer'},
        {**claims, 'aud': 'wrong-audience'},
    ]
    for payload in invalid_payloads:
        forged = jwt.encode(payload, AUTH_SECRET, algorithm=JWT_ALGORITHM)
        assert client.get('/api/v1/account/me', headers={'Authorization': f'Bearer {forged}'}).status_code == 401
    unsigned = jwt.encode(claims, key='', algorithm='none')
    assert client.get('/api/v1/account/me', headers={'Authorization': f'Bearer {unsigned}'}).status_code == 401
