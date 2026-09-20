from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from .models import AuthRefreshToken, AuthSession, User
from .passwords import PasswordService
from .repositories import AuthRepository, UserRepository
from .tokens import ACCESS_TOKEN_LIFETIME, SESSION_LIFETIME, TokenService, utc_now


_DEFAULT_PASSWORDS = PasswordService()


class AuthenticationError(Exception):
    """A deliberately generic public authentication failure."""


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
