from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import (AuthenticatedUser, get_authentication_service,
                            get_cloud_session, get_current_user)
from .schemas import AccountResponse, LoginRequest, RefreshRequest, TokenResponse
from .services import AuthenticationError, AuthenticationService


router = APIRouter(prefix='/api/v1', tags=['cloud authentication'])


def _authentication_failure() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail={'code': 'invalid_credentials', 'message': 'Invalid credentials.'})


@router.post('/auth/login', response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_cloud_session),
          service: AuthenticationService = Depends(get_authentication_service)) -> TokenResponse:
    try:
        result = service.login(session, username=payload.username, password=payload.password)
    except AuthenticationError:
        raise _authentication_failure() from None
    return TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token,
                         access_expires_in=result.access_expires_in)


@router.post('/auth/refresh', response_model=TokenResponse)
def refresh(payload: RefreshRequest, session: Session = Depends(get_cloud_session),
            service: AuthenticationService = Depends(get_authentication_service)) -> TokenResponse:
    try:
        result = service.refresh(session, payload.refresh_token)
    except AuthenticationError:
        raise _authentication_failure() from None
    return TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token,
                         access_expires_in=result.access_expires_in)


@router.post('/auth/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(current: AuthenticatedUser = Depends(get_current_user),
           session: Session = Depends(get_cloud_session),
           service: AuthenticationService = Depends(get_authentication_service)) -> None:
    service.logout(session, current.session)


@router.get('/account/me', response_model=AccountResponse)
def account_me(current: AuthenticatedUser = Depends(get_current_user)) -> AccountResponse:
    user = current.user
    return AccountResponse(id=user.id, username=user.username, email=user.email,
        email_verified=user.email_verified, role=user.role, status=user.status, created_at=user.created_at)
