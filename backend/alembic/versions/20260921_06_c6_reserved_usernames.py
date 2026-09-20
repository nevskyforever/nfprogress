"""Create C6 reserved public-registration usernames.

Revision ID: c6_reserved_usernames
Revises: c5_limits_framework
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c6_reserved_usernames'
down_revision: Union[str, Sequence[str], None] = 'c5_limits_framework'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_NOW = sa.text("timezone('utc', now())")
INITIAL_RESERVED_USERNAMES = (
    'admin', 'administrator', 'root', 'system', 'support', 'security', 'staff',
    'moderator', 'official', 'api', 'www', 'nfprogress', 'wow', 'worta',
)


def upgrade() -> None:
    op.create_table(
        'reserved_usernames',
        sa.Column('username_normalized', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.PrimaryKeyConstraint('username_normalized'),
    )
    op.bulk_insert(
        sa.table('reserved_usernames', sa.column('username_normalized', sa.String())),
        [{'username_normalized': username} for username in INITIAL_RESERVED_USERNAMES],
    )


def downgrade() -> None:
    op.drop_table('reserved_usernames')
