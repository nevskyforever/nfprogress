"""Create C4 public registration controls.

Revision ID: c4_registration_controls
Revises: c3_email_account_recovery
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4_registration_controls'
down_revision: Union[str, Sequence[str], None] = 'c3_email_account_recovery'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.create_table(
        'registration_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=16), nullable=False),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint('id = 1', name='ck_registration_settings_singleton'),
        sa.CheckConstraint("mode IN ('open', 'approval', 'closed')", name='ck_registration_settings_mode'),
        sa.CheckConstraint('max_users IS NULL OR max_users >= 0', name='ck_registration_settings_max_users'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.bulk_insert(
        sa.table('registration_settings', sa.column('id', sa.Integer()), sa.column('mode', sa.String()),
                 sa.column('max_users', sa.Integer())),
        [{'id': 1, 'mode': 'closed', 'max_users': None}],
    )
    op.add_column('users', sa.Column('registration_mode_at_signup', sa.String(length=16), nullable=True))
    op.create_check_constraint(
        'ck_users_registration_mode_at_signup', 'users',
        "registration_mode_at_signup IS NULL OR registration_mode_at_signup IN ('open', 'approval')",
    )
    op.create_index('ix_users_status', 'users', ['status'])


def downgrade() -> None:
    op.drop_index('ix_users_status', table_name='users')
    op.drop_constraint('ck_users_registration_mode_at_signup', 'users', type_='check')
    op.drop_column('users', 'registration_mode_at_signup')
    op.drop_table('registration_settings')
