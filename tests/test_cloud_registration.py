from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.cloud.models import EmailVerificationToken, RegistrationSettings, User
from backend.app.cloud.services import AccountEmailService, RegistrationService
from backend.app.cloud.tokens import TokenService, utc_now
from backend.app.config import RuntimeConfig
from backend.app.main import create_app
from test_cloud_auth import (AUTH_SECRET, ROOT, _database_url, cloud_client,
                             create_user, login, migrated_database)


def _set_policy(engine, *, mode: str, max_users: int | None = None) -> None:
    with Session(engine) as session:
        settings = session.get(RegistrationSettings, 1)
        assert settings is not None
        settings.mode, settings.max_users = mode, max_users
        session.commit()


def _token(sender) -> str:
    match = re.search(r'/verify-email\?token=([^\s]+)', sender.messages[-1].body)
    assert match
    return match.group(1)


def _register(client, *, username='NewWriter', email='new@example.com', password='пароль с Unicode достаточно длинный'):
    return client.post('/api/v1/auth/register', json={
        'username': username, 'email': email, 'password': password,
    })


def test_c4_migration_seed_and_downgrade_upgrade(migrated_database, monkeypatch):
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', _database_url())
    config = AlembicConfig(str(ROOT / 'alembic.ini'))
    command.downgrade(config, 'base')
    for revision in ('c1_postgresql_foundation', 'c2_account_auth_core',
                     'c3_email_account_recovery', 'c4_registration_controls'):
        command.upgrade(config, revision)
    with Session(migrated_database) as session:
        settings = session.get(RegistrationSettings, 1)
        assert settings is not None and settings.mode == 'closed' and settings.max_users is None
    command.downgrade(config, 'c3_email_account_recovery')
    with migrated_database.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'c3_email_account_recovery'
    command.upgrade(config, 'c4_registration_controls')
    with Session(migrated_database) as session:
        settings = session.get(RegistrationSettings, 1)
        assert settings is not None and settings.mode == 'closed' and settings.max_users is None


def test_closed_policy_and_public_policy_are_safe(cloud_client):
    client, engine = cloud_client
    assert client.get('/api/v1/auth/registration').json() == {
        'mode': 'closed', 'registration_enabled': False, 'requires_approval': False,
    }
    response = _register(client)
    assert response.status_code == 403 and response.json()['detail']['code'] == 'registration_closed'
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
    create_user(engine)
    assert login(client).status_code == 200


def test_open_registration_verification_and_duplicate_contract(cloud_client):
    client, engine = cloud_client
    _set_policy(engine, mode='open')
    first = _register(client)
    duplicate_username = _register(client, username=' newwriter ', email='other@example.com')
    duplicate_email = _register(client, username='OtherWriter', email=' NEW@EXAMPLE.COM ')
    assert first.status_code == duplicate_username.status_code == duplicate_email.status_code == 202
    assert first.json() == duplicate_username.json() == duplicate_email.json() == {'code': 'registration_request_accepted'}
    sender = client.app.state.email_sender
    assert len(sender.messages) == 1
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.username_normalized == 'newwriter'))
        assert user is not None
        assert user.role == 'user' and user.status == 'pending' and not user.email_verified
        assert user.registration_mode_at_signup == 'open'
        assert session.scalar(select(func.count()).select_from(User)) == 1
    assert login(client, 'NewWriter', 'пароль с Unicode достаточно длинный').status_code == 401
    verified = client.post('/api/v1/auth/email/verify', json={'token': _token(sender)})
    assert verified.json() == {'code': 'email_verified', 'account_status': 'active', 'activation': 'active'}
    assert login(client, 'NewWriter', 'пароль с Unicode достаточно длинный').status_code == 200


@pytest.mark.parametrize('start_mode,end_mode,expected', [
    ('open', 'closed', ('active', 'active')),
    ('open', 'approval', ('active', 'active')),
    ('approval', 'open', ('pending', 'approval_required')),
    ('approval', 'closed', ('pending', 'approval_required')),
])
def test_signup_policy_snapshot_survives_global_change(cloud_client, start_mode, end_mode, expected):
    client, engine = cloud_client
    _set_policy(engine, mode=start_mode)
    assert _register(client, username=f'{start_mode}{end_mode}', email=f'{start_mode}-{end_mode}@example.com').status_code == 202
    raw = _token(client.app.state.email_sender)
    _set_policy(engine, mode=end_mode)
    response = client.post('/api/v1/auth/email/verify', json={'token': raw})
    assert (response.json()['account_status'], response.json()['activation']) == expected


