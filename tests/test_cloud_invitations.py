from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.cloud.email import NullEmailSender
from backend.app.cloud.models import AdminInvitation, RegistrationSettings, User
from backend.app.cloud.tokens import utc_now
from test_cloud_auth import cloud_client, create_user, login, migrated_database


def _admin(client, engine) -> dict[str, str]:
    admin_id = create_user(engine, username='PrivateAdmin', email='admin@example.test')
    with Session(engine) as session:
        user = session.get(User, admin_id)
        user.role = 'admin'
        user.email_verified = True
        session.commit()
    return {'Authorization': f"Bearer {login(client, 'PrivateAdmin').json()['access_token']}"}


def _issued_token(client) -> str:
    message = client.app.state.email_sender.messages[-1]
    return message.body.split('#token=', 1)[1].split()[0]


def test_private_invitation_authorization_creation_acceptance_and_replay(cloud_client):
    client, engine = cloud_client
    normal_id = create_user(engine, username='Normal', email='normal@example.test')
    normal_headers = {'Authorization': f"Bearer {login(client, 'Normal').json()['access_token']}"}
    payload = {'username': 'PrivateWriter', 'email': 'writer@example.com'}
    assert client.post('/api/v1/admin/invitations', json=payload).status_code == 401
    assert client.post('/api/v1/admin/invitations', json=payload, headers=normal_headers).status_code == 403
    headers = _admin(client, engine)
    assert client.get('/api/v1/auth/registration').json()['mode'] == 'closed'
    assert client.patch('/api/v1/admin/registration', json={'mode': 'open'}, headers=headers).status_code == 409
    issued = client.post('/api/v1/admin/invitations', json=payload, headers=headers)
    assert issued.status_code == 201, issued.json()
    assert issued.json()['status'] == 'pending'
    assert 'token' not in issued.text and 'password' not in issued.text
    assert client.app.state.email_sender.messages[-1].recipient == payload['email']
    token = _issued_token(client)
    assert client.post('/api/v1/auth/invitations/accept', json={
        'token': token[:-1] + ('A' if token[-1] != 'A' else 'B'),
        'password': 'new private password long',
    }).status_code == 400
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.username_normalized == 'privatewriter'))
        row = session.scalar(select(AdminInvitation).where(AdminInvitation.user_id == user.id))
        assert user.status == 'pending' and not user.email_verified
        assert token not in row.token_hash and len(row.token_hash) == 64
    assert client.post('/api/v1/auth/login', json={
        'username': 'PrivateWriter', 'password': 'new private password long',
    }).status_code == 401
    assert client.post('/api/v1/auth/invitations/accept', json={
        'token': token, 'password': 'short',
    }).status_code == 422
    accepted = client.post('/api/v1/auth/invitations/accept', json={
        'token': token, 'password': 'new private password long',
    })
    assert accepted.status_code == 200 and accepted.json()['code'] == 'invitation_accepted'
    assert client.post('/api/v1/auth/invitations/accept', json={
        'token': token, 'password': 'new private password long',
    }).json()['detail']['code'] == 'invalid_or_expired_invitation'
    assert login(client, 'PrivateWriter', 'new private password long').status_code == 200
    listed = client.get('/api/v1/admin/invitations', headers=headers).json()
    assert listed[0]['status'] == 'accepted' and token not in str(listed)
    assert client.post('/api/v1/auth/register', json={
        'username': 'Public', 'email': 'public@example.com', 'password': 'public password long',
    }).status_code == 403


def test_private_invitation_revoke_expiry_reissue_and_capacity(cloud_client):
    client, engine = cloud_client
    headers = _admin(client, engine)
    payload = {'username': 'ReissueWriter', 'email': 'reissue@example.com'}
    first_response = client.post('/api/v1/admin/invitations', json=payload, headers=headers)
    assert first_response.status_code == 201, first_response.json()
    first = first_response.json()
    first_token = _issued_token(client)
    assert client.post('/api/v1/admin/invitations', json=payload, headers=headers).json()['detail']['code'] == 'invitation_pending'
    assert client.post(f"/api/v1/admin/invitations/{first['id']}/revoke", headers=headers).json()['status'] == 'revoked'
    assert client.post('/api/v1/auth/invitations/accept', json={
        'token': first_token, 'password': 'new private password long',
    }).status_code == 400
    second = client.post('/api/v1/admin/invitations', json=payload, headers=headers).json()
    second_token = _issued_token(client)
    with Session(engine) as session:
        session.get(AdminInvitation, second['id']).expires_at = utc_now() - timedelta(seconds=1)
        session.commit()
    assert any(row['id'] == second['id'] and row['status'] == 'expired'
               for row in client.get('/api/v1/admin/invitations', headers=headers).json())
    assert client.post('/api/v1/auth/invitations/accept', json={
        'token': second_token, 'password': 'new private password long',
    }).status_code == 400
    third = client.post('/api/v1/admin/invitations', json=payload, headers=headers).json()
    third_token = _issued_token(client)
    with Session(engine) as session:
        session.get(RegistrationSettings, 1).max_users = 1  # The administrator already uses the slot.
        session.commit()
    blocked = client.post('/api/v1/auth/invitations/accept', json={
        'token': third_token, 'password': 'new private password long',
    })
    assert blocked.status_code == 409 and blocked.json()['detail']['code'] == 'capacity_reached'
    with Session(engine) as session:
        assert session.get(AdminInvitation, third['id']).used_at is None
        session.get(RegistrationSettings, 1).max_users = 2
        session.commit()
    assert client.post('/api/v1/auth/invitations/accept', json={
        'token': third_token, 'password': 'new private password long',
    }).status_code == 200


def test_invitation_requires_email_delivery_without_creating_an_account(cloud_client):
    client, engine = cloud_client
    headers = _admin(client, engine)
    client.app.state.email_sender = NullEmailSender()
    response = client.post('/api/v1/admin/invitations', headers=headers,
        json={'username': 'NoDelivery', 'email': 'no-delivery@example.com'})
    assert response.status_code == 503
    with Session(engine) as session:
        assert session.scalar(select(User).where(User.username_normalized == 'nodelivery')) is None


def test_populated_invitation_history_blocks_downgrade(cloud_client, monkeypatch):
    client, engine = cloud_client
    headers = _admin(client, engine)
    assert client.post('/api/v1/admin/invitations', headers=headers,
        json={'username': 'KeptWriter', 'email': 'kept@example.com'}).status_code == 201
    monkeypatch.setenv('NFPROGRESS_DATABASE_URL', engine.url.render_as_string(hide_password=False))
    config = AlembicConfig(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    with pytest.raises(RuntimeError, match='invitation history'):
        command.downgrade(config, 'c18_compression_readers')
    with Session(engine) as session:
        assert session.scalar(select(AdminInvitation.id)) is not None
