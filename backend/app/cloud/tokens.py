from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError


ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
SESSION_LIFETIME = timedelta(days=30)
EMAIL_VERIFICATION_TOKEN_LIFETIME = timedelta(hours=24)
PASSWORD_RESET_TOKEN_LIFETIME = timedelta(hours=1)
JWT_ISSUER = 'nfprogress-cloud'
JWT_AUDIENCE = 'nfprogress-api'
JWT_ALGORITHM = 'HS256'


class TokenValidationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID


def utc_now() -> datetime:
    return datetime.now(UTC)


class TokenService:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue_access_token(self, user_id: uuid.UUID, session_id: uuid.UUID, now: datetime | None = None) -> str:
        issued_at = now or utc_now()
        payload = {
            'sub': str(user_id), 'sid': str(session_id), 'iss': JWT_ISSUER,
            'aud': JWT_AUDIENCE, 'iat': issued_at, 'nbf': issued_at,
            'exp': issued_at + ACCESS_TOKEN_LIFETIME, 'jti': str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._secret, algorithm=JWT_ALGORITHM)

    def decode_access_token(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER, audience=JWT_AUDIENCE,
                options={'require': ['sub', 'sid', 'iss', 'aud', 'iat', 'nbf', 'exp', 'jti']})
            return AccessClaims(user_id=uuid.UUID(payload['sub']), session_id=uuid.UUID(payload['sid']))
        except (InvalidTokenError, KeyError, ValueError, TypeError) as error:
            raise TokenValidationError from error

    def issue_refresh_token(self) -> tuple[uuid.UUID, str, str]:
        token_id = uuid.uuid4()
        secret = secrets.token_urlsafe(32)
        return token_id, f'rt1.{token_id}.{secret}', self.hash_refresh_secret(secret)

    @staticmethod
    def hash_refresh_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode('utf-8')).hexdigest()

    def verify_refresh_secret(self, secret: str, token_hash: str) -> bool:
        return hmac.compare_digest(self.hash_refresh_secret(secret), token_hash)

    def issue_email_verification_token(self) -> tuple[uuid.UUID, str, str]:
        return self._issue_opaque_token('ev1')

    def issue_password_reset_token(self) -> tuple[uuid.UUID, str, str]:
        return self._issue_opaque_token('pr1')

    @staticmethod
    def _issue_opaque_token(prefix: str) -> tuple[uuid.UUID, str, str]:
        token_id = uuid.uuid4()
        secret = secrets.token_urlsafe(32)
        return token_id, f'{prefix}.{token_id}.{secret}', hashlib.sha256(secret.encode()).hexdigest()

    @staticmethod
    def parse_opaque_token(raw_token: str, prefix: str) -> tuple[uuid.UUID, str] | None:
        parts = raw_token.split('.')
        if len(parts) != 3 or parts[0] != prefix or not parts[2]:
            return None
        try:
            return uuid.UUID(parts[1]), parts[2]
        except ValueError:
            return None

    @staticmethod
    def parse_refresh_token(raw_token: str) -> tuple[uuid.UUID, str] | None:
        parts = raw_token.split('.')
        if len(parts) != 3 or parts[0] != 'rt1' or not parts[2]:
            return None
        try:
            return uuid.UUID(parts[1]), parts[2]
        except ValueError:
            return None
