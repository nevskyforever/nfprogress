from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import AuthRefreshToken, AuthSession, User


def normalize_username(value: str) -> str:
    return value.strip().casefold()


def normalize_email(value: str) -> str:
    return value.strip().casefold()


class UserRepository:
    def get_by_normalized_username(self, session: Session, username: str) -> User | None:
        return session.scalar(select(User).where(User.username_normalized == normalize_username(username)))

    def get_by_id(self, session: Session, user_id: object) -> User | None:
        return session.get(User, user_id)

    def create(self, session: Session, *, username: str, email: str, password_hash: str,
               role: str = 'user', status: str = 'pending') -> User:
        user = User(username=username.strip(), username_normalized=normalize_username(username),
                    email=email.strip(), email_normalized=normalize_email(email), password_hash=password_hash,
                    role=role, status=status)
        session.add(user)
        return user


class AuthRepository:
    def get_session(self, session: Session, session_id: object, *, lock: bool = False) -> AuthSession | None:
        statement = select(AuthSession).where(AuthSession.id == session_id)
        if lock:
            statement = statement.with_for_update()
        return session.scalar(statement)

    def get_refresh_token(self, session: Session, token_id: object, *, lock: bool = False) -> AuthRefreshToken | None:
        statement = select(AuthRefreshToken).where(AuthRefreshToken.id == token_id)
        if lock:
            statement = statement.with_for_update()
        return session.scalar(statement)

    def revoke_active_tokens(self, session: Session, session_id: object, now: object) -> None:
        session.execute(update(AuthRefreshToken).where(
            AuthRefreshToken.session_id == session_id,
            AuthRefreshToken.revoked_at.is_(None),
        ).values(revoked_at=now))
