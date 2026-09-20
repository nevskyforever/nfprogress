from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .passwords import MAX_PASSWORD_LENGTH


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
