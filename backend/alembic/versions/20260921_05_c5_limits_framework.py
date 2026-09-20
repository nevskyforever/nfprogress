"""Create C5 PostgreSQL-backed cloud limits.

Revision ID: c5_limits_framework
Revises: c4_registration_controls
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5_limits_framework'
down_revision: Union[str, Sequence[str], None] = 'c4_registration_controls'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    op.create_table(
        'global_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('max_cloud_projects', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint('id = 1', name='ck_global_limits_singleton'),
        sa.CheckConstraint('max_cloud_projects >= 0', name='ck_global_limits_max_cloud_projects'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.bulk_insert(
        sa.table('global_limits', sa.column('id', sa.Integer()), sa.column('max_cloud_projects', sa.Integer())),
        [{'id': 1, 'max_cloud_projects': 20}],
    )
    op.create_table(
        'user_limit_overrides',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('max_cloud_projects_override', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=UTC_NOW),
        sa.CheckConstraint(
            'max_cloud_projects_override IS NULL OR max_cloud_projects_override >= 0',
            name='ck_user_limit_overrides_max_cloud_projects',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_limit_overrides')
    op.drop_table('global_limits')
