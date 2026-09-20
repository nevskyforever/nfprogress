from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (AuthRefreshToken, AuthSession, EmailVerificationToken,
                     GlobalLimits, PasswordResetToken, RegistrationSettings,
                     ReservedUsername, User, UserLimitOverrides)
from .passwords import PasswordService
from .repositories import (AuthRepository, CloudProjectRepository, GlobalLimitsRepository,
                           RegistrationSettingsRepository,
                           ReservedUsernameRepository,
                           SyncRepository, UserLimitOverridesRepository, UserRepository,
                           lock_username_namespace, normalize_email,
                           normalize_username)
from .schemas import SYNC_PROTOCOL_VERSION, SyncEventEnvelope
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


class LimitsUnavailableError(Exception):
    """The authoritative global limits singleton is missing or unavailable."""


class AdminOperationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


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


@dataclass(frozen=True, slots=True)
class EffectiveLimits:
    max_cloud_projects: int


class LimitsService:
    """Compute effective limits without exposing their global or override source."""

    def __init__(self) -> None:
        self._global_limits = GlobalLimitsRepository()
        self._overrides = UserLimitOverridesRepository()

    def effective_for_user(self, session: Session, user_id: object) -> EffectiveLimits:
        global_limits = self._global_limits.get(session)
        if global_limits is None:
            raise LimitsUnavailableError()
        override = self._overrides.get(session, user_id)
        if override is not None and override.max_cloud_projects_override is not None:
            return EffectiveLimits(max_cloud_projects=override.max_cloud_projects_override)
        return EffectiveLimits(max_cloud_projects=global_limits.max_cloud_projects)


class CloudProjectLimitError(Exception):
    """A new cloud slot cannot be allocated under the effective C5 limit."""


class SyncProtocolError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True, slots=True)
class CloudProjectState:
    project_ids: list[str]
    count: int
    max_cloud_projects: int


class CloudProjectService:
    """C8's metadata-only cloud project registry.

    The owner row lock serializes slot allocation for one user across API
    workers.  It deliberately protects only creation; administrators may lower
    a limit below existing use without rewriting existing registry rows.
    """

    def __init__(self) -> None:
        self._projects = CloudProjectRepository()
        self._limits = LimitsService()

    def list(self, session: Session, user_id: object) -> CloudProjectState:
        limits = self._limits.effective_for_user(session, user_id)
        ids = self._projects.list_ids(session, user_id)
        return CloudProjectState(ids, len(ids), limits.max_cloud_projects)

    def enable(self, session: Session, user_id: object, project_id: str) -> CloudProjectState:
        try:
            # Authentication has already read through this request session.
            # Finish that read transaction before opening the allocation one.
            session.commit()
            with session.begin():
                # Locking the owner, rather than the project rows, also works
                # when the user has no rows yet and gives each user an
                # independent PostgreSQL transaction-scoped allocation lane.
                owner = session.scalar(select(User).where(User.id == user_id).with_for_update())
                if owner is None:
                    raise RuntimeError('Authenticated user disappeared.')
                existing = self._projects.get(session, user_id, project_id)
                if existing is None:
                    limits = self._limits.effective_for_user(session, user_id)
                    if self._projects.count(session, user_id) >= limits.max_cloud_projects:
                        raise CloudProjectLimitError()
                    self._projects.add(session, user_id, project_id)
                    session.flush()
            return self.list(session, user_id)
        except (CloudProjectLimitError, LimitsUnavailableError):
            session.rollback()
            raise

    def disable(self, session: Session, user_id: object, project_id: str) -> None:
        try:
            session.commit()
            with session.begin():
                self._projects.remove(session, user_id, project_id)
        except Exception:
            session.rollback()
            raise


@dataclass(frozen=True, slots=True)
class SyncPushResult:
    event_id: object
    server_sequence: int
    duplicate: bool


