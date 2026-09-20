from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..dependencies import (AuthenticatedUser, get_authentication_service,
                            get_cloud_session, get_current_user, get_email_sender)
from .email import EmailSender, OutgoingEmail
from .schemas import (AccountLimitsResponse, AccountResponse, LoginRequest, PasswordResetConfirmRequest,
                      PasswordResetRequest, PublicVerificationRequest,
                      RefreshRequest, RegistrationRequest, TokenResponse,
                      VerificationTokenRequest)
from .services import (AccountEmailService, AuthenticationError,
                       AuthenticationService, RecoveryTokenError,
                       LimitsService, LimitsUnavailableError, RegistrationService,
                       RegistrationUnavailableError)
from .tokens import TokenService


router = APIRouter(prefix='/api/v1', tags=['cloud authentication'])


def _authentication_failure() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail={'code': 'invalid_credentials', 'message': 'Invalid credentials.'})


def _invalid_recovery_token() -> HTTPException:
    return HTTPException(status_code=400, detail={
        'code': 'invalid_or_expired_token', 'message': 'Invalid or expired token.',
    })


def _email_service(request: Request) -> AccountEmailService:
    return AccountEmailService(TokenService(request.app.state.runtime_config.require_auth_secret()))


def _registration_service(request: Request) -> RegistrationService:
    return RegistrationService(TokenService(request.app.state.runtime_config.require_auth_secret()))


def _trusted_link(request: Request, path: str, token: str) -> str | None:
    base = request.app.state.runtime_config.public_web_url
    if base is None:
        return None
    return f"{base.rstrip('/')}{path}?{urlencode({'token': token})}"


def _send(sender: EmailSender, message: OutgoingEmail) -> None:
    sender.send(message)


@router.get('/auth/registration')
def registration_policy(request: Request, session: Session = Depends(get_cloud_session)) -> dict[str, bool | str]:
    settings = _registration_service(request).public_policy(session)
    return {
        'mode': settings.mode,
        'registration_enabled': settings.mode != 'closed',
        'requires_approval': settings.mode == 'approval',
    }


@router.post('/auth/register', status_code=status.HTTP_202_ACCEPTED)
def register(payload: RegistrationRequest, background: BackgroundTasks, request: Request,
        session: Session = Depends(get_cloud_session), sender: EmailSender = Depends(get_email_sender)) -> dict[str, str]:
    config = request.app.state.runtime_config
    try:
        result = _registration_service(request).register(
            session, username=payload.username, email=payload.email, password=payload.password,
            email_delivery_available=config.environment != 'production' or config.email_delivery_configured,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail={'code': 'invalid_password', 'message': 'Invalid password.'}) from None
    except RegistrationUnavailableError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={
            'code': 'registration_unavailable', 'message': 'Registration is temporarily unavailable.',
        }) from None
    if result.code == 'registration_closed':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            'code': 'registration_closed', 'message': 'Registration is closed.',
        })
    if result.verification_token and result.email:
        link = _trusted_link(request, '/verify-email', result.verification_token)
        if link:
            background.add_task(_send, sender, OutgoingEmail(result.email, 'Подтверждение email',
                f'Подтвердите email: {link}\nСсылка действует 24 часа. Если это были не вы, проигнорируйте письмо.'))
    return {'code': 'registration_request_accepted'}


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


@router.get('/account/limits', response_model=AccountLimitsResponse)
def account_limits(current: AuthenticatedUser = Depends(get_current_user),
                   session: Session = Depends(get_cloud_session)) -> AccountLimitsResponse:
    try:
        limits = LimitsService().effective_for_user(session, current.user.id)
    except LimitsUnavailableError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={
            'code': 'limits_unavailable', 'message': 'Limits are temporarily unavailable.',
        }) from None
    return AccountLimitsResponse(max_cloud_projects=limits.max_cloud_projects)


@router.post('/account/email/verification/request', status_code=status.HTTP_202_ACCEPTED)
def request_verification(background: BackgroundTasks, request: Request,
        current: AuthenticatedUser = Depends(get_current_user), session: Session = Depends(get_cloud_session),
        sender: EmailSender = Depends(get_email_sender)) -> dict[str, str]:
    token = _email_service(request).issue_verification(session, current.user)
    link = _trusted_link(request, '/verify-email', token) if token else None
    if token and link:
        background.add_task(_send, sender, OutgoingEmail(current.user.email, 'Подтверждение email',
            f'Подтвердите email: {link}\nСсылка действует 24 часа. Если это были не вы, проигнорируйте письмо.'))
    return {'code': 'verification_request_accepted'}


@router.post('/auth/email/verification/request', status_code=status.HTTP_202_ACCEPTED)
def request_public_verification(payload: PublicVerificationRequest, background: BackgroundTasks, request: Request,
        session: Session = Depends(get_cloud_session), sender: EmailSender = Depends(get_email_sender)) -> dict[str, str]:
    issued = _registration_service(request).issue_public_verification(session, payload.email)
    if issued is not None:
        email, token = issued
        link = _trusted_link(request, '/verify-email', token)
        if link:
            background.add_task(_send, sender, OutgoingEmail(email, 'Подтверждение email',
                f'Подтвердите email: {link}\nСсылка действует 24 часа. Если это были не вы, проигнорируйте письмо.'))
    return {'code': 'verification_request_accepted'}


@router.post('/auth/email/verify')
def verify_email(payload: VerificationTokenRequest, request: Request,
        session: Session = Depends(get_cloud_session)) -> dict[str, str]:
    try:
        result = _email_service(request).verify_email(session, payload.token)
    except RecoveryTokenError:
        raise _invalid_recovery_token() from None
    return {'code': 'email_verified', 'account_status': result.account_status, 'activation': result.activation}


@router.post('/auth/password-reset/request', status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, background: BackgroundTasks, request: Request,
        session: Session = Depends(get_cloud_session), sender: EmailSender = Depends(get_email_sender)) -> dict[str, str]:
    issued = _email_service(request).issue_password_reset(session, payload.email)
    if issued is not None:
        email, token = issued
        link = _trusted_link(request, '/reset-password', token)
        if link:
            background.add_task(_send, sender, OutgoingEmail(email, 'Восстановление пароля',
                f'Установите новый пароль: {link}\nСсылка действует 1 час. Если это были не вы, проигнорируйте письмо.'))
    return {'code': 'password_reset_request_accepted'}


@router.post('/auth/password-reset/confirm')
def confirm_password_reset(payload: PasswordResetConfirmRequest, background: BackgroundTasks, request: Request,
        session: Session = Depends(get_cloud_session), sender: EmailSender = Depends(get_email_sender)) -> dict[str, str]:
    try:
        email = _email_service(request).confirm_password_reset(session, payload.token, payload.new_password)
    except RecoveryTokenError:
        raise _invalid_recovery_token() from None
    except ValueError:
        raise HTTPException(status_code=422, detail={'code': 'invalid_password', 'message': 'Invalid password.'}) from None
    background.add_task(_send, sender, OutgoingEmail(email, 'Пароль изменён',
        'Пароль вашей учётной записи был изменён. Если это были не вы, обратитесь в поддержку.'))
    return {'code': 'password_reset_complete'}
