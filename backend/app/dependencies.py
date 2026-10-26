from __future__ import annotations

import secrets
from collections.abc import Generator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.orm import Session

from .db import CloudDatabase


@dataclass(slots=True)
class Services:
    repository: object
    projects: object
    notes_class: type
    game: object
    settings: object
    content: object
    integrations: object
    documents: object


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_cloud_session(request: Request) -> Generator[Session, None, None]:
    """Future cloud-route dependency; legacy routes deliberately do not use it."""
    database: CloudDatabase = request.app.state.cloud_database
    try:
        yield from database.session_scope()
    except PoolTimeoutError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={'code': 'database_capacity_unavailable'}) from None


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Authorization context; cloud ownership always originates here, never from client IDs."""

    user: object
    session: object


_bearer = HTTPBearer(auto_error=False)


def _invalid_access_token() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail={'code': 'invalid_token', 'message': 'Invalid authentication token.'})


def get_authentication_service(request: Request):
    from .cloud.services import AuthenticationService
    from .cloud.tokens import TokenService
    return AuthenticationService(TokenService(request.app.state.runtime_config.require_auth_secret()))


def get_email_sender(request: Request):
    return request.app.state.email_sender


def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
        session: Session = Depends(get_cloud_session),
        authentication_service=Depends(get_authentication_service),
) -> AuthenticatedUser:
    """Validate JWT and re-check session/user state in PostgreSQL for every request."""
    from .cloud.models import AuthSession, User
    from .cloud.tokens import TokenValidationError, utc_now

    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise _invalid_access_token()
    try:
        claims = authentication_service._tokens.decode_access_token(credentials.credentials)
    except TokenValidationError:
        raise _invalid_access_token() from None
    auth_session = session.get(AuthSession, claims.session_id)
    user = session.get(User, claims.user_id)
    now = utc_now()
    if (auth_session is None or user is None or auth_session.user_id != user.id
            or auth_session.revoked_at is not None or auth_session.expires_at <= now
            or user.status != 'active'):
        raise _invalid_access_token()
    return AuthenticatedUser(user=user, session=auth_session)


def get_current_accepted_user(
        request: Request,
        current: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_cloud_session),
) -> AuthenticatedUser:
    """Gate normal-user cloud data operations on exact current legal versions."""
    from .cloud.legal_documents import (DEFAULT_LEGAL_DOCUMENT_REGISTRY,
                                        LegalAcceptanceService,
                                        LegalDocumentError)

    if current.user.role != 'user':
        return current
    registry = getattr(request.app.state, 'legal_document_registry',
                       DEFAULT_LEGAL_DOCUMENT_REGISTRY)
    try:
        missing = LegalAcceptanceService(registry).missing_for_gate(session, current.user.id)
    except LegalDocumentError as error:
        raise HTTPException(status_code=error.status_code, detail={
            'code': error.code,
            'message': 'Required legal documents are unavailable.',
        }) from None
    if missing:
        raise HTTPException(status_code=451, detail={
            'code': 'legal_acceptance_required',
            'message': 'Current legal documents must be accepted.',
            'missing_document_ids': [version.document_id for version in missing],
        })
    return current


def get_current_admin(current: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """C7's server-side boundary; frontend guards are only convenience."""
    if current.user.role != 'admin' or current.user.status != 'active':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            'code': 'admin_required', 'message': 'Administrator access is required.',
        })
    return current


def require_session(
        request: Request,
        token: str | None = Header(default=None, alias='X-NFProgress-Token'),
) -> None:
    expected = request.app.state.runtime_config.session_token
    if expected is None:
        return
    if token is None or not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'code': 'invalid_session', 'message': 'Недействительная сессия.'},
        )
