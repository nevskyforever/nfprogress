from __future__ import annotations

from datetime import timedelta
from fastapi.testclient import TestClient
import pytest
import uuid
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.cloud.email import RecordingEmailSender
from backend.app.cloud.models import (AuthRefreshToken, AuthSession,
                                      EmailVerificationToken, GlobalLimits,
                                      RegistrationSettings, ReservedUsername,
                                      PasswordResetToken, User, UserLimitOverrides)
from backend.app.cloud.repositories import ReservedUsernameRepository
from backend.app.cloud.services import AccountService, AuthenticationService
from backend.app.cloud.tokens import TokenService, utc_now
from backend.app.config import RuntimeConfig
from backend.app.main import create_app
from test_cloud_auth import (AUTH_SECRET, ROOT, _database_url, cloud_client,
                             create_user, login, migrated_database)


INITIAL_RESERVED_USERNAMES = {
    'admin', 'administrator', 'root', 'system', 'support', 'security', 'staff',
    'moderator', 'official', 'api', 'www', 'nfprogress', 'wow', 'worta',
}


def _set_policy(engine, *, mode: str, max_users: int | None = None) -> None:
    with Session(engine) as session:
        settings = session.get(RegistrationSettings, 1)
        assert settings is not None
        settings.mode, settings.max_users = mode, max_users
        session.commit()


def _register(client, *, username: str, email: str) -> object:
    return client.post('/api/v1/auth/register', json={
        'username': username, 'email': email, 'password': 'valid sufficiently long password',
    })


def test_c6_seed_normalization_exact_matching_and_primary_key(migrated_database):
    repository = ReservedUsernameRepository()
    with Session(migrated_database) as session:
        assert set(session.scalars(select(ReservedUsername.username_normalized))) == INITIAL_RESERVED_USERNAMES
        for username in ('admin', 'ADMIN', 'Admin', ' admin ', 'worta', 'WORTA', 'Worta', ' WORTA '):
            assert repository.is_reserved(session, username)
        for username in ('admin2', 'myadmin', 'administrator2', 'worta-user', 'wowwriter'):
            assert not repository.is_reserved(session, username)
        session.add(ReservedUsername(username_normalized='admin'))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.parametrize('username', ('admin', 'ADMIN', ' Admin ', 'WORTA', 'WOW', 'NFProgress'))
def test_open_registration_rejects_reserved_username_without_side_effects(cloud_client, username):
    client, engine = cloud_client
    _set_policy(engine, mode='open')
    response = _register(client, username=username, email='new@example.test')
    assert response.status_code == 409
    assert response.json() == {'detail': {'code': 'username_reserved', 'message': 'This username is reserved.'}}
    assert client.app.state.email_sender.messages == []
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
        assert session.scalar(select(func.count()).select_from(EmailVerificationToken)) == 0
        assert session.scalar(select(func.count()).select_from(AuthSession)) == 0
        assert session.scalar(select(func.count()).select_from(AuthRefreshToken)) == 0


def test_reserved_username_does_not_bypass_password_validation(cloud_client):
    client, engine = cloud_client
    _set_policy(engine, mode='open')
    response = client.post('/api/v1/auth/register', json={
        'username': 'admin', 'email': 'new@example.test', 'password': 'too short',
    })
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'invalid_password'


def test_reserved_registration_preserves_closed_approval_open_and_capacity_contracts(cloud_client):
    client, engine = cloud_client
    assert _register(client, username='admin', email='closed@example.test').status_code == 403

    _set_policy(engine, mode='approval')
    assert _register(client, username='admin', email='reserved-approval@example.test').status_code == 409
    assert _register(client, username='WriterAlice', email='writer@example.test').status_code == 202
    with Session(engine) as session:
        writer = session.scalar(select(User).where(User.username_normalized == 'writeralice'))
        assert writer is not None and writer.status == 'pending' and writer.registration_mode_at_signup == 'approval'
        assert session.scalar(select(func.count()).select_from(EmailVerificationToken)) == 1

    _set_policy(engine, mode='open', max_users=1)
    assert _register(client, username='worta', email='reserved-open@example.test').status_code == 409
    assert _register(client, username='OpenWriter', email='open@example.test').status_code == 202
    raw = client.app.state.email_sender.messages[-1].body.split('token=', 1)[1].split()[0]
    verified = client.post('/api/v1/auth/email/verify', json={'token': raw})
    assert verified.json()['activation'] == 'active'
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User).where(User.status == 'active')) == 1
        assert session.get(GlobalLimits, 1).max_cloud_projects == 20


