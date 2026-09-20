from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (AuthRefreshToken, AuthSession, EmailVerificationToken,
                     PasswordResetToken, RegistrationSettings, User)
from .passwords import PasswordService
from .repositories import (AuthRepository, RegistrationSettingsRepository,
                           UserRepository, normalize_email)
from .tokens import (ACCESS_TOKEN_LIFETIME, EMAIL_VERIFICATION_TOKEN_LIFETIME,
                     PASSWORD_RESET_TOKEN_LIFETIME, SESSION_LIFETIME,
                     TokenService, utc_now)


_DEFAULT_PASSWORDS = PasswordService()


class AuthenticationError(Exception):
    """A deliberately generic public authentication failure."""


class RecoveryTokenError(Exception):
    """A deliberately generic token failure."""


class RegistrationUnavailableError(Exception):
    """Public registration cannot safely create a verifiable account."""


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    code: str
    email: str | None = None
    verification_token: str | None = None


@dataclass(frozen=True, slots=True)
class EmailVerificationResult:
    account_status: str
    activation: str


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    access_expires_in: int = int(ACCESS_TOKEN_LIFETIME.total_seconds())


class AccountService:
    """Creation primitive for C3 registration; C2 exposes no registration route."""

    def __init__(self, passwords: PasswordService | None = None) -> None:
        self._passwords = passwords or _DEFAULT_PASSWORDS
        self._users = UserRepository()

    def create_user(self, session: Session, *, username: str, email: str, password: str,
                    role: str = 'user', status: str = 'pending') -> User:
        return self._users.create(session, username=username, email=email,
                                  password_hash=self._passwords.hash(password),
                                  role=role, status=status)


class RegistrationService:
    """C4 public sign-up policy; delivery happens after its committed transaction."""

    def __init__(self, tokens: TokenService, passwords: PasswordService | None = None,
                 now_provider=utc_now) -> None:
        self._tokens = tokens
        self._passwords = passwords or _DEFAULT_PASSWORDS
        self._now = now_provider
        self._users = UserRepository()
        self._settings = RegistrationSettingsRepository()

    def public_policy(self, session: Session) -> RegistrationSettings:
        settings = self._settings.get(session)
        if settings is None:
            raise RuntimeError('Registration settings are unavailable.')
        return settings

    def register(self, session: Session, *, username: str, email: str, password: str,
                 email_delivery_available: bool) -> RegistrationResult:
        # Preserve C2 password cost for accepted and duplicate requests without
        # holding the shared policy lock through Argon2 work.
        password_hash = self._passwords.hash(password)
        token_id, raw_token, token_hash = self._tokens.issue_email_verification_token()
        now = self._now()
        try:
            with session.begin():
                settings = self._settings.get(session, lock=True)
                if settings is None:
                    raise RegistrationUnavailableError()
                if settings.mode == 'closed':
                    return RegistrationResult('registration_closed')
                if not email_delivery_available:
                    raise RegistrationUnavailableError()
                user = self._users.create(
                    session, username=username, email=email, password_hash=password_hash,
                    role='user', status='pending', registration_mode_at_signup=settings.mode,
                )
                session.flush()
                session.add(EmailVerificationToken(
                    id=token_id, user_id=user.id, token_hash=token_hash,
                    email_normalized=user.email_normalized, created_at=now,
                    expires_at=now + EMAIL_VERIFICATION_TOKEN_LIFETIME,
                ))
                recipient = user.email
            return RegistrationResult('registration_request_accepted', recipient, raw_token)
        except IntegrityError:
            session.rollback()
            return RegistrationResult('registration_request_accepted')

    def issue_public_verification(self, session: Session, email: str) -> tuple[str, str] | None:
        """Issue only for an eligible C4 registrant under the existing C3 lock/throttle."""
        return AccountEmailService(self._tokens, self._passwords, self._now).issue_verification_for_public_email(
            session, email,
        )