def test_approval_and_capacity_results(cloud_client):
    client, engine = cloud_client
    _set_policy(engine, mode='approval')
    _register(client, username='Approval', email='approval@example.com')
    assert client.post('/api/v1/auth/email/verify', json={'token': _token(client.app.state.email_sender)}).json()['activation'] == 'approval_required'
    assert login(client, 'Approval', 'пароль с Unicode достаточно длинный').status_code == 401
    _set_policy(engine, mode='open', max_users=0)
    _register(client, username='NoCapacity', email='capacity@example.com')
    response = client.post('/api/v1/auth/email/verify', json={'token': _token(client.app.state.email_sender)})
    assert response.json() == {'code': 'email_verified', 'account_status': 'pending', 'activation': 'capacity_reached'}
    with Session(engine) as session:
        assert session.scalar(select(User).where(User.username_normalized == 'nocapacity')).email_verified


def test_registration_validation_and_privilege_fields_are_rejected(cloud_client):
    client, _engine = cloud_client
    _set_policy(_engine, mode='open')
    cases = [
        {'username': '   ', 'email': 'valid@example.com', 'password': 'x' * 15},
        {'username': 'x' * 129, 'email': 'valid@example.com', 'password': 'x' * 15},
        {'username': 'Valid', 'email': 'bad-address', 'password': 'x' * 15},
        {'username': 'Valid', 'email': 'valid@example.com', 'password': 'too short'},
        {'username': 'Valid', 'email': 'valid@example.com', 'password': 'x' * 1025},
        {'username': 'Valid', 'email': 'valid@example.com', 'password': 'x' * 15, 'role': 'admin'},
        {'username': 'Valid', 'email': 'valid@example.com', 'password': 'x' * 15, 'status': 'active'},
        {'username': 'Valid', 'email': 'valid@example.com', 'password': 'x' * 15, 'email_verified': True},
        {'username': 'Valid', 'email': 'valid@example.com', 'password': 'x' * 15, 'registration_mode_at_signup': 'open'},
    ]
    assert all(client.post('/api/v1/auth/register', json=payload).status_code == 422 for payload in cases)


def test_public_resend_is_generic_and_only_delivers_to_eligible_public_pending(cloud_client):
    client, engine = cloud_client
    _set_policy(engine, mode='open')
    _register(client, username='Resend', email='resend@example.com')
    sender = client.app.state.email_sender
    with Session(engine) as session:
        token = session.scalar(select(EmailVerificationToken))
        token.created_at = utc_now().replace(year=utc_now().year - 1)
        session.commit()
    eligible = client.post('/api/v1/auth/email/verification/request', json={'email': 'RESEND@example.com'})
    unknown = client.post('/api/v1/auth/email/verification/request', json={'email': 'unknown@example.com'})
    assert eligible.status_code == unknown.status_code == 202
    assert eligible.json() == unknown.json() == {'code': 'verification_request_accepted'}
    assert len(sender.messages) == 2
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.username_normalized == 'resend'))
        user.status = 'blocked'
        session.commit()
    blocked = client.post('/api/v1/auth/email/verification/request', json={'email': 'resend@example.com'})
    assert blocked.status_code == 202 and blocked.json() == unknown.json() and len(sender.messages) == 2


def test_production_open_registration_fails_closed_without_smtp(migrated_database, tmp_path):
    _set_policy(migrated_database, mode='open')
    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='production', database_url=_database_url(),
        auth_secret=AUTH_SECRET, public_web_url='https://app.example.test'))
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        response = _register(client)
    assert response.status_code == 503 and response.json()['detail']['code'] == 'registration_unavailable'
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_concurrent_duplicate_registration_has_one_user(migrated_database):
    _set_policy(migrated_database, mode='open')
    barrier = threading.Barrier(2)

    def register() -> str:
        with Session(migrated_database) as session:
            barrier.wait(timeout=10)
            return RegistrationService(TokenService(AUTH_SECRET)).register(
                session, username='Race', email='race@example.com', password='x' * 15,
                email_delivery_available=True,
            ).code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(lambda _: register(), range(2))) == ['registration_request_accepted'] * 2
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


def test_concurrent_last_slot_activation_never_exceeds_limit(migrated_database):
    _set_policy(migrated_database, mode='open', max_users=10)
    for index in range(9):
        create_user(migrated_database, username=f'Active{index}', email=f'active{index}@example.test')
    raw_tokens = []
    for index in range(2):
        with Session(migrated_database) as session:
            result = RegistrationService(TokenService(AUTH_SECRET)).register(
                session, username=f'Candidate{index}', email=f'candidate{index}@example.com', password='x' * 15,
                email_delivery_available=True,
            )
            raw_tokens.append(result.verification_token)
    barrier = threading.Barrier(2)

    def verify(raw: str):
        with Session(migrated_database) as session:
            barrier.wait(timeout=10)
            return AccountEmailService(TokenService(AUTH_SECRET)).verify_email(session, raw)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(verify, raw_tokens))
    assert sum(result.account_status == 'active' for result in results) == 1
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(User).where(User.status == 'active')) == 10
        candidates = session.scalars(select(User).where(User.username_normalized.like('candidate%'))).all()
        assert sorted((user.status, user.email_verified) for user in candidates) == [('active', True), ('pending', True)]
