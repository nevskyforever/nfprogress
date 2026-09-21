from __future__ import annotations

import base64
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .passwords import MAX_PASSWORD_LENGTH


_BASE64URL_RE = re.compile(r'^[A-Za-z0-9_-]*$')
MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES = 8_388_624
MAX_ENCRYPTED_SYNC_BATCH_CIPHERTEXT_BYTES = 16_777_216
MAX_ENCRYPTED_SYNC_WIRE_BODY_BYTES = 33_554_432


def decode_canonical_base64url(value: str, *, expected_length: int | None = None,
                               minimum_length: int | None = None,
                               maximum_length: int | None = None) -> bytes:
    """Decode only canonical, unpadded Base64URL binary wire values."""
    if not isinstance(value, str) or not _BASE64URL_RE.fullmatch(value) or len(value) % 4 == 1:
        raise ValueError('Invalid binary encoding.')
    try:
        decoded = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
    except (ValueError, UnicodeEncodeError) as error:
        raise ValueError('Invalid binary encoding.') from error
    if base64.urlsafe_b64encode(decoded).decode('ascii').rstrip('=') != value:
        raise ValueError('Invalid binary encoding.')
    if expected_length is not None and len(decoded) != expected_length:
        raise ValueError('Invalid binary encoding.')
    if minimum_length is not None and len(decoded) < minimum_length:
        raise ValueError('Invalid binary encoding.')
    if maximum_length is not None and len(decoded) > maximum_length:
        raise ValueError('Invalid binary encoding.')
    return decoded


def encode_canonical_base64url(value: bytes) -> str:
    """Encode binary fields as canonical, unpadded Base64URL."""
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def _validate_binary(*, expected_length: int | None = None,
                     minimum_length: int | None = None,
                     maximum_length: int | None = None):
    def validator(value: str) -> str:
        decode_canonical_base64url(value, expected_length=expected_length, minimum_length=minimum_length,
                                   maximum_length=maximum_length)
        return value
    return validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=1024)


class VerificationTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=1024)


class PasswordResetRequest(BaseModel):
    # Deliberately not EmailStr: malformed inputs receive the same public response.
    email: str = Field(min_length=1, max_length=320)


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    username: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator('username')
    @classmethod
    def username_must_not_be_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Username must not be empty.')
        return value

    @field_validator('email')
    @classmethod
    def email_must_have_valid_syntax(cls, value: str) -> str:
        display_email = value.strip()
        try:
            validate_email(display_email, check_deliverability=False)
        except EmailNotValidError as error:
            raise ValueError('Email must have valid syntax.') from error
        return display_email


class PublicVerificationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Deliberately keep this generic like password reset: malformed and unknown
    # inputs cannot become an account-existence oracle.
    email: str = Field(min_length=1, max_length=320)


class PasswordResetConfirmRequest(VerificationTokenRequest):
    new_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    access_expires_in: int


class AccountResponse(BaseModel):
    id: UUID
    username: str
    email: str
    email_verified: bool
    role: str
    status: str
    created_at: datetime


class AccountLimitsResponse(BaseModel):
    max_cloud_projects: int


class CloudProjectsResponse(BaseModel):
    cloud_project_ids: list[str]
    cloud_project_count: int
    max_cloud_projects: int


class PasswordKdfDto(BaseModel):
    """C11 password-KDF public metadata, with binary values encoded as Base64URL."""

    model_config = ConfigDict(extra='forbid')
    kdf_version: int = Field(ge=1)
    algorithm: Literal['argon2id13']
    salt: str
    opslimit: int = Field(ge=1)
    memlimit: int = Field(ge=1)

    _salt = field_validator('salt')(_validate_binary(expected_length=16))


class PasswordWrappedAmkDto(BaseModel):
    """Future API DTO only; it contains no passphrase or plaintext key material."""

    model_config = ConfigDict(extra='forbid')
    crypto_version: int = Field(ge=1)
    wrapping_version: int = Field(ge=1)
    kdf: PasswordKdfDto
    nonce: str
    ciphertext: str

    _nonce = field_validator('nonce')(_validate_binary(expected_length=24))
    _ciphertext = field_validator('ciphertext')(_validate_binary(expected_length=48))


class RecoveryWrappedAmkDto(BaseModel):
    """Future API DTO only; the Recovery Key itself is never represented."""

    model_config = ConfigDict(extra='forbid')
    crypto_version: int = Field(ge=1)
    wrapping_version: int = Field(ge=1)
    nonce: str
    ciphertext: str

    _nonce = field_validator('nonce')(_validate_binary(expected_length=24))
    _ciphertext = field_validator('ciphertext')(_validate_binary(expected_length=48))


class ObjectEnvelopeDto(BaseModel):
    """Future API DTO for opaque client ciphertext; this server does not decrypt."""

    model_config = ConfigDict(extra='forbid')
    crypto_version: int = Field(ge=1)
    aad_version: int = Field(ge=1)
    nonce: str
    ciphertext: str

    _nonce = field_validator('nonce')(_validate_binary(expected_length=24))
    _ciphertext = field_validator('ciphertext')(_validate_binary(
        minimum_length=16, maximum_length=MAX_ENCRYPTED_SYNC_CIPHERTEXT_BYTES,
    ))