class SyncService:
    """C9 metadata-only transport; server order is not conflict resolution."""

    def __init__(self) -> None:
        self._sync = SyncRepository()
        self._projects = CloudProjectRepository()

    @staticmethod
    def require_protocol(version: int) -> None:
        if version != SYNC_PROTOCOL_VERSION:
            raise SyncProtocolError('sync_protocol_version_unsupported', 'Unsupported sync protocol version.', 422)

    def register_device(self, session: Session, user_id: object, device_id: object):
        try:
            session.commit()
            with session.begin():
                device = self._sync.register_device(session, user_id, device_id)
                device.last_seen_at = utc_now()
                state = self._sync.ensure_user_state(session, user_id)
                session.flush()
                return device.device_id, device.last_ack_sequence, state.current_sequence
        except Exception:
            session.rollback()
            raise

    def _registered_device(self, session: Session, user_id: object, device_id: object):
        device = self._sync.get_device(session, user_id, device_id, lock=True)
        if device is None:
            raise SyncProtocolError('sync_device_not_registered', 'Sync device is not registered.')
        return device

    @staticmethod
    def _same_event(row, event: SyncEventEnvelope, device_id: object) -> bool:
        return (row.device_id == device_id and row.project_id == event.project_id
                and row.entity_id == event.entity_id and row.entity_type == event.entity_type
                and row.operation == event.operation and row.revision == event.revision
                and row.updated_at == event.updated_at and row.deleted_at == event.deleted_at)

    def push(self, session: Session, user_id: object, device_id: object,
             events: list[SyncEventEnvelope]) -> tuple[list[SyncPushResult], int]:
        try:
            session.commit()
            with session.begin():
                device = self._registered_device(session, user_id, device_id)
                device.last_seen_at = utc_now()
                # Validate the whole batch before allocating a sequence so any
                # bad new event makes the transaction a genuine no-op.
                for event in events:
                    if self._projects.get(session, user_id, event.project_id) is None:
                        raise SyncProtocolError('cloud_project_not_enabled', 'Cloud project is not enabled.')
                state = self._sync.ensure_user_state(session, user_id, lock=True)
                results: list[SyncPushResult] = []
                seen: dict[object, SyncEventEnvelope] = {}
                for event in events:
                    prior = seen.get(event.event_id)
                    if prior is not None and prior != event:
                        raise SyncProtocolError('sync_event_id_conflict', 'Event ID was reused with different metadata.')
                    seen[event.event_id] = event
                    existing = self._sync.event(session, user_id, event.event_id)
                    if existing is not None:
                        if not self._same_event(existing, event, device_id):
                            raise SyncProtocolError('sync_event_id_conflict', 'Event ID was reused with different metadata.')
                        results.append(SyncPushResult(event.event_id, existing.server_sequence, True))
                        continue
                    state.current_sequence += 1
                    row = self._sync.add_event(
                        session, user_id=user_id, event_id=event.event_id, device_id=device_id,
                        project_id=event.project_id, entity_id=event.entity_id,
                        entity_type=event.entity_type, operation=event.operation,
                        revision=event.revision, updated_at=event.updated_at,
                        deleted_at=event.deleted_at, server_sequence=state.current_sequence,
                    )
                    session.flush()
                    results.append(SyncPushResult(event.event_id, row.server_sequence, False))
                return results, state.current_sequence
        except Exception:
            session.rollback()
            raise

    def pull(self, session: Session, user_id: object, device_id: object, since: int, limit: int):
        device = self._sync.get_device(session, user_id, device_id)
        if device is None:
            raise SyncProtocolError('sync_device_not_registered', 'Sync device is not registered.')
        events = self._sync.pull(session, user_id, since, limit)
        has_more = len(events) > limit
        visible = events[:limit]
        state = self._sync.ensure_user_state(session, user_id)
        next_cursor = visible[-1].server_sequence if visible else since
        return visible, next_cursor, has_more, state.current_sequence

    def ack(self, session: Session, user_id: object, device_id: object, cursor: int) -> int:
        try:
            session.commit()
            with session.begin():
                device = self._registered_device(session, user_id, device_id)
                state = self._sync.ensure_user_state(session, user_id, lock=True)
                if cursor > state.current_sequence:
                    raise SyncProtocolError('sync_cursor_invalid', 'Cursor is beyond the current server sequence.', 422)
                if cursor > device.last_ack_sequence:
                    device.last_ack_sequence = cursor
                return device.last_ack_sequence
        except Exception:
            session.rollback()
            raise


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
        self._reserved_usernames = ReservedUsernameRepository()

    def public_policy(self, session: Session) -> RegistrationSettings:
        settings = self._settings.get(session)
        if settings is None:
            raise RuntimeError('Registration settings are unavailable.')
        return settings

    def register(self, session: Session, *, username: str, email: str, password: str,
                 email_delivery_available: bool) -> RegistrationResult:
        # CLOSED and unavailable production registration are public policy
        # outcomes, so reject them before creating an avoidable Argon2 DoS
        # surface. This read is deliberately not the authoritative decision:
        # the locked re-check below governs creation if policy changes while
        # Argon2 is running.
        settings = self.public_policy(session)
        if settings.mode == 'closed':
            return RegistrationResult('registration_closed')
        if not email_delivery_available:
            raise RegistrationUnavailableError()

        # Preserve C2's public password-validation contract while avoiding
        # Argon2 work for a known policy-rejected username.
        self._passwords.validate_new_password(password)
        if self._reserved_usernames.is_reserved(session, username):
            return RegistrationResult('username_reserved')
        session.commit()

        # Preserve C2 password cost for accepted and duplicate requests without
        # holding the shared policy lock through Argon2 work.
        password_hash = self._passwords.hash(password)
        try:
            with session.begin():
                settings = self._settings.get(session, lock=True)
                if settings is None:
                    raise RegistrationUnavailableError()
                if settings.mode == 'closed':
                    return RegistrationResult('registration_closed')
                if not email_delivery_available:
                    raise RegistrationUnavailableError()
                # The authoritative claim happens after Argon2 and is shared
                # with C7 reservation management. Never hold it during hashing.
                lock_username_namespace(session, username)
                if self._reserved_usernames.is_reserved(session, username):
                    return RegistrationResult('username_reserved')
                token_id, raw_token, token_hash = self._tokens.issue_email_verification_token()
                now = self._now()
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