class AuthenticationService:
    def __init__(self, token_service: TokenService, passwords: PasswordService | None = None) -> None:
        self._tokens = token_service
        self._passwords = passwords or _DEFAULT_PASSWORDS
        self._users = UserRepository()
        self._auth = AuthRepository()

    @staticmethod
    def _usable(user: User, session: AuthSession, now: datetime) -> bool:
        return user.status == 'active' and session.revoked_at is None and session.expires_at > now

    def login(self, session: Session, *, username: str, password: str) -> IssuedTokens:
        user = self._users.get_by_normalized_username(session, username)
        if user is None:
            self._passwords.verify_dummy(password)
            raise AuthenticationError()
        valid, updated_hash = self._passwords.verify(password, user.password_hash)
        if not valid or user.status != 'active':
            raise AuthenticationError()
        if updated_hash is not None:
            user.password_hash = updated_hash
        now = utc_now()
        auth_session = AuthSession(user_id=user.id, expires_at=now + SESSION_LIFETIME, last_used_at=now)
        session.add(auth_session)
        session.flush()
        issued, raw_refresh_token = self._issue_refresh(session, auth_session, now)
        session.commit()
        return self._issued(user, auth_session, raw_refresh_token)

    def refresh(self, session: Session, raw_token: str) -> IssuedTokens:
        parsed = self._tokens.parse_refresh_token(raw_token)
        if parsed is None:
            raise AuthenticationError()
        token_id, secret = parsed
        now = utc_now()
        try:
            replay_detected = False
            result: IssuedTokens | None = None
            with session.begin():
                refresh = self._auth.get_refresh_token(session, token_id, lock=True)
                if refresh is None:
                    raise AuthenticationError()
                auth_session = self._auth.get_session(session, refresh.session_id, lock=True)
                if auth_session is None:
                    raise AuthenticationError()
                # Any previously consumed token signals replay, even if a prior
                # rotation already revoked it. Locking serializes concurrent use.
                if refresh.used_at is not None or refresh.replaced_by_id is not None:
                    self._revoke_session(session, auth_session, now)
                    replay_detected = True
                else:
                    user = self._users.get_by_id(session, auth_session.user_id)
                    if (user is None or not self._usable(user, auth_session, now)
                            or refresh.revoked_at is not None or refresh.expires_at <= now
                            or not self._tokens.verify_refresh_secret(secret, refresh.token_hash)):
                        raise AuthenticationError()
                    refresh.used_at = now
                    refresh.revoked_at = now
                    auth_session.last_used_at = now
                    replacement, raw_refresh_token = self._issue_refresh(session, auth_session, now)
                    refresh.replaced_by_id = replacement.id
                    session.flush()
                    result = self._issued(user, auth_session, raw_refresh_token)
            if replay_detected or result is None:
                raise AuthenticationError()
            return result
        except AuthenticationError:
            session.rollback()
            raise

    def logout(self, session: Session, auth_session: AuthSession) -> None:
        now = utc_now()
        try:
            locked = self._auth.get_session(session, auth_session.id, lock=True)
            if locked is not None:
                self._revoke_session(session, locked, now)
            session.commit()
        except Exception:
            session.rollback()
            raise

    def _issue_refresh(self, session: Session, auth_session: AuthSession, now: datetime) -> tuple[AuthRefreshToken, str]:
        token_id, raw_token, token_hash = self._tokens.issue_refresh_token()
        token = AuthRefreshToken(id=token_id, session_id=auth_session.id, token_hash=token_hash,
                                 expires_at=auth_session.expires_at)
        session.add(token)
        session.flush()
        return token, raw_token

    def _issued(self, user: User, auth_session: AuthSession, raw_token: str) -> IssuedTokens:
        return IssuedTokens(access_token=self._tokens.issue_access_token(user.id, auth_session.id),
                            refresh_token=raw_token)

    def _revoke_session(self, session: Session, auth_session: AuthSession, now: datetime) -> None:
        if auth_session.revoked_at is None:
            auth_session.revoked_at = now
        self._auth.revoke_active_tokens(session, auth_session.id, now)


