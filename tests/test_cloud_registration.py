from __future__ import annotations

import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.cloud.models import (AuthRefreshToken, AuthSession,
                                      EmailVerificationToken,
                                      RegistrationSettings, User)
from backend.app.cloud.passwords import PasswordService
from backend.app.cloud.services import (AccountEmailService,
                                        RegistrationService,
                                        RegistrationUnavailableError)
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


def test_registration_policy_gate_avoids_hash_only_when_publicly_unavailable(migrated_database):
    passwords = Mock(spec=PasswordService)
    passwords.hash.return_value = 'test-password-hash'
    tokens = Mock(spec=TokenService)
    tokens.issue_email_verification_token.side_effect = lambda: (
        uuid.uuid4(), 'ev1.test-token.secret', 'a' * 64,
    )
    service = RegistrationService(tokens, passwords=passwords)

    with Session(migrated_database) as session:
        assert service.register(session, username='Closed', email='closed@example.com', password='x' * 15,
                                email_delivery_available=True).code == 'registration_closed'
    assert passwords.hash.call_count == 0
    assert tokens.issue_email_verification_token.call_count == 0

    _set_policy(migrated_database, mode='open')
    with Session(migrated_database) as session, pytest.raises(RegistrationUnavailableError):
        service.register(session, username='Unavailable', email='unavailable@example.com', password='x' * 15,
                         email_delivery_available=False)
    assert passwords.hash.call_count == 0
    assert tokens.issue_email_verification_token.call_count == 0

    with Session(migrated_database) as session:
        assert service.register(session, username='Open', email='open@example.com', password='x' * 15,
                                email_delivery_available=True).code == 'registration_request_accepted'
    with Session(migrated_database) as session:
        assert service.register(session, username=' OPEN ', email='other@example.com', password='x' * 15,
                                email_delivery_available=True).code == 'registration_request_accepted'
    assert passwords.hash.call_count == 2
    assert tokens.issue_email_verification_token.call_count == 2
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(EmailVerificationToken)) == 1


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
        assert session.scalar(select(func.count()).select_from(AuthSession)) == 0
        assert session.scalar(select(func.count()).select_from(AuthRefreshToken)) == 0
    assert login(client, 'NewWriter', 'пароль с Unicode достаточно длинный').status_code == 401
    verified = client.post('/api/v1/auth/email/verify', json={'token': _token(sender)})
    assert verified.json() == {'code': 'email_verified', 'account_status': 'active', 'activation': 'active'}
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(AuthSession)) == 0
        assert session.scalar(select(func.count()).select_from(AuthRefreshToken)) == 0
    assert login(client, 'NewWriter', 'пароль с Unicode достаточно длинный').status_code == 200
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(AuthSession)) == 1
        assert session.scalar(select(func.count()).select_from(AuthRefreshToken)) == 1


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


def test_unlimited_capacity_and_only_active_users_count_toward_limit(cloud_client):
    client, engine = cloud_client
    _set_policy(engine, mode='open', max_users=None)
    for status in ('active', 'pending', 'rejected', 'blocked'):
        create_user(engine, username=f'Existing{status}', email=f'existing-{status}@example.test', status=status)
    _register(client, username='Unlimited', email='unlimited@example.com')
    assert client.post('/api/v1/auth/email/verify', json={'token': _token(client.app.state.email_sender)}).json()['activation'] == 'active'

    _set_policy(engine, mode='open', max_users=3)
    _register(client, username='SecondActive', email='second-active@example.com')
    assert client.post('/api/v1/auth/email/verify', json={'token': _token(client.app.state.email_sender)}).json()['activation'] == 'active'
    _register(client, username='OverCapacity', email='over-capacity@example.com')
    result = client.post('/api/v1/auth/email/verify', json={'token': _token(client.app.state.email_sender)})
    assert result.json()['activation'] == 'capacity_reached'


def test_lowering_capacity_preserves_existing_active_users_and_blocks_next_activation(cloud_client):
    client, engine = cloud_client
    _set_policy(engine, mode='open', max_users=None)
    for index in range(5):
        create_user(engine, username=f'Kept{index}', email=f'kept-{index}@example.test')
    _set_policy(engine, mode='open', max_users=2)
    _register(client, username='AfterLowering', email='after-lowering@example.com')
    result = client.post('/api/v1/auth/email/verify', json={'token': _token(client.app.state.email_sender)})
    assert result.json()['activation'] == 'capacity_reached'
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User).where(User.status == 'active')) == 5
    assert login(client, 'Kept0').status_code == 200


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


def test_public_resend_inherits_c3_throttle_with_controlled_clock(migrated_database):
    _set_policy(migrated_database, mode='open')
    with Session(migrated_database) as session:
        registered = RegistrationService(TokenService(AUTH_SECRET)).register(
            session, username='ThrottlePublic', email='throttle-public@example.com', password='x' * 15,
            email_delivery_available=True,
        )
        assert registered.verification_token
    clock = [utc_now()]
    with Session(migrated_database) as session:
        initial = session.scalar(select(EmailVerificationToken))
        initial.created_at = clock[0] - timedelta(hours=2)
        session.commit()
    service = AccountEmailService(TokenService(AUTH_SECRET), now_provider=lambda: clock[0])

    def issue():
        with Session(migrated_database) as session:
            return service.issue_verification_for_public_email(session, 'throttle-public@example.com')

    assert issue() is not None
    assert issue() is None
    for _ in range(4):
        clock[0] += timedelta(seconds=61)
        assert issue() is not None
    clock[0] += timedelta(seconds=61)
    assert issue() is None
    clock[0] += timedelta(hours=1)
    assert issue() is not None


def test_concurrent_public_resend_keeps_one_usable_verification_token(migrated_database):
    _set_policy(migrated_database, mode='open')
    with Session(migrated_database) as session:
        assert RegistrationService(TokenService(AUTH_SECRET)).register(
            session, username='PublicResendRace', email='public-resend-race@example.com', password='x' * 15,
            email_delivery_available=True,
        ).verification_token
    with Session(migrated_database) as session:
        initial = session.scalar(select(EmailVerificationToken))
        initial.created_at = utc_now() - timedelta(hours=2)
        session.commit()
    barrier = threading.Barrier(2)

    def issue():
        with Session(migrated_database) as session:
            barrier.wait(timeout=10)
            return AccountEmailService(TokenService(AUTH_SECRET)).issue_verification_for_public_email(
                session, 'public-resend-race@example.com',
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        issued = list(executor.map(lambda _: issue(), range(2)))
    assert sum(item is not None for item in issued) == 1
    with Session(migrated_database) as session:
        assert session.scalar(select(func.count()).select_from(EmailVerificationToken).where(
            EmailVerificationToken.revoked_at.is_(None), EmailVerificationToken.used_at.is_(None),
        )) == 1


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
