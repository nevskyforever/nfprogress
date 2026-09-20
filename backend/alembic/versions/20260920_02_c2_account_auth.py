"""Create C2 account and authentication tables.

Revision ID: c2_account_auth_core
Revises: c1_postgresql_foundation
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2_account_auth_core'
down_revision: Union[str, Sequence[str], None] = 'c1_postgresql_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('username', sa.String(length=128), nullable=False),
        sa.Column('username_normalized', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('email_normalized', sa.String(length=320), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('password_hash', sa.String(length=512), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False, server_default=sa.text("'user'")),
        sa.Column('status', sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint("role IN ('user', 'admin')", name='ck_users_role'),
        sa.CheckConstraint("status IN ('pending', 'active', 'rejected', 'blocked')", name='ck_users_status'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username_normalized'),
        sa.UniqueConstraint('email_normalized'),
    )
    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_table(
        'auth_refresh_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replaced_by_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['auth_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['replaced_by_id'], ['auth_refresh_tokens.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_refresh_tokens_session_id', 'auth_refresh_tokens', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_auth_refresh_tokens_session_id', table_name='auth_refresh_tokens')
    op.drop_table('auth_refresh_tokens')
    op.drop_index('ix_auth_sessions_user_id', table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_table('users')
