from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


UTC_NOW = text("timezone('utc', now())")


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name='ck_users_role'),
        CheckConstraint(
            "status IN ('pending', 'active', 'rejected', 'blocked')",
            name='ck_users_status',
        ),
        CheckConstraint(
            "registration_mode_at_signup IS NULL OR registration_mode_at_signup IN ('open', 'approval')",
            name='ck_users_registration_mode_at_signup',
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    username_normalized: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text('false'))
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default='user', server_default=text("'user'"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='pending', server_default=text("'pending'"))
    registration_mode_at_signup: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW, onupdate=UTC_NOW)


class RegistrationSettings(Base):
    """The one PostgreSQL-backed authority for public registration policy."""

    __tablename__ = 'registration_settings'
    __table_args__ = (
        CheckConstraint('id = 1', name='ck_registration_settings_singleton'),
        CheckConstraint("mode IN ('open', 'approval', 'closed')", name='ck_registration_settings_mode'),
        CheckConstraint('max_users IS NULL OR max_users >= 0', name='ck_registration_settings_max_users'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    max_users: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW,
                                                   onupdate=UTC_NOW)


class ReservedUsername(Base):
    """A public-registration policy record, deliberately separate from User."""

    __tablename__ = 'reserved_usernames'

    username_normalized: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=UTC_NOW,
    )


class GlobalLimits(Base):
    """The singleton PostgreSQL authority for per-user cloud resource defaults."""

    __tablename__ = 'global_limits'
    __table_args__ = (
        CheckConstraint('id = 1', name='ck_global_limits_singleton'),
        CheckConstraint('max_cloud_projects >= 0', name='ck_global_limits_max_cloud_projects'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    max_cloud_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW,
                                                   onupdate=UTC_NOW)


class UserLimitOverrides(Base):
    __tablename__ = 'user_limit_overrides'
    __table_args__ = (
        CheckConstraint(
            'max_cloud_projects_override IS NULL OR max_cloud_projects_override >= 0',
            name='ck_user_limit_overrides_max_cloud_projects',
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True,
    )
    max_cloud_projects_override: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW,
                                                   onupdate=UTC_NOW)


class CloudProject(Base):
    """An owner's cloud-slot reservation; project content never belongs here."""

    __tablename__ = 'cloud_projects'
    __table_args__ = (
        CheckConstraint("char_length(project_id) >= 1", name='ck_cloud_projects_project_id_not_empty'),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True,
    )
    # Legacy, SQLite and Tauri project IDs are string contracts.  Keep their
    # established 32-hex IDs and any compatible historical values losslessly.
    project_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=UTC_NOW,
    )


class AuthSession(Base):
    __tablename__ = 'auth_sessions'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthRefreshToken(Base):
    __tablename__ = 'auth_refresh_tokens'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('auth_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('auth_refresh_tokens.id', ondelete='SET NULL'))


class EmailVerificationToken(Base):
    __tablename__ = 'email_verification_tokens'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=UTC_NOW)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