SYNC_PROTOCOL_VERSION = 1
ENCRYPTED_SYNC_VERSION = 1
SYNC_MAX_WIRE_INTEGER = 9_007_199_254_740_991  # JavaScript Number.MAX_SAFE_INTEGER


class SyncEventEnvelope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_id: UUID
    project_id: str = Field(min_length=1, max_length=512)
    entity_id: str = Field(min_length=1, max_length=512)
    entity_type: str = Field(min_length=1, max_length=128, pattern=r'^[a-z][a-z0-9_:-]*$')
    operation: Literal['upsert', 'delete', 'event']
    revision: int = Field(ge=1, le=SYNC_MAX_WIRE_INTEGER)
    updated_at: datetime
    deleted_at: datetime | None = None

    @model_validator(mode='after')
    def validate_tombstone_and_timestamps(self) -> 'SyncEventEnvelope':
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError('updated_at must include a timezone.')
        if self.deleted_at is not None and (self.deleted_at.tzinfo is None or self.deleted_at.utcoffset() is None):
            raise ValueError('deleted_at must include a timezone.')
        if (self.operation == 'delete') != (self.deleted_at is not None):
            raise ValueError('delete requires deleted_at; upsert and event forbid it.')
        return self


class SyncPushRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    protocol_version: int
    device_id: UUID
    events: list[SyncEventEnvelope] = Field(max_length=100)


class SyncPushResult(BaseModel):
    event_id: UUID
    server_sequence: int = Field(ge=1, le=SYNC_MAX_WIRE_INTEGER)
    duplicate: bool


class SyncPushResponse(BaseModel):
    protocol_version: int = SYNC_PROTOCOL_VERSION
    results: list[SyncPushResult]
    current_cursor: int = Field(ge=0, le=SYNC_MAX_WIRE_INTEGER)


class SyncDeviceResponse(BaseModel):
    protocol_version: int = SYNC_PROTOCOL_VERSION
    device_id: UUID
    last_ack_cursor: int = Field(ge=0, le=SYNC_MAX_WIRE_INTEGER)


class SyncPullEvent(SyncEventEnvelope):
    device_id: UUID
    server_sequence: int = Field(ge=1, le=SYNC_MAX_WIRE_INTEGER)


class SyncPullResponse(BaseModel):
    protocol_version: int = SYNC_PROTOCOL_VERSION
    events: list[SyncPullEvent]
    next_cursor: int = Field(ge=0, le=SYNC_MAX_WIRE_INTEGER)
    has_more: bool


class SyncAckRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    protocol_version: int
    device_id: UUID
    cursor: int = Field(ge=0, le=SYNC_MAX_WIRE_INTEGER)


class EncryptedSyncPushItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event: SyncEventEnvelope
    object: ObjectEnvelopeDto


class EncryptedSyncPushRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    protocol_version: int
    encrypted_sync_version: int
    device_id: UUID
    items: list[EncryptedSyncPushItem] = Field(max_length=100)


class EncryptedSyncPushResponse(BaseModel):
    protocol_version: int = SYNC_PROTOCOL_VERSION
    encrypted_sync_version: int = ENCRYPTED_SYNC_VERSION
    results: list[SyncPushResult]
    current_cursor: int = Field(ge=0, le=SYNC_MAX_WIRE_INTEGER)


class EncryptedSyncPullItem(BaseModel):
    event: SyncPullEvent
    object: ObjectEnvelopeDto | None


class EncryptedSyncPullResponse(BaseModel):
    protocol_version: int = SYNC_PROTOCOL_VERSION
    encrypted_sync_version: int = ENCRYPTED_SYNC_VERSION
    items: list[EncryptedSyncPullItem]
    next_cursor: int = Field(ge=0, le=SYNC_MAX_WIRE_INTEGER)
    has_more: bool


class AdminUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    email_verified: bool
    role: str
    status: str
    registration_mode_at_signup: str | None
    created_at: datetime
    max_cloud_projects_override: int | None
    effective_max_cloud_projects: int


class AdminUsersResponse(BaseModel):
    users: list[AdminUserResponse]
    total: int
    limit: int
    offset: int


class AdminRegistrationPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['open', 'approval', 'closed'] | None = None
    max_users: int | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def explicit_mode_must_be_valid(self) -> 'AdminRegistrationPatch':
        if 'mode' in self.model_fields_set and self.mode is None:
            raise ValueError('Registration mode must be open, approval, or closed.')
        return self


class AdminRegistrationResponse(BaseModel):
    mode: Literal['open', 'approval', 'closed']
    max_users: int | None
    active_users: int


class AdminLimitsPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    max_cloud_projects: int = Field(ge=0)


class AdminLimitsResponse(BaseModel):
    max_cloud_projects: int


class AdminUserLimitPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    max_cloud_projects_override: int | None = Field(ge=0)


class AdminUserLimitResponse(BaseModel):
    max_cloud_projects_override: int | None
    effective_max_cloud_projects: int


class ReservedUsernameRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=128)


class ReservedUsernameResponse(BaseModel):
    username_normalized: str
    created_at: datetime