def test_c6_upgrade_downgrade_and_existing_reserved_name_user_are_non_retroactive(migrated_database, monkeypatch, tmp_path):
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', _database_url())
    config = AlembicConfig(str(ROOT / 'alembic.ini'))
    command.downgrade(config, 'base')
    for revision in (
            'c1_postgresql_foundation', 'c2_account_auth_core',
            'c3_email_account_recovery', 'c4_registration_controls',
            'c5_limits_framework'):
        command.upgrade(config, revision)
    user_id = create_user(migrated_database, username='Admin', email='admin@example.test')
    with Session(migrated_database) as session:
        AuthenticationService(TokenService(AUTH_SECRET)).login(
            session, username='Admin', password='correct horse battery staple',
        )
    now = utc_now()
    with Session(migrated_database) as session:
        session.add_all([
            EmailVerificationToken(
                id=uuid.uuid4(), user_id=user_id, token_hash='a' * 64,
                email_normalized='admin@example.test', expires_at=now + timedelta(hours=1),
            ),
            PasswordResetToken(
                id=uuid.uuid4(), user_id=user_id, token_hash='b' * 64,
                expires_at=now + timedelta(hours=1),
            ),
            UserLimitOverrides(user_id=user_id, max_cloud_projects_override=9),
        ])
        session.commit()
    with migrated_database.begin() as connection:
        connection.execute(text("UPDATE registration_settings SET mode = 'open', max_users = 7 WHERE id = 1"))

    command.upgrade(config, 'c6_reserved_usernames')
    with Session(migrated_database) as session:
        user = session.get(User, user_id)
        assert user is not None and user.username == 'Admin' and user.username_normalized == 'admin'
        assert user.status == 'active'
        assert session.get(ReservedUsername, 'admin') is not None
        assert session.get(GlobalLimits, 1).max_cloud_projects == 20
        assert session.get(UserLimitOverrides, user_id).max_cloud_projects_override == 9
        assert session.scalar(select(func.count()).select_from(AuthSession)) == 1
        assert session.scalar(select(func.count()).select_from(AuthRefreshToken)) == 1
        assert session.scalar(select(func.count()).select_from(EmailVerificationToken)) == 1
        assert session.scalar(select(func.count()).select_from(PasswordResetToken)) == 1

    app = create_app(RuntimeConfig(data_dir=tmp_path, environment='test', database_url=_database_url(),
        auth_secret=AUTH_SECRET, public_web_url='https://app.example.test'))
    app.state.email_sender = RecordingEmailSender()
    with TestClient(app) as client:
        assert login(client, 'ADMIN').status_code == 200
        response = _register(client, username='ADMIN', email='new-admin@example.test')
        assert response.status_code == 409 and response.json()['detail']['code'] == 'username_reserved'
        assert app.state.email_sender.messages == []

    command.downgrade(config, 'c5_limits_framework')
    assert 'reserved_usernames' not in inspect(migrated_database).get_table_names()
    with Session(migrated_database) as session:
        assert session.get(User, user_id) is not None
        assert session.execute(text('SELECT mode, max_users FROM registration_settings')).one() == ('open', 7)
        assert session.get(GlobalLimits, 1).max_cloud_projects == 20
    command.upgrade(config, 'c6_reserved_usernames')
    with Session(migrated_database) as session:
        assert set(session.scalars(select(ReservedUsername.username_normalized))) == INITIAL_RESERVED_USERNAMES
