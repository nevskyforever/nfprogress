"""Private administrator invitations over the existing account authority."""
from __future__ import annotations

import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import AdminInvitation, RegistrationSettings, User
from .legal_documents import (DocumentConfirmation, LegalAcceptanceService,
                              LegalDocumentError, LegalDocumentRegistry,
                              LegalDocumentVersion)
from .passwords import PasswordService
from .repositories import (RegistrationSettingsRepository, ReservedUsernameRepository,
                           UserRepository, lock_username_namespace, normalize_email,
                           normalize_username)
from .tokens import ADMIN_INVITATION_LIFETIME, TokenService, utc_now


class InvitationError(Exception):
    def __init__(self, code: str, status_code: int = 400) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def invitation_status(row: AdminInvitation, now: datetime) -> str:
    if row.used_at is not None:
        return 'accepted'
    if row.revoked_at is not None:
        return 'revoked'
    if row.expires_at <= now:
        return 'expired'
    return 'pending'


class PrivateInvitationService:
    def __init__(self, tokens: TokenService, passwords: PasswordService | None = None,
                 now_provider=utc_now, legal_registry: LegalDocumentRegistry | None = None) -> None:
        self._tokens = tokens
        self._passwords = passwords or PasswordService()
        self._now = now_provider
        self._legal = LegalAcceptanceService(legal_registry) if legal_registry else LegalAcceptanceService()

    @staticmethod
    def _closed_settings(session: Session) -> RegistrationSettings:
        settings = RegistrationSettingsRepository().get(session, lock=True)
        if settings is None or settings.mode != 'closed':
            raise InvitationError('private_registration_required', 409)
        return settings

    def issue(self, session: Session, *, admin_id: UUID, username: str,
              email: str) -> tuple[AdminInvitation, str]:
        now = self._now()
        token_id, raw, token_hash = self._tokens.issue_admin_invitation_token()
        # A pending account is never usable with this random, undisclosed password.
        unusable_hash = self._passwords.hash(secrets.token_urlsafe(48))
        normalized_name, normalized_email = normalize_username(username), normalize_email(email)
        session.commit()
        try:
            with session.begin():
                self._closed_settings(session)
                lock_username_namespace(session, normalized_name)
                if ReservedUsernameRepository().is_reserved(session, normalized_name):
                    raise InvitationError('username_reserved', 409)
                user = session.scalar(select(User).where(
                    User.username_normalized == normalized_name).with_for_update())
                if user is None:
                    user = UserRepository().create(session, username=username, email=email,
                        password_hash=unusable_hash, role='user', status='pending')
                    session.flush()
                elif (user.role != 'user' or user.status != 'pending'
                      or user.registration_mode_at_signup is not None
                      or user.email_normalized != normalized_email
                      or not session.scalar(select(AdminInvitation.id).where(
                          AdminInvitation.user_id == user.id).limit(1))):
                    raise InvitationError('account_conflict', 409)
                active = session.scalar(select(AdminInvitation.id).where(
                    AdminInvitation.user_id == user.id, AdminInvitation.used_at.is_(None),
                    AdminInvitation.revoked_at.is_(None), AdminInvitation.expires_at > now).limit(1))
                if active is not None:
                    raise InvitationError('invitation_pending', 409)
                row = AdminInvitation(id=token_id, user_id=user.id, created_by_id=admin_id,
                    token_hash=token_hash, created_at=now,
                    expires_at=now + ADMIN_INVITATION_LIFETIME)
                session.add(row)
            return row, raw
        except IntegrityError:
            session.rollback()
            raise InvitationError('account_conflict', 409) from None
        except InvitationError:
            session.rollback()
            raise

    def list(self, session: Session, *, limit: int = 100) -> list[tuple[AdminInvitation, User]]:
        return list(session.execute(select(AdminInvitation, User).join(
            User, User.id == AdminInvitation.user_id).order_by(
                AdminInvitation.created_at.desc(), AdminInvitation.id.desc()).limit(limit)))

    def revoke(self, session: Session, invitation_id: UUID) -> AdminInvitation:
        session.commit()
        try:
            with session.begin():
                row = session.scalar(select(AdminInvitation).where(
                    AdminInvitation.id == invitation_id).with_for_update())
                if row is None:
                    raise InvitationError('invitation_not_found', 404)
                if row.used_at is not None:
                    raise InvitationError('invitation_already_used', 409)
                if row.revoked_at is None:
                    row.revoked_at = self._now()
                return row
        except InvitationError:
            session.rollback()
            raise

    def inspect(self, session: Session, *, raw_token: str) -> None:
        parsed = self._tokens.parse_opaque_token(raw_token, 'iv1')
        if parsed is None:
            raise InvitationError('invalid_or_expired_invitation')
        token_id, secret = parsed
        now = self._now()
        row = session.get(AdminInvitation, token_id)
        if (row is None or invitation_status(row, now) != 'pending'
                or not self._tokens.verify_refresh_secret(secret, row.token_hash)):
            raise InvitationError('invalid_or_expired_invitation')

    def documents(self, language: str) -> tuple[LegalDocumentVersion, ...]:
        documents = self._legal.registry.current(language)
        if not any(item.mandatory for item in documents):
            raise LegalDocumentError('legal_documents_unavailable', 503)
        return documents

    def accept(self, session: Session, *, raw_token: str, password: str,
               language: str, documents: list[DocumentConfirmation]) -> User:
        self.inspect(session, raw_token=raw_token)
        parsed = self._tokens.parse_opaque_token(raw_token, 'iv1')
        assert parsed is not None
        token_id, secret = parsed
        self._legal.registry.verify(documents, language)
        self._passwords.validate_new_password(password)
        password_hash = self._passwords.hash(password)
        session.commit()
        try:
            with session.begin():
                now = self._now()
                settings = self._closed_settings(session)
                row = session.scalar(select(AdminInvitation).where(
                    AdminInvitation.id == token_id).with_for_update())
                if (row is None or invitation_status(row, now) != 'pending'
                        or not self._tokens.verify_refresh_secret(secret, row.token_hash)):
                    raise InvitationError('invalid_or_expired_invitation')
                user = session.scalar(select(User).where(User.id == row.user_id).with_for_update())
                if (user is None or user.role != 'user' or user.status != 'pending'
                        or user.registration_mode_at_signup is not None):
                    raise InvitationError('invalid_or_expired_invitation')
                active_count = session.scalar(select(func.count()).select_from(User).where(
                    User.status == 'active')) or 0
                if settings.max_users is not None and active_count >= settings.max_users:
                    raise InvitationError('capacity_reached', 409)
                self._legal.record(
                    session, user_id=user.id, confirmations=documents,
                    preferred_language=language, method='invitation',
                )
                user.password_hash = password_hash
                user.email_verified = True  # The private link was delivered to this email by the server.
                user.status = 'active'
                row.used_at = now
                return user
        except (InvitationError, LegalDocumentError):
            session.rollback()
            raise