class AccountEmailService:
    """C3 token issuance/consumption. Email delivery stays outside DB transactions."""
    ISSUE_LIMIT = 5

    def __init__(self, tokens: TokenService, passwords: PasswordService | None = None,
                 now_provider=utc_now) -> None:
        self._tokens = tokens
        self._passwords = passwords or _DEFAULT_PASSWORDS
        self._now = now_provider

    def issue_verification(self, session: Session, user: User) -> str | None:
        now = self._now()
        user_id = user.id
        # Authentication dependencies may already have opened a read transaction.
        session.commit()
        token_id, raw, token_hash = self._tokens.issue_email_verification_token()
        with session.begin():
            locked_user = session.scalar(select(User).where(User.id == user_id).with_for_update())
            if locked_user is None or locked_user.email_verified:
                return None
            if self._is_throttled(session, EmailVerificationToken, locked_user.id, now):
                return None
            session.execute(update(EmailVerificationToken).where(
                EmailVerificationToken.user_id == locked_user.id,
                EmailVerificationToken.email_normalized == locked_user.email_normalized,
                EmailVerificationToken.used_at.is_(None), EmailVerificationToken.revoked_at.is_(None),
            ).values(revoked_at=now))
            session.add(EmailVerificationToken(id=token_id, user_id=locked_user.id, token_hash=token_hash,
                email_normalized=locked_user.email_normalized,
                created_at=now, expires_at=now + EMAIL_VERIFICATION_TOKEN_LIFETIME))
        return raw

    def issue_verification_for_public_email(self, session: Session, email: str) -> tuple[str, str] | None:
        normalized = normalize_email(email)
        now = self._now()
        session.commit()
        token_id, raw, token_hash = self._tokens.issue_email_verification_token()
        try:
            with session.begin():
                user = session.scalar(select(User).where(User.email_normalized == normalized).with_for_update())
                if (user is None or user.registration_mode_at_signup not in {'open', 'approval'}
                        or user.status != 'pending' or user.email_verified):
                    return None
                if self._is_throttled(session, EmailVerificationToken, user.id, now):
                    return None
                session.execute(update(EmailVerificationToken).where(
                    EmailVerificationToken.user_id == user.id,
                    EmailVerificationToken.email_normalized == user.email_normalized,
                    EmailVerificationToken.used_at.is_(None), EmailVerificationToken.revoked_at.is_(None),
                ).values(revoked_at=now))
                session.add(EmailVerificationToken(
                    id=token_id, user_id=user.id, token_hash=token_hash,
                    email_normalized=user.email_normalized, created_at=now,
                    expires_at=now + EMAIL_VERIFICATION_TOKEN_LIFETIME,
                ))
                recipient = user.email
            return recipient, raw
        except Exception:
            session.rollback()
            raise

    def issue_password_reset(self, session: Session, email: str) -> tuple[str, str] | None:
        from .repositories import normalize_email
        normalized = normalize_email(email)
        now = self._now()
        session.commit()
        token_id, raw, token_hash = self._tokens.issue_password_reset_token()
        try:
            with session.begin():
                user = session.scalar(select(User).where(
                    User.email_normalized == normalized).with_for_update())
                if user is None or user.status != 'active':
                    return None
                if self._is_throttled(session, PasswordResetToken, user.id, now):
                    return None
                user_id, email = user.id, user.email
                session.execute(update(PasswordResetToken).where(
                    PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.revoked_at.is_(None),
                ).values(revoked_at=now))
                session.add(PasswordResetToken(id=token_id, user_id=user_id, token_hash=token_hash,
                    created_at=now, expires_at=now + PASSWORD_RESET_TOKEN_LIFETIME))
            return email, raw
        except Exception:
            session.rollback()
            raise

    def verify_email(self, session: Session, raw_token: str) -> EmailVerificationResult:
        parsed = self._tokens.parse_opaque_token(raw_token, 'ev1')
        if parsed is None:
            raise RecoveryTokenError()
        token_id, secret = parsed
        now = self._now()
        try:
            with session.begin():
                token = session.scalar(select(EmailVerificationToken).where(
                    EmailVerificationToken.id == token_id).with_for_update())
                if token is None or token.used_at or token.revoked_at or token.expires_at <= now \
                        or not self._tokens.verify_refresh_secret(secret, token.token_hash):
                    raise RecoveryTokenError()
                user = session.scalar(select(User).where(User.id == token.user_id).with_for_update())
                if user is None or user.email_normalized != token.email_normalized:
                    raise RecoveryTokenError()
                user.email_verified = True
                token.used_at = now
                if user.registration_mode_at_signup == 'open':
                    settings = session.scalar(select(RegistrationSettings).where(
                        RegistrationSettings.id == RegistrationSettingsRepository.SINGLETON_ID,
                    ).with_for_update())
                    if settings is None:
                        raise RecoveryTokenError()
                    active_count = session.scalar(select(func.count()).select_from(User).where(
                        User.status == 'active',
                    ))
                    if settings.max_users is None or active_count < settings.max_users:
                        user.status = 'active'
                        result = EmailVerificationResult('active', 'active')
                    else:
                        result = EmailVerificationResult('pending', 'capacity_reached')
                elif user.registration_mode_at_signup == 'approval':
                    result = EmailVerificationResult('pending', 'approval_required')
                else:
                    result = EmailVerificationResult(user.status, 'unchanged')
            return result
        except RecoveryTokenError:
            session.rollback()
            raise

    def confirm_password_reset(self, session: Session, raw_token: str, new_password: str) -> str:
        self._passwords.validate_new_password(new_password)
        parsed = self._tokens.parse_opaque_token(raw_token, 'pr1')
        if parsed is None:
            raise RecoveryTokenError()
        token_id, secret = parsed
        now = self._now()
        try:
            with session.begin():
                token = session.scalar(select(PasswordResetToken).where(
                    PasswordResetToken.id == token_id).with_for_update())
                if token is None or token.used_at or token.revoked_at or token.expires_at <= now \
                        or not self._tokens.verify_refresh_secret(secret, token.token_hash):
                    raise RecoveryTokenError()
                user = session.scalar(select(User).where(User.id == token.user_id).with_for_update())
                if user is None or user.status != 'active':
                    raise RecoveryTokenError()
                email = user.email
                user.password_hash = self._passwords.hash(new_password)
                token.used_at = now
                session.execute(update(PasswordResetToken).where(
                    PasswordResetToken.user_id == user.id, PasswordResetToken.id != token.id,
                    PasswordResetToken.used_at.is_(None), PasswordResetToken.revoked_at.is_(None),
                ).values(revoked_at=now))
                session.execute(update(AuthSession).where(AuthSession.user_id == user.id,
                    AuthSession.revoked_at.is_(None)).values(revoked_at=now))
                session.execute(update(AuthRefreshToken).where(AuthRefreshToken.session_id.in_(
                    select(AuthSession.id).where(AuthSession.user_id == user.id)),
                    AuthRefreshToken.revoked_at.is_(None)).values(revoked_at=now))
            return email
        except RecoveryTokenError:
            session.rollback()
            raise

    def _is_throttled(self, session: Session, model, user_id, now: datetime) -> bool:
        # Token history is PostgreSQL-backed, shared across workers, and is audit retained.
        cutoff = now - timedelta(hours=1)
        recent = session.scalars(select(model.created_at).where(
            model.user_id == user_id, model.created_at >= cutoff).order_by(model.created_at.desc())).all()
        if len(recent) >= self.ISSUE_LIMIT:
            return True
        return bool(recent and recent[0] > now - timedelta(seconds=60))