class AdminService:
    """Small C7 administration service over the existing C2--C6 authority."""

    def __init__(self, now_provider=utc_now) -> None:
        self._now = now_provider
        self._users = UserRepository()
        self._auth = AuthRepository()
        self._settings = RegistrationSettingsRepository()
        self._limits = GlobalLimitsRepository()
        self._overrides = UserLimitOverridesRepository()
        self._reserved = ReservedUsernameRepository()

    @staticmethod
    def _protected(user: User) -> None:
        if user.role == 'admin':
            raise AdminOperationError('admin_account_protected', 'Administrator accounts are protected.')

    @staticmethod
    def _not_found() -> None:
        raise AdminOperationError('user_not_found', 'User was not found.', 404)

    def _locked_user(self, session: Session, user_id: object) -> User:
        user = session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            self._not_found()
        return user

    @staticmethod
    def _require_capacity(session: Session, settings: RegistrationSettings) -> None:
        active_count = session.scalar(select(func.count()).select_from(User).where(User.status == 'active')) or 0
        if settings.max_users is not None and active_count >= settings.max_users:
            raise AdminOperationError('user_capacity_reached', 'User capacity has been reached.')

    def approve(self, session: Session, user_id: object) -> User:
        try:
            session.commit()
            with session.begin():
                user = self._locked_user(session, user_id)
                self._protected(user)
                if user.status == 'active':
                    return user
                if user.status not in {'pending', 'rejected'}:
                    raise AdminOperationError('invalid_user_status', 'User cannot be approved in this state.')
                if not user.email_verified:
                    raise AdminOperationError('email_not_verified', 'Email must be verified before activation.')
                settings = self._settings.get(session, lock=True)
                if settings is None:
                    raise AdminOperationError('registration_unavailable', 'Registration settings are unavailable.', 503)
                self._require_capacity(session, settings)
                user.status = 'active'
                return user
        except AdminOperationError:
            session.rollback()
            raise

    def reject(self, session: Session, user_id: object) -> User:
        try:
            session.commit()
            with session.begin():
                user = self._locked_user(session, user_id)
                self._protected(user)
                if user.status == 'rejected':
                    return user
                if user.status != 'pending':
                    raise AdminOperationError('invalid_user_status', 'Only pending users can be rejected.')
                user.status = 'rejected'
                return user
        except AdminOperationError:
            session.rollback()
            raise

    def block(self, session: Session, user_id: object) -> User:
        try:
            session.commit()
            with session.begin():
                user = self._locked_user(session, user_id)
                self._protected(user)
                if user.status == 'blocked':
                    return user
                if user.status != 'active':
                    raise AdminOperationError('invalid_user_status', 'Only active users can be blocked.')
                user.status = 'blocked'
                self._auth.revoke_user_sessions(session, user.id, self._now())
                return user
        except AdminOperationError:
            session.rollback()
            raise

    def unblock(self, session: Session, user_id: object) -> User:
        try:
            session.commit()
            with session.begin():
                user = self._locked_user(session, user_id)
                self._protected(user)
                if user.status == 'active':
                    return user
                if user.status != 'blocked':
                    raise AdminOperationError('invalid_user_status', 'Only blocked users can be unblocked.')
                if not user.email_verified:
                    raise AdminOperationError('email_not_verified', 'Email must be verified before activation.')
                settings = self._settings.get(session, lock=True)
                if settings is None:
                    raise AdminOperationError('registration_unavailable', 'Registration settings are unavailable.', 503)
                self._require_capacity(session, settings)
                user.status = 'active'
                return user
        except AdminOperationError:
            session.rollback()
            raise

    def revoke_sessions(self, session: Session, user_id: object) -> tuple[int, int]:
        try:
            session.commit()
            with session.begin():
                user = self._locked_user(session, user_id)
                self._protected(user)
                return self._auth.revoke_user_sessions(session, user.id, self._now())
        except AdminOperationError:
            session.rollback()
            raise

    def update_registration(self, session: Session, *, mode: str | None, max_users: int | None | object) -> RegistrationSettings:
        session.commit()
        with session.begin():
            settings = self._settings.get(session, lock=True)
            if settings is None:
                raise AdminOperationError('registration_unavailable', 'Registration settings are unavailable.', 503)
            if mode is not None:
                settings.mode = mode
            if max_users is not _UNSET:
                settings.max_users = max_users
            return settings

    def update_global_limits(self, session: Session, max_cloud_projects: int) -> GlobalLimits:
        session.commit()
        with session.begin():
            limits = self._limits.get(session, lock=True)
            if limits is None:
                raise AdminOperationError('limits_unavailable', 'Limits are unavailable.', 503)
            limits.max_cloud_projects = max_cloud_projects
            return limits

    def update_override(self, session: Session, user_id: object, value: int | None) -> tuple[int | None, int]:
        try:
            session.commit()
            with session.begin():
                user = self._locked_user(session, user_id)
                limits = self._limits.get(session, lock=True)
                if limits is None:
                    raise AdminOperationError('limits_unavailable', 'Limits are unavailable.', 503)
                if value is None:
                    self._overrides.clear(session, user.id)
                    return None, limits.max_cloud_projects
                row = self._overrides.get(session, user.id)
                if row is None:
                    session.add(UserLimitOverrides(user_id=user.id, max_cloud_projects_override=value))
                else:
                    row.max_cloud_projects_override = value
                return value, value
        except AdminOperationError:
            session.rollback()
            raise

    def add_reserved_username(self, session: Session, username: str) -> ReservedUsername:
        normalized = normalize_username(username)
        try:
            session.commit()
            with session.begin():
                lock_username_namespace(session, normalized)
                existing = session.get(ReservedUsername, normalized)
                if existing is not None:
                    return existing
                if self._users.get_by_normalized_username(session, normalized) is not None:
                    raise AdminOperationError('username_in_use', 'Username is already in use.')
                row = self._reserved.add(session, normalized)
                session.flush()
                return row
        except AdminOperationError:
            session.rollback()
            raise

    def remove_reserved_username(self, session: Session, username: str) -> bool:
        normalized = normalize_username(username)
        session.commit()
        with session.begin():
            lock_username_namespace(session, normalized)
            return self._reserved.remove(session, normalized)


_UNSET = object()


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
