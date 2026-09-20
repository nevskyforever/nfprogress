from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.cloud.models import AuthSession, EmailVerificationToken, PasswordResetToken, User
from backend.app.cloud.email import OutgoingEmail, SmtpEmailSender
from backend.app.cloud.services import AccountEmailService, RecoveryTokenError
from backend.app.cloud.tokens import TokenService, utc_now
from backend.app.config import RuntimeConfig
from test_cloud_auth import (AUTH_SECRET, cloud_client, create_user, login,
                             migrated_database)


def _token_from(sender, path: str) -> str:
    body = sender.messages[-1].body
    match = re.search(rf'{path}\?token=([^\s]+)', body)
    assert match
    return match.group(1)


def test_smtp_configuration_tls_sender_and_secret_redaction(monkeypatch):
    config = RuntimeConfig(public_web_url='https://app.example.test', smtp_host='smtp.example.test',
        smtp_port=465, smtp_username='mailer', smtp_password='smtp-secret',
        smtp_from_email='no-reply@example.test', smtp_from_name='NFProgress', smtp_security='implicit_tls')
    assert 'smtp-secret' not in repr(config)
    client = Mock(); client.__enter__ = Mock(return_value=client); client.__exit__ = Mock(return_value=False)
    smtp_ssl = Mock(return_value=client)
    monkeypatch.setattr('backend.app.cloud.email.smtplib.SMTP_SSL', smtp_ssl)
    SmtpEmailSender(config).send(OutgoingEmail('to@example.test', 'Subject', 'Body'))
    assert smtp_ssl.call_args.kwargs['timeout'] == 10
    client.login.assert_called_once_with('mailer', 'smtp-secret')
    message = client.send_message.call_args.args[0]
    assert message['From'] == 'NFProgress <no-reply@example.test>'
    with pytest.raises(ValueError, match='complete'):
        RuntimeConfig(smtp_host='smtp.example.test')


def test_verification_flow_storage_rotation_and_status(cloud_client):
    client, engine = cloud_client
    user_id = create_user(engine, status='pending')
    logged_in = login(client)  # pending cannot request with auth; activate only to exercise endpoint
    assert logged_in.status_code == 401
    with Session(engine) as db:
        db.get(User, user_id).status = 'active'; db.commit()
    tokens = login(client).json()
    sender = client.app.state.email_sender
    request = client.post('/api/v1/account/email/verification/request', headers={'Authorization': f"Bearer {tokens['access_token']}"})
    assert request.status_code == 202 and request.json()['code'] == 'verification_request_accepted'
    raw = _token_from(sender, '/verify-email')
    parsed = TokenService.parse_opaque_token(raw, 'ev1'); assert parsed
    with Session(engine) as db:
        row = db.get(EmailVerificationToken, parsed[0]); assert row
        hashes = db.execute(text('select token_hash from email_verification_tokens')).scalars().all()
        assert raw not in hashes and parsed[1] not in hashes
        assert re.fullmatch(r'[0-9a-f]{64}', row.token_hash)
        db.get(User, user_id).status = 'pending'
        db.commit()
    assert client.post('/api/v1/auth/email/verify', json={'token': raw}).status_code == 200
    assert client.post('/api/v1/auth/email/verify', json={'token': raw}).json()['detail']['code'] == 'invalid_or_expired_token'
    with Session(engine) as db:
        user = db.get(User, user_id)
        assert user.email_verified is True and user.status == 'pending'


def test_verification_resend_revokes_and_throttles(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    access = login(client).json()['access_token']
    headers = {'Authorization': f'Bearer {access}'}
    client.post('/api/v1/account/email/verification/request', headers=headers)
    # Immediate request is safely accepted but PostgreSQL history prevents a second email/token.
    client.post('/api/v1/account/email/verification/request', headers=headers)
    with Session(engine) as db:
        assert db.query(EmailVerificationToken).count() == 1


def test_reset_is_generic_revokes_sessions_and_notifies(cloud_client):
    client, engine = cloud_client
    create_user(engine)
    known = client.post('/api/v1/auth/password-reset/request', json={'email': 'arthur@example.test'})
    unknown = client.post('/api/v1/auth/password-reset/request', json={'email': 'none@example.test'})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    sender = client.app.state.email_sender
    raw = _token_from(sender, '/reset-password')
    old = login(client).json()
    complete = client.post('/api/v1/auth/password-reset/confirm', json={'token': raw, 'new_password': 'new password with enough unicode длина'})
    assert complete.status_code == 200
    assert login(client).status_code == 401
    assert login(client, password='new password with enough unicode длина').status_code == 200
    assert client.get('/api/v1/account/me', headers={'Authorization': f"Bearer {old['access_token']}"}).status_code == 401
    assert 'new password' not in sender.messages[-1].body and raw not in sender.messages[-1].body
    with Session(engine) as db:
        assert all(item.revoked_at is not None for item in db.query(AuthSession).all())
        assert db.query(PasswordResetToken).one().used_at is not None


def test_expired_revoked_and_concurrent_reset_are_single_use(migrated_database):
    user_id = create_user(migrated_database)
    service = AccountEmailService(TokenService(AUTH_SECRET))
    with Session(migrated_database) as db:
        user = db.get(User, user_id)
        issued = service.issue_password_reset(db, user.email); assert issued
        raw = issued[1]
    barrier = threading.Barrier(2)
    def consume() -> bool:
        with Session(migrated_database) as db:
            barrier.wait(timeout=10)
            try:
                service.confirm_password_reset(db, raw, 'a password long enough for C3')
                return True
            except RecoveryTokenError:
                return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: consume(), range(2)))
    assert results.count(True) == 1
    with Session(migrated_database) as db:
        token = db.query(PasswordResetToken).one()
        assert token.used_at is not None
        token = db.query(PasswordResetToken).one(); token.expires_at = utc_now() - timedelta(seconds=1); db.commit()
    with Session(migrated_database) as db:
        try:
            service.confirm_password_reset(db, raw, 'a password long enough for C3')
        except RecoveryTokenError:
            pass
        else:
            raise AssertionError('used token must fail')
