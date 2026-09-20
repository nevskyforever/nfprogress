from __future__ import annotations

import threading

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import admin_cli
from backend.app.cloud.models import AuthRefreshToken, AuthSession, RegistrationSettings, ReservedUsername, User
from backend.app.cloud.services import AdminService, RegistrationService
from backend.app.cloud.tokens import TokenService
from test_cloud_auth import AUTH_SECRET, cloud_client, create_user, login, migrated_database


def _admin(engine, username='Admin', email='admin@example.test'):
    user_id = create_user(engine, username=username, email=email)
    with Session(engine) as session:
        user = session.get(User, user_id)
        user.role = 'admin'
        user.email_verified = True
        session.commit()
    return user_id


def _headers(client, username='Admin'):
    return {'Authorization': f"Bearer {login(client, username).json()['access_token']}"}


def test_admin_authorization_list_and_safe_metadata(cloud_client):
    client, engine = cloud_client
    create_user(engine, username='Normal', email='normal@example.test')
    _admin(engine)
    assert client.get('/api/v1/admin/users').status_code == 401
    denied = client.get('/api/v1/admin/users', headers={'Authorization': f"Bearer {login(client, 'Normal').json()['access_token']}"})
    assert denied.status_code == 403 and denied.json()['detail']['code'] == 'admin_required'
    response = client.get('/api/v1/admin/users?limit=1&search=normal', headers=_headers(client))
    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 1 and payload['users'][0]['username'] == 'Normal'
    assert 'password_hash' not in payload['users'][0] and 'refresh_token' not in payload['users'][0]


def test_admin_lifecycle_capacity_revocation_and_protection(cloud_client):
    client, engine = cloud_client
    admin_id = _admin(engine)
    pending_id = create_user(engine, username='Pending', email='pending@example.test', status='pending')
    with Session(engine) as session:
        session.get(User, pending_id).email_verified = True
        settings = session.get(RegistrationSettings, 1)
        settings.max_users = 2
        session.commit()
    headers = _headers(client)
    approved = client.post(f'/api/v1/admin/users/{pending_id}/approve', headers=headers)
    assert approved.status_code == 200 and approved.json()['status'] == 'active'
    token = login(client, 'Pending').json()['access_token']
    blocked = client.post(f'/api/v1/admin/users/{pending_id}/block', headers=headers)
    assert blocked.status_code == 200 and blocked.json()['status'] == 'blocked'
    assert client.get('/api/v1/account/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401
    with Session(engine) as session:
        assert session.scalars(select(AuthSession).where(AuthSession.user_id == pending_id)).one().revoked_at is not None
        assert session.scalars(select(AuthRefreshToken).where(AuthRefreshToken.session_id.in_(
            select(AuthSession.id).where(AuthSession.user_id == pending_id),
        ))).one().revoked_at is not None
    assert client.post(f'/api/v1/admin/users/{admin_id}/block', headers=headers).json()['detail']['code'] == 'admin_account_protected'
    assert client.post(f'/api/v1/admin/users/{admin_id}/sessions/revoke', headers=headers).json()['detail']['code'] == 'admin_account_protected'


def test_admin_policy_limits_and_reservations(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine, username='Writer', email='writer@example.test')
    _admin(engine)
    headers = _headers(client)
    assert client.patch('/api/v1/admin/registration', json={'mode': 'approval', 'max_users': 0}, headers=headers).json()['max_users'] == 0
    assert client.patch('/api/v1/admin/limits', json={'max_cloud_projects': 0}, headers=headers).json() == {'max_cloud_projects': 0}
    assert client.patch(f'/api/v1/admin/users/{user_id}/limits', json={'max_cloud_projects_override': 7}, headers=headers).json()['effective_max_cloud_projects'] == 7
    assert client.patch(f'/api/v1/admin/users/{user_id}/limits', json={'max_cloud_projects_override': None}, headers=headers).json()['effective_max_cloud_projects'] == 0
    added = client.post('/api/v1/admin/reserved-usernames', json={'username': ' Example '}, headers=headers)
    assert added.status_code == 200 and added.json()['username_normalized'] == 'example'
    assert client.delete('/api/v1/admin/reserved-usernames?username=example', headers=headers).status_code == 200
    assert client.post('/api/v1/admin/reserved-usernames', json={'username': 'Writer'}, headers=headers).json()['detail']['code'] == 'username_in_use'


def test_registration_and_reservation_race_has_one_namespace_claim(migrated_database):
    """Real independent PostgreSQL sessions exercise C6/C7 advisory locking."""
    with Session(migrated_database) as session:
        settings = session.get(RegistrationSettings, 1)
        assert settings is not None
        settings.mode = 'open'
        settings.max_users = None
        session.commit()
    barrier = threading.Barrier(2)
    outcomes: dict[str, object] = {}

    def register() -> None:
        with Session(migrated_database) as session:
            barrier.wait()
            outcomes['registration'] = RegistrationService(TokenService(AUTH_SECRET)).register(
                session, username='RaceName', email='race@example.test', password='x' * 15,
                email_delivery_available=True,
            ).code

    def reserve() -> None:
        with Session(migrated_database) as session:
            barrier.wait()
            try:
                outcomes['reservation'] = AdminService().add_reserved_username(session, ' RaceName ')
            except Exception as error:  # expected username_in_use is inspected below
                outcomes['reservation'] = getattr(error, 'code', type(error).__name__)

    left = threading.Thread(target=register)
    right = threading.Thread(target=reserve)
    left.start(); right.start(); left.join(); right.join()
    with Session(migrated_database) as session:
        user = session.scalar(select(User).where(User.username_normalized == 'racename'))
        reservation = session.get(ReservedUsername, 'racename')
    assert (user is None) != (reservation is None)
    if user is not None:
        assert outcomes['registration'] == 'registration_request_accepted'
        assert outcomes['reservation'] == 'username_in_use'
    else:
        assert outcomes['registration'] == 'username_reserved'


def test_admin_cli_create_promote_restore_and_no_password_argv(migrated_database, monkeypatch, capsys):
    monkeypatch.setenv(
        'NFPROGRESS_DATABASE_URL',
        migrated_database.url.render_as_string(hide_password=False),
    )
    values = iter(['admin', 'admin-cli@example.test'])
    passwords = iter(['x' * 15, 'x' * 15])
    monkeypatch.setattr('builtins.input', lambda _prompt: next(values))
    monkeypatch.setattr('getpass.getpass', lambda _prompt: next(passwords))
    assert admin_cli.main(['create']) == 0
    with Session(migrated_database) as session:
        created = session.scalar(select(User).where(User.username_normalized == 'admin'))
        assert created is not None and created.role == 'admin' and created.status == 'active' and created.email_verified
        original_hash = created.password_hash
    assert 'x' * 15 not in capsys.readouterr().out
    normal_id = create_user(migrated_database, username='Promote', email='promote@example.test', status='blocked')
    with Session(migrated_database) as session:
        normal = session.get(User, normal_id); password_hash = normal.password_hash; verified = normal.email_verified
    assert admin_cli.main(['promote', 'Promote']) == 0
    assert admin_cli.main(['promote', 'Promote']) == 0
    assert admin_cli.main(['restore', 'Promote']) == 0
    with Session(migrated_database) as session:
        promoted = session.get(User, normal_id)
        assert promoted.role == 'admin' and promoted.status == 'active'
        assert promoted.password_hash == password_hash and promoted.email_verified == verified
        assert session.scalar(select(User).where(User.username_normalized == 'admin')).password_hash == original_hash
    with pytest.raises(SystemExit):
        admin_cli._parser().parse_args(['create', '--password', 'secret'])
